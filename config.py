import json

JSON_PATH = "config.json"
LOG_PATH = "hornet.log"

with open(JSON_PATH) as f:
    data = json.load(f)

token = data["token"]
admins = data["admins"]