let slideshowIndex = 0;
let currentSlideshowSignature = "";
let lastManualPosterSrc = null;
let lastSlideChangeTime = 0;

const waitingScreen = document.getElementById("waitingScreen");
const clientPosterWrap = document.getElementById("clientPosterWrap");
const clientPoster = document.getElementById("clientPoster");
const clientGlow = document.getElementById("clientGlow");
const nowPlayingInside = document.getElementById("nowPlayingInside");

function forceFullscreen() {
    const el = document.documentElement;

    if (el.requestFullscreen) {
        el.requestFullscreen().catch(() => {});
    }
}

window.addEventListener("load", () => {
    forceFullscreen();
});

function hashColorFromText(text) {
    let hash = 0;
    for (let i = 0; i < text.length; i++) {
        hash = text.charCodeAt(i) + ((hash << 5) - hash);
    }
    const hue = Math.abs(hash % 360);
    return `hsla(${hue}, 85%, 55%, 0.45)`;
}

function setPosterVisuals(poster) {

    if (!poster || !poster.src) {
        waitingScreen.classList.remove("hidden");
        clientPosterWrap.classList.add("hidden");
        return;
    }

    waitingScreen.classList.add("hidden");
    clientPosterWrap.classList.remove("hidden");

    clientPoster.classList.add("poster-fade-out");

    setTimeout(() => {

        clientPoster.src = poster.src;
        clientPoster.alt = poster.title || "Poster";

        const c1 = hashColorFromText((poster.title || "poster") + "a");
        const c2 = hashColorFromText((poster.title || "poster") + "b");

        clientGlow.style.background = `
            radial-gradient(circle at 30% 30%, ${c1}, transparent 45%),
            radial-gradient(circle at 70% 70%, ${c2}, transparent 45%)
        `;

        if (poster.show_now_playing) {
            nowPlayingInside.textContent = `Now Playing: ${poster.title || "Poster"}`;
            nowPlayingInside.classList.remove("hidden");
        } else {
            nowPlayingInside.textContent = "";
            nowPlayingInside.classList.add("hidden");
        }

        clientPoster.classList.remove("poster-fade-out");
        clientPoster.classList.add("poster-fade-in");

    }, 400);
}

function buildSlideshowSignature(posters) {
    return posters.map((p) => p.src).join("|");
}

async function pollState() {
    try {
        const response = await fetch("/api/state", { cache: "no-store" });
        const state = await response.json();

        if (state.slideshow_running && state.selected_posters.length > 0) {
            const posters = state.selected_posters;
            const signature = buildSlideshowSignature(posters);
            const delay = Number(state.slideshow_delay) || 15000;
            const now = Date.now();

            if (signature !== currentSlideshowSignature) {
                currentSlideshowSignature = signature;
                slideshowIndex = 0;
                lastSlideChangeTime = now;
                setPosterVisuals(posters[slideshowIndex]);
                lastManualPosterSrc = null;
                return;
            }

            if (slideshowIndex >= posters.length) {
                slideshowIndex = 0;
            }

            if (now - lastSlideChangeTime >= delay) {
                slideshowIndex = (slideshowIndex + 1) % posters.length;
                lastSlideChangeTime = now;
                setPosterVisuals(posters[slideshowIndex]);
            } else if (!clientPoster.src) {
                setPosterVisuals(posters[slideshowIndex]);
            }

            lastManualPosterSrc = null;
            return;
        }

        currentSlideshowSignature = "";
        slideshowIndex = 0;
        lastSlideChangeTime = 0;

        if (state.current_poster && state.current_poster.src) {
            if (lastManualPosterSrc !== state.current_poster.src) {
                setPosterVisuals(state.current_poster);
                lastManualPosterSrc = state.current_poster.src;
            } else if (state.current_poster.show_now_playing) {
                setPosterVisuals(state.current_poster);
            }
        } else {
            setPosterVisuals(null);
            lastManualPosterSrc = null;
        }
    } catch (error) {
        console.error("Client poll failed:", error);
    }
}

setInterval(pollState, 1000);
pollState();