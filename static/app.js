let servers = [];
let currentSort = "event";

const EVENT_START = 50;

console.log("✅ app.js chargé");

/* -----------------------------
   UTILS
----------------------------- */

function escapeHtml(str) {
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function formatTime(minutes) {
    const min = Math.floor(minutes);
    const sec = Math.floor((minutes - min) * 60);
    return `${String(min).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
}

function formatServerTime(totalMinutes) {
    const hours = Math.floor(totalMinutes / 60);
    const minutes = Math.floor(totalMinutes % 60);
    return `${hours}h${String(minutes).padStart(2, "0")}`;
}

function parseServerTime(input) {
    const match = input.match(/^(\d+)h(\d{1,2})$/);
    if (!match) return null;

    const hours = parseInt(match[1]);
    const minutes = parseInt(match[2]);

    if (minutes > 59) return null;

    return hours * 60 + minutes;
}

/* -----------------------------
   TIMER LOGIC
----------------------------- */

function getTimerInfo(server) {
    if (!server?.recordedAt || !server?.serverTimeAtRecord) {
        return {
            timerDisplay: "00:00",
            timerColor: "#888",
            currentServerTime: "Non défini",
            minutesLeft: 9999,
            status: "unknown",
            currentServerMinutes: 0
        };
    }

    const recordedDate = new Date(server.recordedAt);
    const now = new Date();

    const elapsedMinutes = (now - recordedDate) / 60000;

    const currentServerMinutes =
        server.serverTimeAtRecord + elapsedMinutes;

    const currentMod = currentServerMinutes % 60;

    let minutesLeft, timerColor, status;

    if (currentMod < EVENT_START) {
        minutesLeft = EVENT_START - currentMod;
        timerColor = "#ff9800";
        status = "before";
    } else {
        minutesLeft = 60 - currentMod;
        timerColor = "#32cd32";
        status = "event";
    }

    return {
        timerDisplay: formatTime(minutesLeft),
        timerColor,
        currentServerTime: formatServerTime(currentServerMinutes),
        minutesLeft,
        status,
        currentServerMinutes
    };
}

/* -----------------------------
   SORTING
----------------------------- */

function sortServers(list) {
    const arr = [...list];

    if (currentSort === "age") {
        return arr.sort((a, b) =>
            getTimerInfo(b).currentServerMinutes -
            getTimerInfo(a).currentServerMinutes
        );
    }

    if (currentSort === "initial") {
        return arr; // ordre backend (Roblox API)
    }

    // default = event
    return arr.sort((a, b) => {
        const A = getTimerInfo(a);
        const B = getTimerInfo(b);

        if (A.status !== B.status) {
            return A.status === "event" ? -1 : 1;
        }

        return B.minutesLeft - A.minutesLeft;
    });
}

/* -----------------------------
   RENDER
----------------------------- */

function renderServers() {
    const container = document.getElementById("servers");
    if (!container) return;

    const sorted = sortServers(servers);

    container.innerHTML = sorted.map((server, i) => {
        const info = getTimerInfo(server);

        const originalIndex = servers.findIndex(
            s => s.jobId === server.jobId
        );

        return `
        <div class="server-card">

            <h2>${escapeHtml(server.name || "Server")}</h2>

            <p>
                <strong>Job ID :</strong><br>
                ${escapeHtml(server.jobId)}
            </p>

            <p>
                <strong>Age server :</strong><br>
                <span id="age-${server.jobId}">
                    ${info.currentServerTime}
                </span>
            </p>

            <p>
                <strong>Next Event :</strong><br>
                <span
                    id="timer-${server.jobId}"
                    style="color:${info.timerColor}; font-size:1.6em; font-weight:bold;"
                >
                    ${info.timerDisplay}
                </span>
            </p>

            <div class="buttons">

                <button onclick="joinServer('${server.jobId}')">
                    Join
                </button>

                <button onclick="editServer(${originalIndex})">
                    Edit
                </button>

            </div>

        </div>
        `;
    }).join("");
}

/* -----------------------------
   LIVE TIMER UPDATE
----------------------------- */

function updateTimersOnly() {
    for (const server of servers) {
        const info = getTimerInfo(server);

        const timerEl = document.getElementById(`timer-${server.jobId}`);
        const ageEl = document.getElementById(`age-${server.jobId}`);

        if (timerEl) {
            timerEl.textContent = info.timerDisplay;
            timerEl.style.color = info.timerColor;
        }

        if (ageEl) {
            ageEl.textContent = info.currentServerTime;
        }
    }
}

/* -----------------------------
   ACTIONS
----------------------------- */

function joinServer(jobId) {
    window.location.href = `/join/${jobId}`;
}

async function editServer(index) {
    const input = prompt("Temps du serveur (ex: 12h12) :");
    if (!input) return;

    const minutes = parseServerTime(input.trim());
    if (minutes === null) {
        return alert("Format invalide (ex: 12h12)");
    }

    servers[index].recordedAt = new Date().toISOString();
    servers[index].serverTimeAtRecord = minutes;

    renderServers();
    await saveServers();
}

function setSort(mode) {
    currentSort = mode;

    document.querySelectorAll(".sort-btn").forEach(btn => {
        btn.classList.toggle(
            "active",
            btn.dataset.sort === mode
        );
    });

    renderServers();
}

/* -----------------------------
   API
----------------------------- */

async function saveServers() {
    try {
        await fetch("/api/servers", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(servers)
        });
    } catch (e) {
        console.error("saveServers error", e);
    }
}

async function refreshServers(silent = false) {
    if (!silent) {
        if (!confirm("Rafraîchir les serveurs ?")) return;
    }

    try {
        const res = await fetch("/api/refresh", { method: "POST" });
        const data = await res.json();

        if (Array.isArray(data)) {
            servers = data;
            renderServers();
        }

    } catch (e) {
        console.error(e);
        if (!silent) alert("Erreur refresh");
    }
}

/* -----------------------------
   INIT
----------------------------- */

async function init() {
    try {
        const res = await fetch("/api/servers");
        servers = await res.json();

        renderServers();

        setInterval(updateTimersOnly, 1000);
        setInterval(() => refreshServers(true), 60000);

        console.log("✅ Init OK:", servers.length);

    } catch (e) {
        console.error(e);

        document.getElementById("servers").innerHTML =
            `<p style="color:red">Erreur backend</p>`;
    }
}

window.addEventListener("load", init);

/* -----------------------------
   EXPORT GLOBAL (IMPORTANT)
----------------------------- */

window.joinServer = joinServer;
window.editServer = editServer;
window.refreshServers = refreshServers;
window.setSort = setSort;
