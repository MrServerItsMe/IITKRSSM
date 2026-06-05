from flask import Flask, render_template, jsonify, request
import json
import os
import sqlite3
import requests
from datetime import datetime

app = Flask(__name__)

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "servers.db")
PLACE_ID = 112233665771826

app.static_folder = 'static'
app.template_folder = 'templates'

# -----------------------------
# DATABASE SETUP
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

# Init DB au démarrage
init_db()

# -----------------------------
# LOAD / SAVE SERVERS
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


def save_servers(data):
    try:
        conn = sqlite3.connect(DB_FILE)
        for server in data:
            conn.execute('''
                INSERT OR REPLACE INTO servers 
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
        print("save_servers error:", e)


# -----------------------------
# ROBLOX API (inchangée)
# -----------------------------
def get_current_jobids():
    try:
        url = f"https://games.roblox.com/v1/games/{PLACE_ID}/servers/Public"
        servers_list = []
        cursor = None

        while True:
            params = {"limit": 100}
            if cursor:
                params["cursor"] = cursor

            response = requests.get(url, params=params, timeout=10)
            if response.status_code != 200:
                print("Roblox API error:", response.status_code)
                return []

            data = response.json()
            for server in data.get("data", []):
                job_id = server.get("id")
                if job_id:
                    servers_list.append(job_id)

            cursor = data.get("nextPageCursor")
            if not cursor:
                break

        return servers_list
    except Exception as e:
        print(f"Erreur Roblox API: {e}")
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
        return jsonify({"success": False, "error": "No data"}), 400

    save_servers(data)
    return jsonify({"success": True})


@app.route('/api/refresh', methods=['POST'])
def refresh_servers():
    current_servers = load_servers()
    live_jobids = get_current_jobids()

    existing = {s["jobId"]: s for s in current_servers if "jobId" in s}

    new_servers = []
    for index, jobId in enumerate(live_jobids):
        server_data = existing.get(jobId, {"jobId": jobId}).copy()
        server_data["name"] = f"Server {index + 1}"
        new_servers.append(server_data)

    save_servers(new_servers)
    return jsonify(new_servers)


@app.route('/api/join/<jobId>')
def join_server(jobId):
    url = f"roblox://experiences/start?placeId={PLACE_ID}&gameInstanceId={jobId}"
    return jsonify({"joinUrl": url})


# -----------------------------
# MAIN
# -----------------------------
if __name__ == '__main__':
    os.makedirs('static', exist_ok=True)
    os.makedirs('templates', exist_ok=True)
    print("🚀 Flask app running")
    app.run(host='0.0.0.0', port=5000, debug=True)
