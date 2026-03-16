let slideshowIndex = 0;
let currentPlaylistSignature = "";
let lastManualItemSrc = null;
let lastSlideChangeTime = 0;
let isAnimating = false;

const waitingScreen = document.getElementById("waitingScreen");
const clientPosterWrap = document.getElementById("clientPosterWrap");
const clientGlow = document.getElementById("clientGlow");
const nowPlayingInside = document.getElementById("nowPlayingInside");

const currentPosterEl = document.getElementById("clientPosterCurrent");
const nextPosterEl = document.getElementById("clientPosterNext");
const currentVideoEl = document.getElementById("clientVideoCurrent");

function hashColorFromText(text) {
    let hash = 0;
    for (let i = 0; i < text.length; i++) {
        hash = text.charCodeAt(i) + ((hash << 5) - hash);
    }
    const hue = Math.abs(hash % 360);
    return `hsla(${hue}, 85%, 55%, 0.45)`;
}

function updateGlowAndLabel(item) {
    const c1 = hashColorFromText((item.title || "poster") + "a");
    const c2 = hashColorFromText((item.title || "poster") + "b");

    clientGlow.style.background = `
        radial-gradient(circle at 30% 30%, ${c1}, transparent 45%),
        radial-gradient(circle at 70% 70%, ${c2}, transparent 45%)
    `;

    if (item.show_now_playing) {
        nowPlayingInside.textContent = `Now Playing: ${item.title || "Poster"}`;
        nowPlayingInside.classList.remove("hidden");
    } else {
        nowPlayingInside.textContent = "";
        nowPlayingInside.classList.add("hidden");
    }
}

function showImageItem(item) {
    currentVideoEl.classList.add("hidden");
    currentVideoEl.pause();
    currentVideoEl.removeAttribute("src");
    currentVideoEl.load();

    currentPosterEl.classList.remove("hidden");
    nextPosterEl.classList.remove("hidden");

    currentPosterEl.src = item.src;
    currentPosterEl.alt = item.title || "Poster";
    nextPosterEl.src = "";
    currentPosterEl.classList.remove("poster-slide-current-out");
    nextPosterEl.classList.remove("poster-slide-next-in");

    updateGlowAndLabel(item);
}

function showVideoItem(item) {
    currentPosterEl.classList.add("hidden");
    nextPosterEl.classList.add("hidden");

    currentVideoEl.classList.remove("hidden");
    currentVideoEl.src = item.src;
    currentVideoEl.load();
    currentVideoEl.play().catch(() => {});

    updateGlowAndLabel(item);
}

function setItemImmediate(item) {
    if (!item || !item.src) {
        waitingScreen.classList.remove("hidden");
        clientPosterWrap.classList.add("hidden");
        return;
    }

    waitingScreen.classList.add("hidden");
    clientPosterWrap.classList.remove("hidden");

    if (item.type === "video") {
        showVideoItem(item);
    } else {
        showImageItem(item);
    }
}

function slideToImageItem(item) {
    if (!item || !item.src || isAnimating) return;

    waitingScreen.classList.add("hidden");
    clientPosterWrap.classList.remove("hidden");

    if (item.type === "video") {
        setItemImmediate(item);
        return;
    }

    currentVideoEl.classList.add("hidden");
    currentVideoEl.pause();

    currentPosterEl.classList.remove("hidden");
    nextPosterEl.classList.remove("hidden");

    isAnimating = true;

    nextPosterEl.src = item.src;
    nextPosterEl.alt = item.title || "Poster";

    nextPosterEl.classList.remove("poster-slide-next-in");
    currentPosterEl.classList.remove("poster-slide-current-out");
    void nextPosterEl.offsetHeight;

    currentPosterEl.classList.add("poster-slide-current-out");
    nextPosterEl.classList.add("poster-slide-next-in");

    updateGlowAndLabel(item);

    setTimeout(() => {
        currentPosterEl.src = item.src;
        currentPosterEl.alt = item.title || "Poster";
        currentPosterEl.classList.remove("poster-slide-current-out");
        nextPosterEl.classList.remove("poster-slide-next-in");
        nextPosterEl.src = "";
        isAnimating = false;
    }, 950);
}

function buildPlaylistSignature(items) {
    return items.map((p) => `${p.type}:${p.src}`).join("|");
}

async function pollState() {
    try {
        const response = await fetch("/api/state", { cache: "no-store" });
        const state = await response.json();

        if (state.slideshow_running && state.playlist.length > 0) {
            const items = state.playlist;
            const signature = buildPlaylistSignature(items);
            const delay = Number(state.slideshow_delay) || 15000;
            const now = Date.now();

            if (signature !== currentPlaylistSignature) {
                currentPlaylistSignature = signature;
                slideshowIndex = 0;
                lastSlideChangeTime = now;
                setItemImmediate(items[slideshowIndex]);
                lastManualItemSrc = null;
                return;
            }

            if (slideshowIndex >= items.length) slideshowIndex = 0;

            if (now - lastSlideChangeTime >= delay && !isAnimating) {
                slideshowIndex = (slideshowIndex + 1) % items.length;
                lastSlideChangeTime = now;
                slideToImageItem(items[slideshowIndex]);
            }
            return;
        }

        currentPlaylistSignature = "";
        slideshowIndex = 0;
        lastSlideChangeTime = 0;

        if (state.current_item && state.current_item.src) {
            if (lastManualItemSrc !== state.current_item.src) {
                setItemImmediate(state.current_item);
                lastManualItemSrc = state.current_item.src;
            } else if (state.current_item.show_now_playing) {
                updateGlowAndLabel(state.current_item);
            }
        } else {
            waitingScreen.classList.remove("hidden");
            clientPosterWrap.classList.add("hidden");
            lastManualItemSrc = null;
        }
    } catch (error) {
        console.error("Client poll failed:", error);
    }
}

setInterval(pollState, 1000);
pollState();