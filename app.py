from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import requests
import socket
import json
import os

app = Flask(__name__)
app.secret_key = "posterdash-secret-key"

CONFIG_FILE = "config.json"
STATE_FILE = "state.json"

BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE = "https://image.tmdb.org/t/p/w500"
FULL_IMAGE_BASE = "https://image.tmdb.org/t/p/original"


DEFAULT_SERVER_STATE = {
    "selected_posters": [],
    "current_poster": None,
    "slideshow_running": False,
    "slideshow_delay": 15000
}


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


# ---------- SERVER STATE ----------

def load_server_state():
    state = load_json_file(STATE_FILE, DEFAULT_SERVER_STATE.copy())

    merged = DEFAULT_SERVER_STATE.copy()
    merged.update(state)

    return merged


def save_server_state():
    save_json_file(STATE_FILE, server_state)


server_state = load_server_state()


# ---------- CONFIG ----------

def load_config():
    return load_json_file(CONFIG_FILE, {"api_key": ""})


def save_config(data):
    save_json_file(CONFIG_FILE, data)


def get_api_key():
    config = load_config()
    return config.get("api_key", "").strip()


# ---------- NETWORK ----------

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


# ---------- TMDB ----------

def get_genres():
    api_key = get_api_key()
    if not api_key:
        return []

    url = f"{BASE_URL}/genre/movie/list"
    params = {"api_key": api_key}

    response = requests.get(url, params=params)
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

    response = requests.get(url, params=params)
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
                "id": movie_id,
                "title": movie.get("title", "Untitled"),
                "src": f"{FULL_IMAGE_BASE}{movie['poster_path']}",
                "thumb": f"{IMAGE_BASE}{movie['poster_path']}",
                "genre_ids": movie.get("genre_ids", [])
            })

    return posters


# ---------- ROUTES ----------

@app.route("/")
def root():
    return redirect(url_for("admin"))


@app.route("/settings", methods=["GET", "POST"])
def settings():
    config = load_config()

    if request.method == "POST":

        api_key = request.form.get("api_key", "").strip()

        config["api_key"] = api_key
        save_config(config)

        flash("API key saved")

        return redirect(url_for("settings"))

    return render_template(
        "settings.html",
        api_key=config.get("api_key", "")
    )


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

    movies, total_pages = get_movies(
        page=page,
        genre=genre,
        search=search,
        decade=decade
    )

    local_ip = get_local_ip()

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
        local_ip=local_ip
    )


@app.route("/client")
def client():
    local_ip = get_local_ip()
    return render_template("client.html", local_ip=local_ip)


# ---------- API ----------

@app.route("/api/state")
def api_state():
    return jsonify(server_state)


@app.route("/api/current", methods=["POST"])
def api_current():

    data = request.get_json(force=True)

    server_state["current_poster"] = data

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
    server_state["current_poster"] = None
    server_state["slideshow_running"] = False

    save_server_state()

    return jsonify({"ok": True})


@app.route("/api/slideshow/start", methods=["POST"])
def api_slideshow_start():

    data = request.get_json(force=True)

    server_state["selected_posters"] = data.get(
        "selected_posters",
        server_state["selected_posters"]
    )

    server_state["slideshow_delay"] = int(data.get("delay", 15000))
    server_state["slideshow_running"] = True

    if server_state["selected_posters"]:
        server_state["current_poster"] = server_state["selected_posters"][0]

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
        return jsonify({"ok": False})

    posters = get_movies_for_genre_slideshow(
        genre_id=genre_id,
        decade=decade,
        max_pages=max_pages
    )

    return jsonify({
        "ok": True,
        "posters": posters
    })


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5005)