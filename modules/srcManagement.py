import speedruncompy
from speedruncompy.enums import verified
from discord.ext.commands import Bot, Cog, Context, command
from discord.ext.tasks import loop
import logging
from collections import deque
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from Hornet import HornetBot

import config, save
from components import src, embeds, auth, twitch

MODULE_NAME = __name__.split(".")[-1]

"""
module schema:
games {
    game_id : {
        guild: 123456789,
        checks: [checkname, checkname...],
        checked: [checkedrun1, checkedrun2 ... ] (maxlen = 200)
    }
    
}
"""

DEFAULT_MOD_CFG = {
    "guild": 0,
    "checks": [],
    "checked": []
}

class Checks():
    """Static class holding check methods."""
    @staticmethod
    async def IL_noRTA(run: dict, run_settings: dict, comments: list, reject_reasons: list):
        level_id = run.get("levelId")
        if level_id:
            rta = run.get("timeWithLoads", 0)
            lrt = run.get("time", 0)
            if rta != 0 and lrt != 0:
                hr = run_settings["timeWithLoads"]["hour"]
                min = run_settings["timeWithLoads"]["minute"]
                s = run_settings["timeWithLoads"]["second"]
                ms = run_settings["timeWithLoads"]["millisecond"]
                comments.append(f"RTA removed from IL (submitted {hr}:{min:02}:{s:02}.{ms:03})")
                run_settings["timeWithLoads"]["hour"] = 0
                run_settings["timeWithLoads"]["minute"] = 0
                run_settings["timeWithLoads"]["second"] = 0
                run_settings["timeWithLoads"]["millisecond"] = 0

    @staticmethod
    async def IL_RTA_to_LRT(run: dict, run_settings: dict, comments: list, reject_reasons: list):
        level_id = run.get("levelId")
        if level_id:
            rta = run.get("timeWithLoads", 0)
            lrt = run.get("time", 0)
            if rta != 0 and lrt == 0:
                hr = run_settings["timeWithLoads"]["hour"]
                min = run_settings["timeWithLoads"]["minute"]
                s = run_settings["timeWithLoads"]["second"]
                ms = run_settings["timeWithLoads"]["millisecond"]
                comments.append(f"RTA taken as LRT for leaderboard formatting (submitted {hr}:{min:02}:{s:02}.{ms:03})")
                construct = {"hour": hr, "minute": min, "second": s, "millisecond": ms}
                run_settings["time"] = construct
                run_settings["timeWithLoads"] = None
    
    @staticmethod
    async def Twitch_VOD_Persistent(run: dict, run_settings: dict, comments: list, reject_reasons: list):
        url = run.get("video")
        twitch_id = twitch.check_for_twitch_id(url)
        if twitch_id is None:
            return # Assume its fine if we don't know anything about it :)
        if not await twitch.video_id_is_persistent(twitch_id):
            reject_reasons.append("The submitted video is a Twitch VOD, which will be deleted after a while. Please create a Twitch Highlight before submitting")
    
    @staticmethod
    async def RTA_noMS(run: dict, run_settings: dict, comments: list, reject_reasons: list):
        rta = run.get("timeWithLoads", 0)
        if rta != 0:
            ms = run_settings["timeWithLoads"]["millisecond"]
            if ms != 0:
                comments.append(f"Removed milliseconds from RTA (submitted {ms})")
                run_settings["timeWithLoads"]["millisecond"] = 0

    @staticmethod
    async def noMS_10min(run: dict, run_settings: dict, comments: list, reject_reasons: list):
        lrt = run.get("time", 0)
        if lrt >= 600:
            ms = run_settings["time"]["millisecond"]
            if ms != 0:
                comments.append(f"Removed milliseconds from run over 10 minutes (submitted {ms})")
                run_settings["time"]["millisecond"] = 0
    
    @staticmethod
    async def fixMS(run: dict, run_settings: dict, comments: list, reject_reasons: list):
        lrt = run.get("time", 0)
        if lrt != 0:
            ms = run_settings["time"]["millisecond"]
            if (ms % 10) != 0 and (ms < 100):
                comments.append(f"Milliseconds -> Centiseconds (.{ms} -> .{ms * 10})")
                run_settings["time"]["millisecond"] *= 10

async def setup(bot: 'HornetBot'):
    global _log
    _log = bot._log.getChild("SRCManagement")
    save.add_global_module_template(MODULE_NAME, {"games": {}})
    await twitch.setup()
    await bot.add_cog(SRCManagementCog(bot))

async def teardown(bot: Bot):
    await bot.remove_cog("SRCManagement")

