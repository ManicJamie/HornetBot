from speedruncompy import GetUserPopoverData, GetSearch
from speedruncompy import NetworkId, Game, User
from speedruncompy.exceptions import APIException

from speedruncompy import SpeedrunClient

CLIENT = SpeedrunClient("Hornet_Bot")

class NotFoundException(Exception): pass

class UserNotFound(Exception): pass
class NoDiscordUsername(Exception): pass

async def find_game(name: str) -> Game:
    try:
        search_results = await GetSearch(name, includeGames=True, limit=1, _client=CLIENT).perform()
        return search_results.gameList[0]
    except IndexError:
        raise NotFoundException

async def find_src_user(username: str) -> User:
    try:
        results = await GetSearch(username, favorExactMatches=True, includeUsers=True, _client=CLIENT).perform()
        return results.userList[0]
    except IndexError:
        raise NotFoundException
    
async def get_src_user_discord(username: str) -> tuple[User, str]:
    """Gets the discord username of a speedrun.com User."""
    try:
        userSearch = await GetSearch(username, favorExactMatches=True, includeUsers=True, limit=1, _client=CLIENT).perform()
    except APIException as e:
        raise e
    
    if len(userSearch.userList) < 1:
        raise UserNotFound
    user = userSearch.userList[0]
    
    try:
        userPopover = await GetUserPopoverData(user.id).perform(autovary=True)
    except APIException as e:
        raise e
    
    try:
        discord_username = next(x.value for x in userPopover.userSocialConnectionList if x.networkId == NetworkId.DISCORD)
    except StopIteration:
        raise NoDiscordUsername(user.name)
    
    return (userPopover.user, discord_username.strip())
