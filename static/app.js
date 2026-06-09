// ======================
// LISTE DES NOMS PRÉDÉFINIS (INITIALISATION ICI)
// ======================
const predefinedNames = [
    "Banane", "Raspberry", "Kiwi", "Mango", "Avocat", "Ananas",
    "Pomme", "Cerise", "Orange", "Fraise", "Melon", "Pastèque",
    "Prune", "Pêche", "Mirabelle", "Pomme d'amour", "Noix de coco",
    "Citron vert", "Groseille", "Framboise", "Mûre", "Kaki",
    "Nashi", "Sapote", "Soursop", "Mango", "Papaye", "Figue",
    "Datte", "Amande", "Noix", "Aubergine", "Coco", "Mangue",
    "Cantaloup", "Pamplemousse", "Goyave", "Kiwi", "Litchi",
    "Longane", "Mandarine", "Maracuja", "Myrtille", "Nectarine",
    "Pêches", "Prunes", "Rhubarbe", "Tomate", "Cassis", "Groseille",
    "Myrtilles", "Raisins", "Kiwi"
];

let servers = [];
let assignedNames = new Map();   // jobId -> nom

// ======================
// EDIT SERVEUR (noms personnalisés)
// =====================-
async function editServer(jobId) {
    const serversList = await fetch('/api/servers').then(r => r.json());
    const server = serversList.find(s => s.jobId === jobId);
    if (!server) return;

    let currentName = server.name || "Server";
    const newName = prompt(`Changer le nom du serveur (Job ID: ${jobId})\n\nExemples : Banane, Raspberry, Pomme d'amour...`, currentName);

    if (!newName || newName.trim() === '') return;

    let cleanName = newName.trim().substring(0, 25);

    // Vérifie unicité
    const allNames = serversList.map(s => s.name);
    if (allNames.includes(cleanName) && cleanName !== currentName) {
        alert("❌ Ce nom est déjà utilisé !");
        return;
    }

    server.name = cleanName;
    await fetch('/api/servers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(serversList)
    });
    renderServers();
    alert("✅ Nom mis à jour !");
}

// ======================
// RENDU DES CARTES
// ======================
function renderServer(s) {
    const name = s.name || "Server";
    const info = getTimerInfo(s);   // tu dois garder ta fonction getTimerInfo

    const container = document.getElementById("servers");
    if (!container) return;

    container.innerHTML += `
        <div class="server-card">
            <h2>${name}</h2>
            <p><strong>Job ID :</strong><br>${s.jobId}</p>
            <p><strong>Age server :</strong><br>${info.currentServerTime}</p>
            <p><strong>Next Event :</strong><br><span style="color:${info.timerColor}">${info.timerDisplay}</span></p>
            <div class="buttons">
                <button class="join-btn" onclick="joinServer('${s.jobId}')">Join</button>
                <button class="edit-btn" onclick="editServer('${s.jobId}')">Edit</button>
            </div>
        </div>
    `;
}

function renderServers() {
    const container = document.getElementById("servers");
    if (!container) return;
    container.innerHTML = "";

    const sortedServers = sortServers(servers);

    sortedServers.forEach(server => renderServer(server));
}

// ... (garde tes fonctions getTimerInfo, sortServers, updateTimersOnly, refreshServers, joinServer, etc. que tu avais déjà dans le script.js)

function startTimers() {
    setInterval(updateTimersOnly, 1000);
    setInterval(() => refreshServers(true), 60 * 1000);
}

async function init() {
    try {
        const res = await fetch('/api/servers');
        servers = await res.json();
        renderServers();
        startTimers();
    } catch (e) {
        document.getElementById("servers").innerHTML = `<p style="color:red">Erreur</p>`;
    }
}

window.addEventListener("load", init);
