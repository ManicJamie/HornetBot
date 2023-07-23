import srcomapi
from srcomapi.datatypes import Game, Level, Run, User, Variable
import requests

api = srcomapi.SpeedrunCom()
api.debug = 0
api.user_agent = "HK_HornetBot" # src does not deserve api usage analytics but tbh they're almost certainly not reading them anyway
"""Api key is set by config if provided; required to fetch most recent data!"""

DISCORD_SEARCH = '<button type="button" tabindex="0" class="x-input-button rounded text-xs px-2 py-1 bg-white/10 text-on-input font-normal border border-transparent hover:bg-white/20 disabled:opacity-50 shadow"><svg xmlns="http://www.w3.org/2000/svg" fill="currentColor" class="h-4 w-4" viewBox="0 0 16 16"><path d="M13.545 2.907a13.227 13.227 0 0 0-3.257-1.011.05.05 0 0 0-.052.025c-.141.25-.297.577-.406.833a12.19 12.19 0 0 0-3.658 0 8.258 8.258 0 0 0-.412-.833.051.051 0 0 0-.052-.025c-1.125.194-2.22.534-3.257 1.011a.041.041 0 0 0-.021.018C.356 6.024-.213 9.047.066 12.032c.001.014.01.028.021.037a13.276 13.276 0 0 0 3.995 2.02.05.05 0 0 0 .056-.019c.308-.42.582-.863.818-1.329a.05.05 0 0 0-.01-.059.051.051 0 0 0-.018-.011 8.875 8.875 0 0 1-1.248-.595.05.05 0 0 1-.02-.066.051.051 0 0 1 .015-.019c.084-.063.168-.129.248-.195a.05.05 0 0 1 .051-.007c2.619 1.196 5.454 1.196 8.041 0a.052.052 0 0 1 .053.007c.08.066.164.132.248.195a.051.051 0 0 1-.004.085 8.254 8.254 0 0 1-1.249.594.05.05 0 0 0-.03.03.052.052 0 0 0 .003.041c.24.465.515.909.817 1.329a.05.05 0 0 0 .056.019 13.235 13.235 0 0 0 4.001-2.02.049.049 0 0 0 .021-.037c.334-3.451-.559-6.449-2.366-9.106a.034.034 0 0 0-.02-.019Zm-8.198 7.307c-.789 0-1.438-.724-1.438-1.612 0-.889.637-1.613 1.438-1.613.807 0 1.45.73 1.438 1.613 0 .888-.637 1.612-1.438 1.612Zm5.316 0c-.788 0-1.438-.724-1.438-1.612 0-.889.637-1.613 1.438-1.613.807 0 1.451.73 1.438 1.613 0 .888-.631 1.612-1.438 1.612Z"></path></svg>'
DISCORD_END = '</button>'
DISCORD_VERIFIED_SUFFIX = ' <div data-state="closed"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" class="-mr-1 h-4 w-4 text-primary-400"><path fill-rule="evenodd" d="M8.603 3.799A4.49 4.49 0 0112 2.25c1.357 0 2.573.6 3.397 1.549a4.49 4.49 0 013.498 1.307 4.491 4.491 0 011.307 3.497A4.49 4.49 0 0121.75 12a4.49 4.49 0 01-1.549 3.397 4.491 4.491 0 01-1.307 3.497 4.491 4.491 0 01-3.497 1.307A4.49 4.49 0 0112 21.75a4.49 4.49 0 01-3.397-1.549 4.49 4.49 0 01-3.498-1.306 4.491 4.491 0 01-1.307-3.498A4.49 4.49 0 012.25 12c0-1.357.6-2.573 1.549-3.397a4.49 4.49 0 011.307-3.497 4.49 4.49 0 013.497-1.307zm7.007 6.387a.75.75 0 10-1.22-.872l-3.236 4.53L9.53 12.22a.75.75 0 00-1.06 1.06l2.25 2.25a.75.75 0 001.14-.094l3.75-5.25z" clip-rule="evenodd"></path></svg></div>'
# for scraping discord username :)

class NotFoundException(Exception): pass

def get_game(name: str) -> Game:
    try:
        return api.search(Game, {"name": name})[0]
    except IndexError:
        raise NotFoundException

def get_unverified_runs(game: Game):
    """Caps at 200; pagination takes work & you shouldn't have this many unverified runs!"""
    return api.search(Run, {"game": game.id, "status": "new", "max": 200, "orderby": "submitted", "direction": "asc"})

def get_runs_from_user(games: list[Game], user: User):
    """Get a list of verified runs from the user for a given list of games"""
    runs = []
    for game in games:
        runs += api.search(Run, {"game": game.id, "status": "verified", "user": user.id})
    return runs

def get_category(id):
    return Run(api, data=api.get(f"categories/{id}"))

def get_user(id):
    return User(api, data=api.get(f"users/{id}"))

def get_variable(id):
    return Variable(api, data=api.get(f"variables/{id}"))

def get_level(id):
    return Level(api, data=api.get(f"levels/{id}"))

def find_user(name):
    try:
        return api.search(User, {"name": name})[0]
    except IndexError:
        raise NotFoundException

def get_discord(user: User) -> str:
    """Gets the discord username of a speedrun.com User."""
    # The SRC api does not contain the discord username from the user profile, so we're scraping it instead. This is stupid.
    get = requests.get(f"http://www.speedrun.com/user/{user.name}") # not safe but idc anymore
    content = str(get.content)
    index = content.find(DISCORD_SEARCH) + len(DISCORD_SEARCH)
    if index == -1: raise NotFoundException
    content = content[index:].removeprefix(' <!-- -->').removeprefix("@") # ephemeral prefix that sometimes exists + @ if present
    end = content.index(DISCORD_END)
    content = content[:end].strip().removesuffix(DISCORD_VERIFIED_SUFFIX).removesuffix("<!-- -->") # ephemeral suffixes that sometimes exists
    return content.strip()
