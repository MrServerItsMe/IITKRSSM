# pip install -r requirements.txt
import webview
import json
import requests
import os
import platform
import subprocess
import ctypes
import sys
import threading

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

JSON_FILE = os.path.join(BASE_DIR, "servers.json")
INDEX_FILE = os.path.join(BASE_DIR, "index.html")
ICON_FILE = os.path.join(BASE_DIR, "Rayleigh.ico")

PLACE_ID = 112233665771826

myappid = 'rayleighfastchecker.1.0'
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

def load_servers():
    try:
        with open(JSON_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            for i, server in enumerate(data):
                if "name" not in server or not server.get("name"):
                    server["name"] = f"Server {i + 1}"
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_json(data):
    for i, server in enumerate(data):
        if "name" not in server or not server.get("name"):
            server["name"] = f"Server {i + 1}"
    
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def get_current_jobids():
    try:
        url = f"https://games.roblox.com/v1/games/{PLACE_ID}/servers/Public?limit=100"
        servers = []
        cursor = None
        while True:
            params = {"limit": 100}

            if cursor:
                params["cursor"] = cursor
            response = requests.get(url, params=params)
            data = response.json()

            for server in data.get("data", []):
                servers.append(server["id"])
            cursor = data.get("nextPageCursor")

            if not cursor:
                break

        return servers

    except Exception as e:
        print(f"Roblox server retrieval error: {e}")
        return []

class Api:
    def getServers(self):
        return load_servers()

    def saveServers(self, servers):
        save_json(servers)
        return True

    def refreshServers(self):
        try:
            current_servers = load_servers()
    
            live_jobids = get_current_jobids()
    
            existing = {s["jobId"]: s for s in current_servers}
    
            new_servers = []
    
            for index, jobId in enumerate(live_jobids):
                if jobId in existing:
                    server_data = existing[jobId]
                    server_data["name"] = f"Server {index + 1}"
    
                    new_servers.append(server_data)
    
                else:
                    new_servers.append({
                        "jobId": jobId,
                        "name": f"Server {index + 1}"
                    })
    
            save_json(new_servers)
    
            return new_servers
    
        except Exception as e:
            print(f"Erreur refresh: {e}")
            return []

    def joinServer(self, jobId):
        place_id = 112233665771826
        url = f"roblox://experiences/start?placeId={place_id}&gameInstanceId={jobId}"
        
        try:
            if platform.system() == "Windows":
                os.startfile(url)
            elif platform.system() == "Darwin":
                subprocess.run(["open", url])
            else:
                subprocess.run(["xdg-open", url])
            return True
        except Exception as e:
            print(f"Erreur join: {e}")
            return False

webview.create_window(
    "Rayleigh Fast Checker",
    INDEX_FILE,
    resizable=False,
    width=540,
    height=680,
    on_top=True,
    js_api=Api()
)



webview.start(icon=ICON_FILE)