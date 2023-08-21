from typing import Optional
import config, logging, re
from twitchAPI import *
from twitchAPI.object import Video
from twitchAPI.helper import first
from twitchAPI.types import AuthScope, VideoType

_log = logging.getLogger("twitch")

api: Twitch = None

TWITCH_ID_MATCH: re.Pattern = re.compile("^\d{9,11}$")

if not config.twitch_api_id:
    _log.warn("Config twitch_api_id not provided! Twitch component calls will not work!")
if not config.twitch_api_secret:
    _log.warn("Config twitch_api_secret not provided! Twitch component calls will not work!")

async def setup():
    global api
    try:
        api = await Twitch(config.twitch_api_id, app_secret=config.twitch_api_secret, target_app_auth_scope=[AuthScope.ANALYTICS_READ_EXTENSION])
    except Exception as e:
        _log.error(e, exc_info=True)

async def video_id_is_persistent(id: int):
    global api
    vid_data: dict = api.get_videos(ids=[id])
    vid: Video = await first(vid_data)
    if vid is None:
        return True # If video isn't accessible assume best for manual moderation
    if vid.type == VideoType.ARCHIVE:
        return False
    else:
        return True

def check_for_twitch_id(uri: str) -> Optional[int]:
    """Returns id if found, otherwise None"""
    if not "twitch.tv" in uri:
        return None
    try:
        id = int([e for e in uri.split("/") if TWITCH_ID_MATCH.match(e)][0])
    except IndexError:
        return None
    return id
