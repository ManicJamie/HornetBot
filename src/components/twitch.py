from typing import Optional
import config, logging, re
from twitchAPI.twitch import Twitch
from twitchAPI.object import Video
from twitchAPI.helper import first
from twitchAPI.types import AuthScope, VideoType

_log = logging.getLogger("twitch")

api: Twitch | None = None

TWITCH_URL_MATCH: re.Pattern = re.compile(r"https?:\/\/(?:www.)?twitch.tv\/videos\/(\d{9,11})")

if not config.twitch_api_id:
    _log.warn("Config twitch_api_id not provided! Twitch component calls will not work!")
if not config.twitch_api_secret:
    _log.warn("Config twitch_api_secret not provided! Twitch component calls will not work!")

class NotFoundException(Exception):
    pass

async def setup():
    global api
    if api is not None:
        _log.warning("Setup attempted when already set up, ignoring")
        return
    if not config.twitch_api_id or not config.twitch_api_secret:
        _log.warning("Setup attempted when twitch api info not present, ignoring")
        return
    try:
        api = await Twitch(config.twitch_api_id, app_secret=config.twitch_api_secret, target_app_auth_scope=[AuthScope.ANALYTICS_READ_EXTENSION])
    except Exception as e:
        _log.error(e, exc_info=True)

async def video_id_is_persistent(id: str | int):
    global api
    if api is None: raise Exception("Twitch API not initialised!")
    vid_data = api.get_videos(ids=[str(id)])
    vid: Video | None = await first(vid_data)
    if vid is None:
        return True  # If video isn't accessible assume best for manual moderation
    if vid.type == VideoType.ARCHIVE:
        return False
    else:
        return True

def check_for_twitch_id(uri: str) -> Optional[str]:
    """Returns id if found, otherwise None"""
    match = TWITCH_URL_MATCH.match(uri)
    if match is None:
        return None
    else:
        return match.group(0)

async def check_channel_live(channel_id: str) -> bool:
    """Check if a given channel id is currently live"""
    global api
    if api is None: raise Exception("Twitch API not initialised!")
    channel = await first(api.get_streams(user_id=[channel_id], stream_type="live"))
    if channel is not None:
        return True
    else: return False

async def get_channel_url(channel_id: str) -> str:
    global api
    if api is None: raise Exception("Twitch API not initialised!")
    channel = await first(api.get_streams(user_id=[channel_id]))
    if channel is None: raise NotFoundException(f"Channel id {channel_id} not found!")
    return f"https://twitch.tv/{channel.user_name.lower()}"

async def get_title(channel_id: str) -> str:
    global api
    if api is None: raise Exception("Twitch API not initialised!")
    channel = await first(api.get_streams(user_id=[channel_id]))
    if channel is None: raise NotFoundException(f"Channel id {channel_id} not found!")
    return channel.title

async def get_thumbnail(channel_id: str) -> str:
    global api
    if api is None: raise Exception("Twitch API not initialised!")
    channel = await first(api.get_streams(user_id=[channel_id]))
    if channel is None: raise NotFoundException(f"Channel id {channel_id} not found!")
    return channel.thumbnail_url

async def get_username(channel_id: str) -> str:
    global api
    if api is None: raise Exception("Twitch API not initialised!")
    channel = await first(api.get_streams(user_id=[channel_id]))
    if channel is None: raise NotFoundException(f"Channel id {channel_id} not found!")
    return channel.user_name
