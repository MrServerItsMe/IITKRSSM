from flask import Flask, render_template, jsonify, request, redirect
import os
import requests
import time
import psycopg2
import psycopg2.extras
import sqlite3

app = Flask(__name__)

# -----------------------------
# CONFIG
# -----------------------------
PLACE_ID = 112233665771826

app.static_folder = "static"
app.template_folder = "templates"

DATABASE_URL = os.environ.get("DATABASE_URL")

# -----------------------------
# CACHE ROBLOX API
# -----------------------------
cached_servers = []
last_fetch = 0
CACHE_DURATION = 30

# -----------------------------
# DB CONNECTION (SAFE)
# -----------------------------
def get_db():
    if not DATABASE_URL:
        # Fallback to SQLite for local development
        conn = sqlite3.connect("local_dev.db")
        conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        return conn

    return psycopg2.connect(
        DATABASE_URL,
        cursor_factory=psycopg2.extras.RealDictCursor
    )

# -----------------------------
# INIT DB
# -----------------------------
def init_db():
    try:
        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS servers (
                jobId TEXT PRIMARY KEY,
                name TEXT,
                recordedAt TEXT,
                serverTimeAtRecord INTEGER
            )
        """)

        conn.commit()
        cur.close()
        conn.close()

        print("DB INIT OK")

    except Exception as e:
        print("DB INIT ERROR:", e)

# Run DB init on startup (Render safe)
with app.app_context():
    init_db()

# -----------------------------
# LOAD SERVERS
# -----------------------------
def load_servers():
    try:
        conn = get_db()
        cur = conn.cursor()

        cur.execute("SELECT * FROM servers")
        servers = cur.fetchall()

        cur.close()
        conn.close()

        # normalize keys (IMPORTANT PostgreSQL safety)
        for s in servers:
            s["jobId"] = s.get("jobId") or s.get("jobid") or s.get("job_id")
            
            recorded_at = s.get("recordedAt")
            if recorded_at is None:
                recorded_at = s.get("recordedat")
            s["recordedAt"] = recorded_at
            
            server_time = s.get("serverTimeAtRecord")
            if server_time is None:
                server_time = s.get("servertimeatrecord")
            s["serverTimeAtRecord"] = server_time
            
            if not s.get("name"):
                s["name"] = "Server"

        return servers

    except Exception as e:
        print("load_servers error:", e)
        return []

# -----------------------------
# REPLACE SERVERS (SAFE UPSERT)
# -----------------------------
def replace_servers(data):
    try:
        conn = get_db()
        cur = conn.cursor()

        cur.execute("DELETE FROM servers")

        placeholder = "?" if not DATABASE_URL else "%s"

        for server in data:
            job_id = server.get("jobId")
            if not job_id:
                continue

            cur.execute(f"""
                INSERT INTO servers (jobId, name, recordedAt, serverTimeAtRecord)
                VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder})
                ON CONFLICT (jobId) DO UPDATE SET
                    name = EXCLUDED.name,
                    recordedAt = EXCLUDED.recordedAt,
                    serverTimeAtRecord = EXCLUDED.serverTimeAtRecord
            """, (
                job_id,
                server.get("name"),
                server.get("recordedAt"),
                server.get("serverTimeAtRecord")
            ))

        conn.commit()
        cur.close()
        conn.close()

    except Exception as e:
        print("replace_servers error:", e)

# -----------------------------
# ROBLOX API
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

    existing = {s.get("jobId"): s for s in current if s.get("jobId")}

    new_servers = []

    for i, jobId in enumerate(live):
        s = dict(existing.get(jobId, {}))

        s["jobId"] = jobId
        s["name"] = f"Server {i + 1}"

        new_servers.append(s)

    replace_servers(new_servers)

    return jsonify(new_servers)

@app.route("/join/<jobId>")
def join(jobId):
    return redirect(
        f"roblox://experiences/start?placeId={PLACE_ID}&gameInstanceId={jobId}"
    )

# -----------------------------
# MAIN
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)
