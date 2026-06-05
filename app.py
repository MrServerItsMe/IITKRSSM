from flask import Flask, render_template, jsonify, request
import json
import os
import requests

app = Flask(__name__)

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_FILE = os.path.join(BASE_DIR, "servers.json")
PLACE_ID = 112233665771826


# -----------------------------
# LOAD / SAVE SERVERS
# -----------------------------
def load_servers():
    try:
        if not os.path.exists(JSON_FILE):
            return []

        with open(JSON_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            return []

        for i, server in enumerate(data):
            if "name" not in server or not server.get("name"):
                server["name"] = f"Server {i + 1}"

        return data

    except Exception as e:
        print("load_servers error:", e)
        return []


def save_servers(data):
    try:
        if not isinstance(data, list):
            return

        for i, server in enumerate(data):
            if "name" not in server or not server.get("name"):
                server["name"] = f"Server {i + 1}"

        with open(JSON_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    except Exception as e:
        print("save_servers error:", e)


# -----------------------------
# ROBLOX API
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

    existing = {}
    for s in current_servers:
        if isinstance(s, dict) and "jobId" in s:
            existing[s["jobId"]] = s

    new_servers = []

    for index, jobId in enumerate(live_jobids):
        if jobId in existing:
            server_data = existing[jobId].copy()
        else:
            server_data = {"jobId": jobId}

        server_data["name"] = f"Server {index + 1}"
        new_servers.append(server_data)

    save_servers(new_servers)
    return jsonify(new_servers)


@app.route('/api/join/<jobId>')
def join_server(jobId):
    url = f"roblox://experiences/start?placeId={PLACE_ID}&gameInstanceId={jobId}"
    return jsonify({"joinUrl": url})


# -----------------------------
# MAIN (LOCAL ONLY)
# -----------------------------
if __name__ == '__main__':
    os.makedirs('static', exist_ok=True)
    os.makedirs('templates', exist_ok=True)

    print("🚀 Flask app running locally")

    app.run(host='0.0.0.0', port=5000, debug=True)
