import srcomapi
import srcomapi.datatypes as dt

api = srcomapi.SpeedrunCom()
api.debug = 1
api.user_agent = "HK_HornetBot"

class UserNotFoundException(Exception): pass

def getGame(name: str) -> dt.Game:
    return api.search(dt.Game, {"name": name})[0]

def getUnverifiedRuns(game: dt.Game):
    return api.search(dt.Run, {"game": game.id, "status": "new", "max": 200})

def getRunsFromUser(games, un: str):
    try:
        user = api.search(dt.User, {"name": un, "embed": "id"})[0]
    except IndexError: 
        raise UserNotFoundException 
    
    runs = []
    for game in games:
        runs += api.search(dt.Run, {"game": game.id, "status": "verified", "user": user.id})
    return runs