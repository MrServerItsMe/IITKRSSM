let servers = [];
let currentSort = "event";

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
    if (!server.recordedAt || !server.serverTimeAtRecord) {
        return { 
            timerDisplay: "00:00", 
            timerColor: "#888", 
            currentServerTime: "Not defined",
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

    if (currentMod < 50) {
        minutesLeft = 50 - currentMod;
        timerColor = "#ff9800";
        status = "before";
    } else {
        minutesLeft = 60 - currentMod;
        timerColor = "#32cd32";
        status = "event";
    }

    return {
        timerDisplay: formatTime(minutesLeft),
        timerColor: timerColor,
        currentServerTime: formatServerTime(currentServerMinutes),
        minutesLeft: minutesLeft,
        status: status,
        currentServerMinutes: currentServerMinutes
    };
}

function sortServers(serversList) {
    const list = [...serversList];

    if (currentSort === "age") {
        list.sort((a, b) => {
            const infoA = getTimerInfo(a);
            const infoB = getTimerInfo(b);
            return (infoB.currentServerMinutes || 0) - (infoA.currentServerMinutes || 0);
        });
    } 
    else if (currentSort === "alpha") {
        list.sort((a, b) => naturalCompare(a.name, b.name));
    } 
    else {
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

function naturalCompare(a, b) {
    return a.localeCompare(b, undefined, { numeric: true, sensitivity: 'base' });
}

function renderServers() {
    const container = document.getElementById("servers");
    container.innerHTML = "";

    const sortedServers = sortServers(servers);

    sortedServers.forEach((server) => {
        const originalIndex = servers.findIndex(s => s.jobId === server.jobId);
        const info = getTimerInfo(server);

        container.innerHTML += `
            <div class="server-card">
                <h2>${server.name || "Server"}</h2>
                <p><strong>Job ID :</strong><br>${server.jobId}</p>

                <p>
                    <strong>Age server :</strong><br>
                    <span style="font-size: 1.1em; color: #bbbbbb;">
                        ${info.currentServerTime}
                    </span>
                </p>

                <p>
                    <strong>Next Event :</strong><br>
                    <span style="font-size: 1.6em; font-weight: bold; color: ${info.timerColor};">
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

async function editServer(index) {
    if (index < 0 || index >= servers.length) {
        alert("Erreur : server no found");
        return;
    }

    const input = prompt("Enter time of server (ex: 12h12) :", "");
    if (input === null) return;

    const serverMinutes = parseServerTime(input.trim());
    if (serverMinutes === null) {
        alert("invalid format ! (ex: 12h12)");
        return;
    }

    servers[index].recordedAt = new Date().toISOString();
    servers[index].serverTimeAtRecord = serverMinutes;

    renderServers();
    await window.pywebview.api.saveServers(servers);
}

async function joinServer(jobId) {
    await window.pywebview.api.joinServer(jobId);
}

async function refreshServers() {
    if (!confirm("Refresh list of server ?")) 
        return;
    
    const result = await window.pywebview.api.refreshServers();
    
    if (result && Array.isArray(result)) {
        servers = result;
        renderServers();
    } else {
        alert("Erreur lors du refresh.");
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
    setInterval(renderServers, 1000);
}

async function init() {
    servers = await window.pywebview.api.getServers();
    renderServers();
    startTimers();
}

window.addEventListener("pywebviewready", init);
