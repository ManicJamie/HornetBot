import srcomapi
import srcomapi.datatypes as dt
import requests

api = srcomapi.SpeedrunCom()
api.debug = 0
api.user_agent = "HK_HornetBot" # src does not deserve api usage analytics but tbh they're almost certainly not reading them anyway

DISCORD_SEARCH = "src=\"/images/socialmedia/discord.png\" data-id=\"" # for scraping discord username :)

class NotFoundException(Exception): pass

def getGame(name: str) -> dt.Game:
    try:
        return api.search(dt.Game, {"name": name})[0]
    except IndexError:
        raise NotFoundException

def getUnverifiedRuns(game: dt.Game):
    """Caps at 200; pagination takes work & you shouldn't have this many unverified runs!"""
    return api.search(dt.Run, {"game": game.id, "status": "new", "max": 200, "orderby": "submitted", "direction": "asc"})

def getRunsFromUser(games : list[dt.Game], user: dt.User):
    """Get a list of verified runs from the user for a given list of games"""
    runs = []
    for game in games:
        runs += api.search(dt.Run, {"game": game.id, "status": "verified", "user": user.id})
    return runs

def getCategory(id):
    return dt.Run(api, data=api.get(f"categories/{id}"))

def getUser(id):
    return dt.User(api, data=api.get(f"users/{id}"))

def getVariable(id):
    return dt.Variable(api, data=api.get(f"variables/{id}"))

def getLevel(id):
    return dt.Level(api, data=api.get(f"levels/{id}"))

def findUser(name):
    try:
        return api.search(dt.User, {"name": name})[0]
    except IndexError:
        raise NotFoundException
    
def getDiscord(user: dt.User) -> str:
    """Gets the discord username of a speedrun.com User."""
    # The SRC api does not contain the discord username from the user profile, so we're scraping it instead. This is stupid.
    get = requests.get(f"http://www.speedrun.com/user/{user.name}") # not safe but idc anymore
    content = str(get.content)
    index = content.find(DISCORD_SEARCH) + len(DISCORD_SEARCH)
    if index == -1: raise NotFoundException
    end = content.index("\"", index)
    return content[index:end]