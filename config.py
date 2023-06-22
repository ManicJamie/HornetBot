import json

JSON_PATH = "config.json"
LOG_PATH = "hornet.log"
LOG_FOLDER = "logs"

with open(JSON_PATH) as f:
    data = json.load(f)

token = data["token"]
admins = data["admins"]
cache_size = data["cache_size"]

"""
Example config.json:
{
    "token" : "",
    "admins" : [
        1234567890,
        2345678901
    ]
}
"admins" are GLOBAL admins - this is unlikely to be used outside of alpha, and will likely be removed.
"""