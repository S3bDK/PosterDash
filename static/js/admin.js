let pickedPosters = [];
const slideshowDelay = 25000;

const selectedPostersList = document.getElementById("selectedPostersList");
const selectionCount = document.getElementById("selectionCount");
const slideshowGenreSelect = document.getElementById("slideshowGenreSelect");
const slideshowPagesSelect = document.getElementById("slideshowPagesSelect");
const searchForm = document.getElementById("searchForm");
const genreFilter = document.getElementById("genreFilter");
const decadeFilter = document.getElementById("decadeFilter");

function normalizeGenreIds(rawGenreIds) {
    if (!rawGenreIds) return [];
    return rawGenreIds.split(",").map(x => x.trim()).filter(Boolean);
}

async function pushSelectedToServer() {
    await fetch("/api/selected", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ selected_posters: pickedPosters })
    });
}

async function showNowPoster(poster) {
    await fetch("/api/current", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            ...poster,
            show_now_playing: true
        })
    });
}

function updateSelectionCount() {
    selectionCount.textContent = `${pickedPosters.length} selected`;
}

function updateSelectedPanel() {
    selectedPostersList.innerHTML = "";

    if (pickedPosters.length === 0) {
        selectedPostersList.innerHTML = `<p class="selected-empty">No posters selected yet.</p>`;
        updateSelectionCount();
        return;
    }

    pickedPosters.forEach((poster) => {
        const item = document.createElement("div");
        item.className = "selected-item";

        item.innerHTML = `
            <img src="${poster.thumb || poster.src}" alt="${poster.title}">
            <div class="selected-item-content">
                <p>${poster.title}</p>
                <button type="button" class="btn btn-secondary remove-selected-btn">Remove</button>
            </div>
        `;

        item.querySelector("img").addEventListener("click", async () => {
            await showNowPoster(poster);
        });

        item.querySelector(".remove-selected-btn").addEventListener("click", async () => {
            await removePosterBySrc(poster.src);
        });

        selectedPostersList.appendChild(item);
    });

    updateSelectionCount();
}

function setCardSelectedState(id, isSelected) {
    const card = document.getElementById("movie" + id);
    const button = document.querySelector(`.select-btn[data-id="${id}"]`);

    if (card) {
        card.classList.toggle("selected", isSelected);
    }
    if (button) {
        button.textContent = isSelected ? "Remove" : "Select";
    }
}

async function togglePoster(button) {
    const id = button.dataset.id;
    const src = button.dataset.src;
    const thumb = button.dataset.thumb;
    const title = button.dataset.title;
    const genreIds = normalizeGenreIds(button.dataset.genreIds);

    const index = pickedPosters.findIndex((p) => p.src === src);

    if (index === -1) {
        pickedPosters.push({ id, src, thumb, title, genreIds });
        setCardSelectedState(id, true);
    } else {
        pickedPosters.splice(index, 1);
        setCardSelectedState(id, false);
    }

    updateSelectedPanel();
    await pushSelectedToServer();
}

async function removePosterBySrc(src) {
    const poster = pickedPosters.find((p) => p.src === src);
    pickedPosters = pickedPosters.filter((p) => p.src !== src);

    if (poster) {
        setCardSelectedState(poster.id, false);
    }

    updateSelectedPanel();
    await pushSelectedToServer();
}

async function removeAllPosters() {
    pickedPosters = [];

    document.querySelectorAll(".movie").forEach((card) => {
        card.classList.remove("selected");
    });

    document.querySelectorAll(".select-btn").forEach((button) => {
        button.textContent = "Select";
    });

    updateSelectedPanel();

    await fetch("/api/remove_all", {
        method: "POST"
    });
}

async function startSlideshow() {
    let postersForSlideshow = [...pickedPosters];

    const selectedGenre = slideshowGenreSelect.value;
    const selectedPages = slideshowPagesSelect.value;

    if (selectedGenre) {
        const params = new URLSearchParams({
            genre: selectedGenre,
            pages: selectedPages
        });

        const response = await fetch(`/api/genre_slideshow?${params.toString()}`);
        const data = await response.json();

        if (!data.ok || !data.posters.length) {
            alert("No posters found for that genre.");
            return;
        }

        postersForSlideshow = data.posters.map((p) => ({
            ...p,
            id: String(p.id),
            show_now_playing: false
        }));

        pickedPosters = postersForSlideshow.map((p) => ({ ...p }));

        document.querySelectorAll(".movie").forEach((card) => {
            card.classList.remove("selected");
        });

        document.querySelectorAll(".select-btn").forEach((button) => {
            button.textContent = "Select";
        });

        pickedPosters.forEach((poster) => {
            setCardSelectedState(String(poster.id), true);
        });

        updateSelectedPanel();
        await pushSelectedToServer();
    }

    if (!postersForSlideshow.length) {
        alert("Select some posters first.");
        return;
    }

    postersForSlideshow = postersForSlideshow.map((poster) => ({
        ...poster,
        show_now_playing: false
    }));

    await fetch("/api/slideshow/start", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            selected_posters: postersForSlideshow,
            delay: slideshowDelay
        })
    });
}

async function stopSlideshow() {
    await fetch("/api/slideshow/stop", {
        method: "POST"
    });
}

async function restoreSelectedFromServer() {
    try {
        const response = await fetch("/api/state", { cache: "no-store" });
        const state = await response.json();

        pickedPosters = Array.isArray(state.selected_posters) ? state.selected_posters : [];

        document.querySelectorAll(".movie").forEach((card) => {
            card.classList.remove("selected");
        });

        document.querySelectorAll(".select-btn").forEach((button) => {
            button.textContent = "Select";
        });

        pickedPosters.forEach((poster) => {
            if (poster.id) {
                setCardSelectedState(String(poster.id), true);
            } else {
                const match = document.querySelector(`.select-btn[data-src="${CSS.escape(poster.src)}"]`);
                if (match) {
                    setCardSelectedState(String(match.dataset.id), true);
                }
            }
        });

        updateSelectedPanel();
    } catch (error) {
        console.error("Failed to restore selected posters:", error);
        updateSelectedPanel();
    }
}

document.querySelectorAll(".select-btn").forEach((button) => {
    button.addEventListener("click", async (event) => {
        event.stopPropagation();
        await togglePoster(button);
    });
});

document.querySelectorAll(".show-now-btn").forEach((button) => {
    button.addEventListener("click", async () => {
        await showNowPoster({
            id: button.dataset.id,
            src: button.dataset.src,
            thumb: button.dataset.thumb,
            title: button.dataset.title
        });
    });
});

document.getElementById("startSlideshowBtn").addEventListener("click", startSlideshow);
document.getElementById("stopSlideshowBtn").addEventListener("click", stopSlideshow);
document.getElementById("removeAllBtn").addEventListener("click", removeAllPosters);

if (genreFilter) {
    genreFilter.addEventListener("change", () => {
        searchForm.submit();
    });
}

if (decadeFilter) {
    decadeFilter.addEventListener("change", () => {
        searchForm.submit();
    });
}

restoreSelectedFromServer();