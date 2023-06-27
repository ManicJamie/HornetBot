import json

from components import src

JSON_PATH = "config.json"
LOG_PATH = "hornet.log"
LOG_FOLDER = "logs"

with open(JSON_PATH) as f:
    data = json.load(f)

token = data["token"]
admins = data["admins"]
cache_size = data["cache_size"]
src_api_key = data["src_api_key"]

if src_api_key != "":
    src.api.api_key = src_api_key

"""
Example config.json:
{
    "token" : "",
    "admins" : [
        1234567890,
        2345678901
    ],
    "cache_size": 1000000,
    "src_api_key": ""
}
"admins" are GLOBAL admins - this is unlikely to be used outside of alpha, and will likely be removed.
"""