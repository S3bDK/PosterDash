from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import requests
import socket
import json
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "posterdash-secret-key"

CONFIG_FILE = "config.json"
STATE_FILE = "state.json"
UPLOAD_FOLDER = os.path.join("static", "uploads")

BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE = "https://image.tmdb.org/t/p/w500"
FULL_IMAGE_BASE = "https://image.tmdb.org/t/p/original"

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "mp4"}

DEFAULT_CONFIG = {
    "api_key": "",
    "slideshow_delay": 15000,
    "insert_media_every": 3
}

DEFAULT_SERVER_STATE = {
    "selected_posters": [],
    "uploaded_media": [],
    "current_item": None,
    "slideshow_running": False,
    "slideshow_delay": 15000
}


os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def load_json_file(path, default_value):
    if not os.path.exists(path):
        return default_value
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default_value


def save_json_file(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_config():
    config = load_json_file(CONFIG_FILE, DEFAULT_CONFIG.copy())
    merged = DEFAULT_CONFIG.copy()
    merged.update(config)
    return merged


def save_config(data):
    save_json_file(CONFIG_FILE, data)


def load_server_state():
    state = load_json_file(STATE_FILE, DEFAULT_SERVER_STATE.copy())
    merged = DEFAULT_SERVER_STATE.copy()
    merged.update(state)
    return merged


def save_server_state():
    save_json_file(STATE_FILE, server_state)


server_state = load_server_state()


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def media_type_from_filename(filename):
    ext = filename.rsplit(".", 1)[1].lower()
    if ext == "mp4":
        return "video"
    return "image"


def get_api_key():
    return load_config().get("api_key", "").strip()


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def get_genres():
    api_key = get_api_key()
    if not api_key:
        return []

    response = requests.get(
        f"{BASE_URL}/genre/movie/list",
        params={"api_key": api_key},
        timeout=20
    )
    data = response.json()
    return data.get("genres", [])


def get_movies(page=1, genre=None, search=None, decade=None):
    api_key = get_api_key()
    if not api_key:
        return [], 1

    if search:
        url = f"{BASE_URL}/search/movie"
        params = {
            "api_key": api_key,
            "query": search,
            "page": page
        }
    else:
        url = f"{BASE_URL}/discover/movie"
        params = {
            "api_key": api_key,
            "page": page,
            "sort_by": "popularity.desc"
        }
        if genre:
            params["with_genres"] = genre

    if decade:
        start = int(decade)
        end = start + 9
        params["primary_release_date.gte"] = f"{start}-01-01"
        params["primary_release_date.lte"] = f"{end}-12-31"

    response = requests.get(url, params=params, timeout=20)
    data = response.json()
    movies = [m for m in data.get("results", []) if m.get("poster_path")]
    total_pages = min(data.get("total_pages", 1), 500)
    return movies, total_pages


def get_movies_for_genre_slideshow(genre_id, decade=None, max_pages=5):
    posters = []
    seen = set()

    for page in range(1, max_pages + 1):
        movies, _ = get_movies(page=page, genre=genre_id, decade=decade)
        for movie in movies:
            movie_id = movie.get("id")
            if movie_id in seen:
                continue
            seen.add(movie_id)
            posters.append({
                "id": str(movie_id),
                "title": movie.get("title", "Untitled"),
                "src": f"{FULL_IMAGE_BASE}{movie['poster_path']}",
                "thumb": f"{IMAGE_BASE}{movie['poster_path']}",
                "genre_ids": movie.get("genre_ids", []),
                "type": "poster",
                "show_now_playing": False
            })

    return posters


def build_mixed_playlist():
    selected = server_state.get("selected_posters", [])
    uploads = server_state.get("uploaded_media", [])
    config = load_config()
    insert_every = max(1, int(config.get("insert_media_every", 3)))

    if not uploads:
        return selected

    mixed = []
    upload_index = 0

    for i, poster in enumerate(selected, start=1):
        mixed.append(poster)

        if i % insert_every == 0 and uploads:
            mixed.append(uploads[upload_index % len(uploads)])
            upload_index += 1

    if not mixed and uploads:
        return uploads

    return mixed


@app.route("/")
def root():
    return redirect(url_for("admin"))


@app.route("/settings", methods=["GET", "POST"])
def settings():
    config = load_config()

    if request.method == "POST":
        config["api_key"] = request.form.get("api_key", "").strip()
        config["slideshow_delay"] = int(request.form.get("slideshow_delay", 15000))
        config["insert_media_every"] = int(request.form.get("insert_media_every", 3))
        save_config(config)

        server_state["slideshow_delay"] = config["slideshow_delay"]
        save_server_state()

        flash("Settings saved.")
        return redirect(url_for("settings"))

    return render_template("settings.html", config=config)


@app.route("/admin")
def admin():
    api_key = get_api_key()
    if not api_key:
        flash("Add your TMDb API key in Settings first.")
        return redirect(url_for("settings"))

    page = int(request.args.get("page", 1))
    genre = request.args.get("genre")
    search = request.args.get("search")
    decade = request.args.get("decade")

    genres = get_genres()
    movies, total_pages = get_movies(page=page, genre=genre, search=search, decade=decade)

    return render_template(
        "admin.html",
        movies=movies,
        genres=genres,
        page=page,
        total_pages=total_pages,
        genre=genre,
        search=search,
        decade=decade,
        image_base=IMAGE_BASE,
        full_image_base=FULL_IMAGE_BASE,
        local_ip=get_local_ip(),
        config=load_config()
    )


@app.route("/uploads", methods=["GET", "POST"])
def uploads():
    if request.method == "POST":
        file = request.files.get("file")
        if not file or not file.filename:
            flash("Choose a file first.")
            return redirect(url_for("uploads"))

        if not allowed_file(file.filename):
            flash("Only jpg, jpeg, png, webp, mp4 are allowed.")
            return redirect(url_for("uploads"))

        filename = secure_filename(file.filename)
        save_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(save_path)

        media_item = {
            "id": filename,
            "title": filename,
            "src": f"/static/uploads/{filename}",
            "thumb": f"/static/uploads/{filename}",
            "type": media_type_from_filename(filename),
            "show_now_playing": False
        }

        existing = [m for m in server_state["uploaded_media"] if m["id"] != filename]
        existing.append(media_item)
        server_state["uploaded_media"] = existing
        save_server_state()

        flash("File uploaded.")
        return redirect(url_for("uploads"))

    return render_template(
        "uploads.html",
        uploaded_media=server_state.get("uploaded_media", []),
        local_ip=get_local_ip()
    )


@app.route("/client")
def client():
    return render_template("client.html", local_ip=get_local_ip())


@app.route("/api/state")
def api_state():
    state = server_state.copy()
    if state.get("slideshow_running"):
        state["playlist"] = build_mixed_playlist()
    else:
        state["playlist"] = []
    return jsonify(state)


@app.route("/api/current", methods=["POST"])
def api_current():
    data = request.get_json(force=True)
    server_state["current_item"] = data
    save_server_state()
    return jsonify({"ok": True})


@app.route("/api/selected", methods=["POST"])
def api_selected():
    data = request.get_json(force=True)
    server_state["selected_posters"] = data.get("selected_posters", [])
    save_server_state()
    return jsonify({"ok": True})


@app.route("/api/remove_all", methods=["POST"])
def api_remove_all():
    server_state["selected_posters"] = []
    server_state["current_item"] = None
    server_state["slideshow_running"] = False
    save_server_state()
    return jsonify({"ok": True})


@app.route("/api/remove_upload", methods=["POST"])
def api_remove_upload():
    data = request.get_json(force=True)
    media_id = data.get("id")

    media_item = next((m for m in server_state["uploaded_media"] if m["id"] == media_id), None)
    if media_item:
        filename = media_item["src"].replace("/static/uploads/", "")
        path = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.exists(path):
            os.remove(path)

    server_state["uploaded_media"] = [m for m in server_state["uploaded_media"] if m["id"] != media_id]
    save_server_state()
    return jsonify({"ok": True})


@app.route("/api/save_delay", methods=["POST"])
def api_save_delay():
    data = request.get_json(force=True)
    delay_ms = int(data.get("delay", 15000))

    config = load_config()
    config["slideshow_delay"] = delay_ms
    save_config(config)

    server_state["slideshow_delay"] = delay_ms
    save_server_state()

    return jsonify({"ok": True})

@app.route("/api/slideshow/start", methods=["POST"])
def api_slideshow_start():
    data = request.get_json(force=True)
    config = load_config()

    server_state["selected_posters"] = data.get("selected_posters", server_state["selected_posters"])
    server_state["slideshow_delay"] = int(data.get("delay", config.get("slideshow_delay", 15000)))
    server_state["slideshow_running"] = True

    playlist = build_mixed_playlist()
    if playlist:
        server_state["current_item"] = playlist[0]

    save_server_state()
    return jsonify({"ok": True})


@app.route("/api/slideshow/stop", methods=["POST"])
def api_slideshow_stop():
    server_state["slideshow_running"] = False
    save_server_state()
    return jsonify({"ok": True})


@app.route("/api/genre_slideshow")
def api_genre_slideshow():
    genre_id = request.args.get("genre")
    decade = request.args.get("decade")
    max_pages = int(request.args.get("pages", 5))

    if not genre_id:
        return jsonify({"ok": False, "error": "Missing genre"}), 400

    posters = get_movies_for_genre_slideshow(genre_id=genre_id, decade=decade, max_pages=max_pages)
    return jsonify({"ok": True, "posters": posters})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5005)