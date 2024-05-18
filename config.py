import json

from discord import Colour

from components import src

JSON_PATH = "config.json"
LOG_PATH = "hornet.log"
LOG_FOLDER = "logs"
HORNET_COLOUR = Colour(0x79414B)

with open(JSON_PATH) as f:
    data: dict = json.load(f)

token: str = data["token"]
admins: list[str] = data.get("admins", [])
cache_size: int = data.get("cache_size", 1000)
src_api_key: str | None = data.get("src_api_key")
src_phpsessid: str | None = data.get("src_phpsessid")
twitch_api_id: str | None = data.get("twitch_api_id")
twitch_api_secret: str | None = data.get("twitch_api_secret")

if src_api_key is not None:
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
    "src_api_key": "", // Required for srroles & gameTracking using srcomapi
    "src_phpsessid": "", // Required for srcManagement using speedruncompy
    
}
"admins" are GLOBAL admins - this is unlikely to be used outside of alpha, and will likely be removed.
"""
