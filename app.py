from flask import Flask, render_template, jsonify, request, redirect
import os
import requests
import time
import psycopg2
import psycopg2.extras
import sqlite3

app = Flask(__name__)
PLACE_ID = 112233665771826

app.static_folder = "static"
app.template_folder = "templates"

DATABASE_URL = os.environ.get("DATABASE_URL")

# -----------------------------
# FRUITS LISTE (exactement comme tu l’as donné)
# -----------------------------
FRUITS_LIST = [
    "Pomme", "Poire", "Banane", "Orange", "Mandarine", "Clémentine",
    "Citron", "Citron vert", "Pamplemousse", "Ananas", "Mangue", "Papaye",
    "Kiwi", "Fraise", "Framboise", "Myrtille", "Mûre", "Groseille",
    "Cerise", "Raisin", "Pastèque", "Melon", "Abricot", "Pêche",
    "Nectarine", "Prune", "Mirabelle", "Figue", "Datte", "Grenade",
    "Litchi", "Fruit de la passion", "Noix de coco", "Goyave", "Kaki",
    "Coing", "Cassis", "Rhubarbe", "Canneberge", "Kumquat"
]

# -----------------------------
# CACHE ROBLOX
# -----------------------------
cached_servers = []
last_fetch = 0
CACHE_DURATION = 30

# -----------------------------
# DB CONNECTION
# -----------------------------
def get_db():
    if not DATABASE_URL:
        conn = sqlite3.connect("local_dev.db")
        conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        return conn
    return psycopg2.connect(
        DATABASE_URL,
        cursor_factory=psycopg2.extras.RealDictCursor
    )

# -----------------------------
# INIT DB (fruits + associations uniques)
# -----------------------------
def init_db():
    try:
        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS servers (
                jobId TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                recordedAt TEXT,
                serverTimeAtRecord INTEGER,
                is_combined BOOLEAN DEFAULT FALSE
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS used_fruits (
                fruit TEXT PRIMARY KEY,
                is_combined BOOLEAN DEFAULT FALSE
            )
        """)

        # Initialisation fruits si vide
        cur.execute("SELECT COUNT(*) FROM used_fruits")
        if cur.fetchone()[0] == 0:
            for f in FRUITS_LIST:
                cur.execute("INSERT INTO used_fruits (fruit, is_combined) VALUES (%s, %s)", (f, False))
            conn.commit()

        cur.close()
        conn.close()
        print("✅ DB fruit initialised OK")
    except Exception as e:
        print("DB INIT ERROR:", e)

with app.app_context():
    init_db()

# -----------------------------
# CHARGEMENT DES NOMS (fruits uniques)
# -----------------------------
def load_servers():
    try:
        conn = get_db()
        cur = conn.cursor()

        cur.execute("SELECT * FROM servers")
        servers = cur.fetchall()

        cur.close()
        conn.close()

        for s in servers:
            for key in ["jobId", "jobid", "job_id"]:
                if key in s:
                    s["jobId"] = s.pop(key)
                    break
            if "recordedAt" not in s and "recordedat" in s:
                s["recordedAt"] = s.pop("recordedat")
            if "serverTimeAtRecord" not in s and "servertimeatrecord" in s:
                s["serverTimeAtRecord"] = s.pop("servertimeatrecord")

            if not s.get("name"):
                s["name"] = "Server"

        return servers
    except Exception as e:
        print("load_servers error:", e)
        return []

# -----------------------------
# REMPLACER LES SERVEURS (avec fruits uniques)
# -----------------------------
def replace_servers(data):
    try:
        conn = get_db()
        cur = conn.cursor()

        cur.execute("DELETE FROM servers")
        conn.commit()

        placeholder = "?" if not DATABASE_URL else "%s"

        for server in data:
            job_id = server.get("jobId")
            if not job_id:
                continue

            name = server.get("name", f"Server {job_id}")
            is_combined = server.get("is_combined", False)

            cur.execute(f"""
                INSERT INTO servers (jobId, name, recordedAt, serverTimeAtRecord, is_combined)
                VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
                ON CONFLICT (jobId) DO UPDATE SET
                    name = EXCLUDED.name,
                    is_combined = EXCLUDED.is_combined,
                    recordedAt = EXCLUDED.recordedAt,
                    serverTimeAtRecord = EXCLUDED.serverTimeAtRecord
            """, (job_id, name, server.get("recordedAt"), server.get("serverTimeAtRecord"), is_combined))

        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print("replace_servers error:", e)

# -----------------------------
# ROBLOX API (liste des jobId)
# -----------------------------
def get_current_jobids():
    global cached_servers, last_fetch
    try:
        now = time.time()
        if now - last_fetch < CACHE_DURATION:
            return cached_servers

        url = f"https://games.roblox.com/v1/games/{PLACE_ID}/servers/Public"
        servers_list = []
        seen = set()
        cursor = None

        while True:
            params = {"limit": 100, "sortOrder": "Asc"}
            if cursor:
                params["cursor"] = cursor
            r = requests.get(url, params=params, timeout=10)

            if r.status_code != 200:
                return []

            data = r.json()
            for server in data.get("data", []):
                job_id = server.get("id")
                if job_id and job_id not in seen:
                    seen.add(job_id)
                    servers_list.append(job_id)

            cursor = data.get("nextPageCursor")
            if not cursor:
                break

        cached_servers = servers_list
        last_fetch = now
        return servers_list
    except Exception as e:
        print("Roblox API error:", e)
        return []

# -----------------------------
# ROUTES
# -----------------------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/servers", methods=["GET"])
def api_get_servers():
    return jsonify(load_servers())

@app.route("/api/servers", methods=["POST"])
def api_save_servers():
    data = request.get_json()
    if not data:
        return jsonify({"success": False}), 400
    replace_servers(data)
    return jsonify({"success": True})

@app.route("/api/refresh", methods=["POST"])
def api_refresh():
    current = load_servers()
    live = get_current_jobids()

    # Fruit à nom (cache)
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT fruit, is_combined FROM used_fruits")
    fruit_db = {r[0]: r[1] for r in cur.fetchall()}
    cur.close()
    conn.close()

    existing = {s.get("jobId"): s for s in current if s.get("jobId")}

    new_servers = []
    for i, jobId in enumerate(live):
        s = dict(existing.get(jobId, {}))
        s["jobId"] = jobId
        s["name"] = f"Server {i + 1}"
        s["is_combined"] = False

        # Associer fruit
        if not fruit_db:
            s["name"] = f"Server {i + 1}"
        else:
            single = next((f for f, used in fruit_db.items() if not used), None)
            if single:
                s["name"] = single
                fruit_db[single] = True
            else:
                # Combinaison de 2 fruits
                combined = next((f for f, used in fruit_db.items() if not used), None)
                if combined:
                    s["name"] = f"{combined} Banane"  # exemple, tu peux changer l’ordre
                    fruit_db[combined] = True
                    s["is_combined"] = True

        new_servers.append(s)

    replace_servers(new_servers)
    return jsonify(new_servers)

@app.route("/join/<jobId>")
def join(jobId):
    return redirect(f"roblox://experiences/start?placeId={PLACE_ID}&gameInstanceId={jobId}")

# -----------------------------
# MAIN
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)
