from flask import Flask, render_template, jsonify, request, redirect
import os
import sqlite3
import requests
import time

app = Flask(__name__)

# -----------------------------
# CONFIG
# -----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "servers.db")
PLACE_ID = 112233665771826

app.static_folder = 'static'
app.template_folder = 'templates'

# -----------------------------
# CACHE ROBLOX API
# -----------------------------
cached_servers = []
last_fetch = 0
CACHE_DURATION = 30  # secondes

# -----------------------------
# DATABASE
# -----------------------------
def init_db():
    conn = sqlite3.connect(DB_FILE)

    conn.execute('''
        CREATE TABLE IF NOT EXISTS servers (
            jobId TEXT PRIMARY KEY,
            name TEXT,
            recordedAt TEXT,
            serverTimeAtRecord INTEGER
        )
    ''')

    conn.commit()
    conn.close()

init_db()

# -----------------------------
# LOAD SERVERS
# -----------------------------
def load_servers():
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row

        cursor = conn.execute("SELECT * FROM servers")
        servers = [dict(row) for row in cursor.fetchall()]

        conn.close()

        for server in servers:
            if not server.get("name"):
                server["name"] = "Server"

        return servers

    except Exception as e:
        print("load_servers error:", e)
        return []

# -----------------------------
# REPLACE SERVERS
# -----------------------------
def replace_servers(data):
    try:
        conn = sqlite3.connect(DB_FILE)

        conn.execute("DELETE FROM servers")

        for server in data:
            conn.execute('''
                INSERT INTO servers
                (jobId, name, recordedAt, serverTimeAtRecord)
                VALUES (?, ?, ?, ?)
            ''', (
                server.get("jobId"),
                server.get("name"),
                server.get("recordedAt"),
                server.get("serverTimeAtRecord")
            ))

        conn.commit()
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

        # cache
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

            response = requests.get(
                url,
                params=params,
                timeout=10
            )

            if response.status_code != 200:
                print("Roblox API error:", response.status_code)
                return []

            data = response.json()

            for server in data.get("data", []):

                job_id = server.get("id")

                # évite doublons MAIS garde ordre
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
        print("Erreur Roblox API:", e)
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

    if not data:
        return jsonify({
            "success": False,
            "error": "No data"
        }), 400

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

    for index, jobId in enumerate(live_jobids):
        server_data = existing.get(jobId, {
            "jobId": jobId
        }).copy()

        server_data["name"] = f"Server {index + 1}"

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
