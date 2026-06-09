let servers = [];
let currentSort = "event";

const EVENT_START = 50;

console.log("✅ app.js chargé (fruit names)");

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

function getTimerInfo(server) {
    if (!server || !server.recordedAt || !server.serverTimeAtRecord) {
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
    const currentServerMinutes = server.serverTimeAtRecord + elapsedMinutes;
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

function sortServers(serversList) {
    const list = [...serversList];
    if (currentSort === "age") {
        list.sort((a, b) =>
            (getTimerInfo(b).currentServerMinutes || 0) -
            (getTimerInfo(a).currentServerMinutes || 0)
        );
    } else if (currentSort === "initial") {
        return list;
    } else {
        list.sort((a, b) => {
            const infoA = getTimerInfo(a);
            const infoB = getTimerInfo(b);
            if (infoA.status === "event" && infoB.status !== "event") return -1;
            if (infoB.status === "event" && infoA.status !== "event") return 1;
            if (infoA.status === "event" && infoB.status === "event") {
                return infoB.minutesLeft - infoA.minutesLeft;
            }
            return infoA.minutesLeft - infoB.minutesLeft;
        });
    }
    return list;
}

function renderServers() {
    const container = document.getElementById("servers");
    if (!container) return;
    container.innerHTML = "";

    const sortedServers = sortServers(servers);

    sortedServers.forEach((server) => {
        const originalIndex = servers.findIndex(s => s.jobId === server.jobId);
        const info = getTimerInfo(server);

        const displayName = server.fruit || (server.name || "Server");
        const fruit = server.fruit || "";

        container.innerHTML += `
            <div class="server-card">
                <h2>${escapeHtml(displayName)}</h2>
                <p><strong>Job ID :</strong><br>${escapeHtml(server.jobId)}</p>
                <p><strong>Age server :</strong><br>
                    <span id="age-${server.jobId}" style="font-size: 1.1em; color: #bbbbbb;">
                        ${info.currentServerTime}
                    </span>
                </p>
                <p><strong>Next Event :</strong><br>
                    <span id="timer-${server.jobId}"
                        style="font-size: 1.6em; font-weight: bold; color: ${info.timerColor};">
                        ${info.timerDisplay}
                    </span>
                </p>
                <div class="buttons">
                    <button class="join-btn" onclick="joinServer('${server.jobId}')">Join</button>
                    <button class="edit-btn" onclick="editServer(${originalIndex})">Edit</button>
                </div>
            </div>
        `;
    });
}

function updateTimersOnly() {
    servers.forEach(server => {
        const info = getTimerInfo(server);
        const timerEl = document.getElementById(`timer-${server.jobId}`);
        const ageEl = document.getElementById(`age-${server.jobId}`);

        if (timerEl) {
            timerEl.textContent = info.timerDisplay;
            timerEl.style.color = info.timerColor;
        }
        if (ageEl) ageEl.textContent = info.currentServerTime;
    });
}

async function editServer(index) {
    if (index < 0 || index >= servers.length) return alert("Server introuvable");

    const input = prompt("Temps du serveur (ex: 12h12) :", "");
    if (!input) return;

    const serverMinutes = parseServerTime(input.trim());
    if (serverMinutes === null) {
        return alert("Format invalide ! Exemple : 12h12");
    }

    servers[index].recordedAt = new Date().toISOString();
    servers[index].serverTimeAtRecord = serverMinutes;
    renderServers();
    await saveServers();
}

function joinServer(jobId) {
    window.location.href = `/join/${jobId}`;
}

async function saveServers() {
    try {
        await fetch('/api/servers', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(servers)
        });
    } catch (e) {
        console.error("Erreur sauvegarde", e);
    }
}

async function refreshServers(silent = false) {
    if (!silent) {
        const confirmRefresh = confirm("Rafraîchir la liste des serveurs ?");
        if (!confirmRefresh) return;
    }

    try {
        const res = await fetch('/api/refresh', { method: 'POST' });
        const result = await res.json();
        if (Array.isArray(result)) {
            servers = result;
            renderServers();
        }
    } catch (e) {
        console.error(e);
        if (!silent) alert("Erreur lors du refresh.");
    }
}

function setSort(mode) {
    currentSort = mode;
    document.querySelectorAll('.sort-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.sort === mode);
    });
    renderServers();
}

function startTimers() {
    setInterval(updateTimersOnly, 1000);
    setInterval(() => refreshServers(true), 60000);
}

async function init() {
    try {
        const res = await fetch('/api/servers');
        servers = await res.json();
        renderServers();
        startTimers();
        console.log("✅ Application initialisée avec", servers.length, "serveurs");
    } catch (e) {
        console.error("Erreur chargement serveurs", e);
        document.getElementById("servers").innerHTML = `
            <p style="color:red;text-align:center">Erreur de connexion au backend</p>
        `;
    }
}

window.addEventListener("load", init);