class SRCManagementCog(Cog, name="SRCManagement", description="Allows Hornet to lint run submissions"):
    def __init__(self, bot: 'HornetBot'):
        self.bot = bot
        self._log : logging.Logger = self.bot._log
        speedruncompy.auth.login_PHPSESSID(config.src_phpsessid)
        self.csrf = speedruncompy.auth.get_CSRF()
        self.checkRuns.start()

    def cog_unload(self):
        self.checkRuns.stop()
    
    def checkGameModerated(self, game_id):
        """Check if Hornet can moderate a game"""
        modGames = speedruncompy.GetModerationGames().perform()
        if game_id not in [g.get("id") for g in modGames["games"]]:
            return False
        return True

    def checkModerators(self, username, game):
        """Checks a game's moderators for a specific discord username (NOT verifiers)"""
        game_data = speedruncompy.GetGameData(gameId=game).perform()
        mods = [x["userId"] for x in game_data["moderators"] if x["level"] >= 0]
        modNames = [str(x["name"]) for x in game_data["users"] if x["id"] in mods]
        for name in modNames:
            if username == src.get_discord_username(name):
                return True
        return False

    @command(help="Add a game to be managed by Hornet")
    @auth.check_admin
    async def addModeratedGame(self, ctx: Context, *, game: str):
        game = src.find_game(game)
        game_id = game.id
        mod_data = save.get_global_module(MODULE_NAME)

        if not self.checkGameModerated(game_id):
            await embeds.embed_reply(ctx, f"Game `{game.name}` with id `{game.id}` doesn't appear to be moderated by Hornet")
            return
        if game_id in mod_data.get("games"):
            await embeds.embed_reply(ctx, "Game is already moderated!")
            return
        if not self.checkModerators(ctx.author.name, game_id):
            await embeds.embed_reply("You must moderate this game! (Check your SRC discord connection)")
            return
        
        mod_data["games"][game_id] = {"guild": ctx.guild.id, "checks": [], "checked": []}
        save.save()
        await embeds.embed_reply(ctx, f"Game `{game.name}` with id `{game.id}` added")
    
    @command(help="Stop Hornet managing a game")
    @auth.check_admin
    async def removeModeratedGame(self, ctx: Context, *, game):
        game = src.find_game(game)
        game_id = game.id

        mod_data : dict = save.get_global_module(MODULE_NAME)
        games = mod_data.get("games", {})

        if game_id not in games:
            await embeds.embed_reply(ctx, f"Game `{game.name}` with id `{game.id}` doesn't appear to be moderated by Hornet")
            return
        if not self.checkModerators(ctx.author.name, game_id):
            await embeds.embed_reply("You must moderate this game! (Check your SRC discord connection)")
            return
        
        games.pop(game_id)
        save.save()
        await embeds.embed_reply(ctx, f"Game `{game.name}` with id `{game.id}` removed")
    
    @command(help="Add a moderation check to a game")
    @auth.check_admin
    async def addCheck(self, ctx: Context, check: str, *, game):
        game = src.find_game(game)
        if not self.checkModerators(ctx.author.name, game.id):
            await embeds.embed_reply("You must moderate this game! (Check your SRC discord connection)")
            return
        checks = [method[0] for method in Checks.__dict__.items() if isinstance(method[1], staticmethod)]
        if check not in checks:
            await embeds.embed_reply(ctx, f"Could not recognise check `{check}`")
            return
        
        mod_data = save.get_global_module(MODULE_NAME)
        if game.id not in mod_data["games"]:
            await embeds.embed_reply(ctx, f"Game `{game.name}` with id `{game.id}` doesn't appear to be moderated by Hornet")
            return
        
        checks: list = mod_data["games"][game.id]["checks"]
        if check in checks:
            await embeds.embed_reply(ctx, f"Game `{game.name}` already has check `{check}`")
            return
        
        checks.append(check)
        save.save()
        await embeds.embed_reply(ctx, f"Added `{check}` to `{game.name}`\r\n```{', '.join(checks)}```")

    @command(help="Remove a moderation check from a game")
    @auth.check_admin
    async def removeCheck(self, ctx: Context, check: str, *, game):
        game = src.find_game(game)
        if not self.checkModerators(ctx.author.name, game.id):
            await embeds.embed_reply("You must moderate this game! (Check your SRC discord connection)")
            return
        checks = [method[0] for method in Checks.__dict__.items() if isinstance(method[1], staticmethod)]
        if check not in checks:
            await embeds.embed_reply(ctx, f"Could not recognise check `{check}`")
            return
        
        mod_data = save.get_global_module(MODULE_NAME)
        if game.id not in mod_data["games"]:
            await embeds.embed_reply(ctx, f"Game `{game.name}` with id `{game.id}` doesn't appear to be moderated by Hornet")
            return
        
        checks: list = mod_data["games"][game.id]["checks"]
        if check not in checks:
            await embeds.embed_reply(ctx, f"Game `{game.name}` doesn't have check `{check}`")
            return
        
        checks.remove(check)
        save.save()
        await embeds.embed_reply(ctx, f"Removed `{check}` from `{game.name}`\r\n```{', '.join(checks)}```")

    @command(help="Lists all checks available")
    @auth.check_admin
    async def listChecks(self, ctx: Context, *, game: str = ""):
        checks = [method[0] for method in Checks.__dict__.items() if isinstance(method[1], staticmethod)]
        if game == "":
            await embeds.embed_reply(ctx, ", ".join(checks))
            return
        game = src.find_game(game)
        if not self.checkModerators(ctx.author.name, game.id):
            await embeds.embed_reply("You must moderate this game! (Check your SRC discord connection)")
            return

        mod_data = save.get_global_module(MODULE_NAME)
        if game.id not in mod_data["games"]:
            await embeds.embed_reply(ctx, f"Game `{game.name}` with id `{game.id}` doesn't appear to be moderated by Hornet")
            return

        checks = [method for method in checks if method in mod_data["games"][game.id]["checks"]]
        await embeds.embed_reply(ctx, ", ".join(checks), title=game.name)

    @command(help="Clear cache of checked runs")
    @auth.check_admin
    async def clearChecked(self, ctx: Context, *, game: str):
        game = src.find_game(game)
        if not self.checkModerators(ctx.author.name, game.id):
            await embeds.embed_reply("You must moderate this game! (Check your SRC discord connection)")
            return
        save.get_global_module(MODULE_NAME)["games"][game.id]["checked"] = []
        save.save()
        await embeds.embed_reply(f"Cleared cache for game `{game.name}` with id `{game.id}`")

    async def doChecks(self, game_data: dict, run: dict, unverified: dict):
        run_settings = speedruncompy.GetRunSettings(run["id"]).perform()["settings"]
        comments = []
        reject_reasons = []
        all_checks = [method for method in Checks.__dict__.items() if isinstance(method[1], staticmethod)]
        checks: list[staticmethod] = [method[1] for method in all_checks if (method[0] in game_data["checks"])]
        
        for check in checks:
            await check.__func__(run, run_settings, comments, reject_reasons)
        
        if len(comments) != 0:
            run_settings["comment"] = run_settings.get("comment", "") + "\r\n\r\n// Hornet Comments: " + " & ".join(comments)
            _log.info(f"Run {run['id']} given comments {comments}")
            await self.bot.guild_log(game_data["guild"], f"Run {run['id']} edited w/ comments:\r\n```{comments}```", source="SRCManagement")
            speedruncompy.PutRunSettings(autoverify=False, csrfToken=self.csrf, settings=run_settings).perform()

        if len(reject_reasons) != 0:
            _log.debug(run)
            _log.info(f"Run {run['id']} rejected with reasons {reject_reasons}")
            await self.bot.guild_log(game_data["guild"], f"Run {run['id']} rejected w/ reasons:\r\n```{reject_reasons}```", source="SRCManagement")
            reason = "Hornet Auto-Reject: Your run was rejected automatically for the following reason(s): " + " & ".join(reject_reasons) + ". | If you believe this is in error, please contact a moderator."
            speedruncompy.PutRunVerification(run["id"], verified.REJECTED, reason=reason).perform()

    @loop(minutes=5)
    async def checkRuns(self):
        _log.debug("checkRuns running...")
        mod_data = save.get_global_module(MODULE_NAME)
        for game_id in mod_data["games"]:
            game_data = mod_data["games"][game_id]
            try:
                game_queue = deque(game_data["checked"], maxlen=200)
                if not self.checkGameModerated(game_id):
                    await self.bot.guild_log(game_data["guild"], f"Hornet cannot moderate game w/ ID `{game_id}`, skipping", source="SRCManagement")
                    continue
                unverified = speedruncompy.GetModerationRuns(game_id, 100, 1, verified=0).perform()
                for run in unverified.get("runs", []):
                    if run["id"] in game_queue: continue
                    await self.doChecks(game_data, run, unverified)
                    game_queue.append(run["id"])
                
                game_data["checked"] = list(game_queue)
                save.save()
            except Exception as e:
                _log.error(f"Task checkRuns failed on game {game_id}")
                await self.bot.guild_log(game_data["guild"], f"Task failed: checkRuns\r\n```{str(e.args)}```", source="SRCManagement")
                _log.error(e, exc_info=True)
        _log.debug("checkRuns done")