from flask import Flask, render_template, jsonify, request, redirect
import os
import requests
import time
import psycopg2
import psycopg2.extras

app = Flask(__name__)

# -----------------------------
# CONFIG
# -----------------------------
PLACE_ID = 112233665771826

app.static_folder = 'static'
app.template_folder = 'templates'

DATABASE_URL = os.environ.get("DATABASE_URL")

# -----------------------------
# CACHE ROBLOX
# -----------------------------
cached_servers = []
last_fetch = 0
CACHE_DURATION = 30

# -----------------------------
# DB
# -----------------------------
def get_db():
    return psycopg2.connect(
        DATABASE_URL,
        cursor_factory=psycopg2.extras.RealDictCursor
    )

# -----------------------------
# INIT DB
# -----------------------------
def init_db():
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

init_db()

# -----------------------------
# LOAD
# -----------------------------
def load_servers():
    try:
        conn = get_db()
        cur = conn.cursor()

        cur.execute("SELECT * FROM servers")
        rows = cur.fetchall()

        cur.close()
        conn.close()

        servers = []
        for r in rows:
            server = dict(r)
            if not server.get("name"):
                server["name"] = "Server"
            servers.append(server)

        return servers

    except Exception as e:
        print("load_servers error:", e)
        return []

# -----------------------------
# SAFE UPSERT
# -----------------------------
def replace_servers(data):
    try:
        conn = get_db()
        cur = conn.cursor()

        cur.execute("DELETE FROM servers")

        for server in data:

            job_id = server.get("jobId")

            # 🔥 PROTECTION CRITIQUE
            if not job_id:
                continue

            cur.execute("""
                INSERT INTO servers (jobId, name, recordedAt, serverTimeAtRecord)
                VALUES (%s, %s, %s, %s)
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

            params = {
                "limit": 100,
                "sortOrder": "Asc"
            }

            if cursor:
                params["cursor"] = cursor

            response = requests.get(url, params=params, timeout=10)

            if response.status_code != 200:
                return []

            data = response.json()

            for s in data.get("data", []):

                job_id = s.get("id")

                # 🔥 FILTER STRICT
                if not job_id:
                    continue

                if job_id in seen:
                    continue

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
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/servers', methods=['GET'])
def get_servers():
    return jsonify(load_servers())

@app.route('/api/servers', methods=['POST'])
def save_servers_route():
    data = request.get_json()

    if not isinstance(data, list):
        return jsonify({"success": False}), 400

    replace_servers(data)
    return jsonify({"success": True})

@app.route('/api/refresh', methods=['POST'])
def refresh_servers():

    current_servers = load_servers()
    live_jobids = get_current_jobids()

    existing = {
        s["jobId"]: s
        for s in current_servers
        if "jobId" in s
    }

    new_servers = []

    for i, jobId in enumerate(live_jobids):

        if not jobId:
            continue

        server_data = existing.get(jobId, {
            "jobId": jobId
        }).copy()

        server_data["name"] = f"Server {i + 1}"

        new_servers.append(server_data)

    replace_servers(new_servers)

    return jsonify(new_servers)

@app.route('/join/<jobId>')
def join_server(jobId):
    return redirect(
        f"roblox://experiences/start?placeId={PLACE_ID}&gameInstanceId={jobId}"
    )

# -----------------------------
# MAIN
# -----------------------------
if __name__ == '__main__':
    os.makedirs('static', exist_ok=True)
    os.makedirs('templates', exist_ok=True)

    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
