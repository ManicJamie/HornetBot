import speedruncompy
from speedruncompy.datatypes.enums import Verified
from discord.ext.commands import Cog, command
from discord.ext.tasks import loop
from collections import deque
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from Hornet import HornetBot, HornetContext

import config, save
from components import src, auth, twitch

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
    async def Twitch_Run(run: dict, run_settings: dict, comments: list, reject_reasons: list):
        url: str = run.get("video", "")
        twitch_id = twitch.check_for_twitch_id(url)
        if twitch_id is not None:
            reject_reasons.append("We are no longer accepting Twitch Highlights; please resubmit after exporting to YouTube")
    
    @staticmethod
    async def Twitch_VOD_Persistent(run: dict, run_settings: dict, comments: list, reject_reasons: list):
        url: str = run.get("video", "")
        twitch_id = twitch.check_for_twitch_id(url)
        if twitch_id is None:
            return  # Assume its fine if we don't know anything about it :)
        if not await twitch.video_id_is_persistent(twitch_id):
            reject_reasons.append("The submitted video is a Twitch VOD, which will be deleted after a while. Please create a Twitch Highlight before submitting")
    
    @staticmethod
    async def RTA_noMS(run: dict, run_settings: dict, comments: list, reject_reasons: list):
        rta = run.get("timeWithLoads", 0)
        if rta != 0:
            if run_settings["timeWithLoads"] is None: return  # RTA has already been removed
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
    save.add_global_module_template(MODULE_NAME, {"games": {}})
    await twitch.setup()
    await bot.add_cog(SRCManagementCog(bot))

async def teardown(bot: 'HornetBot'):
    await bot.remove_cog("SRCManagement")

class SRCManagementCog(Cog, name="SRCManagement", description="Allows Hornet to lint run submissions"):
    def __init__(self, bot: 'HornetBot'):
        self.bot = bot
        self._log = self.bot._log.getChild("SRCManagement")
    
    async def cog_load(self):
        if not config.src_phpsessid:
            self._log.error("SRC PHPSESSID not provided; exiting")
            raise Exception("SRC PHPSESSID not provided")
        
        session = (await speedruncompy.GetSession(_api=src.CLIENT).perform_async()).session
        if not session.signedIn:
            self._log.error("Could not log in - cancelling load")
            raise Exception("Could not log in!")
        
        self.csrf: str = session.csrfToken
        self.checkRuns.start()

    async def cog_unload(self):
        self.checkRuns.stop()
    
    async def checkGameModerated(self, game_id):
        """Check if Hornet can moderate a game"""
        modGames = await speedruncompy.GetModerationGames(_api=src.CLIENT).perform_async()
        if game_id not in [g.get("id") for g in modGames.games]:  # type:ignore  # GetModerationGames returns None when not logged in. We are logged in.
            return False
        return True

    async def checkModerators(self, username, game):
        """Checks a game's moderators for a specific discord username (NOT verifiers)"""
        game_data = await speedruncompy.GetGameData(gameId=game).perform_async()
        mods = [moderator.userId for moderator in game_data.moderators if moderator.level >= 0]
        modNames = [str(u.name) for u in game_data.users if u.id in mods]
        for name in modNames:
            if username == await src.get_src_user_discord(name):
                return True
        return False

    @command(help="Add a game to be managed by Hornet")
    @auth.check_admin
    async def addModeratedGame(self, ctx: 'HornetContext', *, game: str):
        if ctx.guild is None: return
        game_o = await src.find_game(game)
        game_id = game_o.id
        mod_data = save.get_global_module(MODULE_NAME)

        if not self.checkGameModerated(game_id):
            await ctx.embed_reply(f"Game `{game_o.name}` with id `{game_o.id}` doesn't appear to be moderated by Hornet")
            return
        if game_id in mod_data.get("games"):  # type: ignore #TODO: actual typeguard
            await ctx.embed_reply("Game is already moderated!")
            return
        if not self.checkModerators(ctx.author.name, game_id):
            await ctx.embed_reply("You must moderate this game! (Check your SRC discord connection)")
            return
        
        mod_data["games"][game_id] = {"guild": ctx.guild.id, "checks": [], "checked": []}
        save.save()
        await ctx.embed_reply(f"Game `{game_o.name}` with id `{game_o.id}` added")
    
    @command(help="Stop Hornet managing a game")
    @auth.check_admin
    async def removeModeratedGame(self, ctx: 'HornetContext', *, game):
        game = await src.find_game(game)
        game_id = game.id

        mod_data: dict = save.get_global_module(MODULE_NAME)
        games = mod_data.get("games", {})

        if game_id not in games:
            await ctx.embed_reply(f"Game `{game.name}` with id `{game.id}` doesn't appear to be moderated by Hornet")
            return
        if not self.checkModerators(ctx.author.name, game_id):
            await ctx.embed_reply("You must moderate this game! (Check your SRC discord connection)")
            return
        
        games.pop(game_id)
        save.save()
        await ctx.embed_reply(f"Game `{game.name}` with id `{game.id}` removed")
    
    @command(help="Add a moderation check to a game")
    @auth.check_admin
    async def addCheck(self, ctx: 'HornetContext', check: str, *, game):
        game = await src.find_game(game)
        if not self.checkModerators(ctx.author.name, game.id):
            await ctx.embed_reply("You must moderate this game! (Check your SRC discord connection)")
            return
        checks = [method[0] for method in Checks.__dict__.items() if isinstance(method[1], staticmethod)]
        if check not in checks:
            await ctx.embed_reply(f"Could not recognise check `{check}`")
            return
        
        mod_data = save.get_global_module(MODULE_NAME)
        if game.id not in mod_data["games"]:
            await ctx.embed_reply(f"Game `{game.name}` with id `{game.id}` doesn't appear to be moderated by Hornet")
            return
        
        checks: list = mod_data["games"][game.id]["checks"]
        if check in checks:
            await ctx.embed_reply(f"Game `{game.name}` already has check `{check}`")
            return
        
        checks.append(check)
        save.save()
        await ctx.embed_reply(f"Added `{check}` to `{game.name}`\r\n```{', '.join(checks)}```")

    @command(help="Remove a moderation check from a game")
    @auth.check_admin
    async def removeCheck(self, ctx: 'HornetContext', check: str, *, game):
        game = await src.find_game(game)
        if not self.checkModerators(ctx.author.name, game.id):
            await ctx.embed_reply("You must moderate this game! (Check your SRC discord connection)")
            return
        checks = [method[0] for method in Checks.__dict__.items() if isinstance(method[1], staticmethod)]
        if check not in checks:
            await ctx.embed_reply(f"Could not recognise check `{check}`")
            return
        
        mod_data = save.get_global_module(MODULE_NAME)
        if game.id not in mod_data["games"]:
            await ctx.embed_reply(f"Game `{game.name}` with id `{game.id}` doesn't appear to be moderated by Hornet")
            return
        
        checks: list = mod_data["games"][game.id]["checks"]
        if check not in checks:
            await ctx.embed_reply(f"Game `{game.name}` doesn't have check `{check}`")
            return
        
        checks.remove(check)
        save.save()
        await ctx.embed_reply(f"Removed `{check}` from `{game.name}`\r\n```{', '.join(checks)}```")

    @command(help="Lists all checks available")
    @auth.check_admin
    async def listChecks(self, ctx: 'HornetContext', *, game: str = ""):
        checks = [method[0] for method in Checks.__dict__.items() if isinstance(method[1], staticmethod)]
        if game == "":
            await ctx.embed_reply(", ".join(checks))
            return
        game_o = await src.find_game(game)
        if not self.checkModerators(ctx.author.name, game_o.id):
            await ctx.embed_reply("You must moderate this game! (Check your SRC discord connection)")
            return

        mod_data = save.get_global_module(MODULE_NAME)
        if game_o.id not in mod_data["games"]:
            await ctx.embed_reply(f"Game `{game_o.name}` with id `{game_o.id}` doesn't appear to be moderated by Hornet")
            return

        checks = [method for method in checks if method in mod_data["games"][game_o.id]["checks"]]
        await ctx.embed_reply(", ".join(checks), title=game_o.name)

    @command(help="Clear cache of checked runs")
    @auth.check_admin
    async def clearChecked(self, ctx: 'HornetContext', *, game: str):
        game_o = await src.find_game(game)
        if not self.checkModerators(ctx.author.name, game_o.id):
            await ctx.embed_reply("You must moderate this game! (Check your SRC discord connection)")
            return
        save.get_global_module(MODULE_NAME)["games"][game_o.id]["checked"] = []
        save.save()
        await ctx.embed_reply(f"Cleared cache for game `{game_o.name}` with id `{game_o.id}`")

    async def doChecks(self, game_data: dict, run: dict, unverified: dict):
        run_settings = (await speedruncompy.GetRunSettings(run["id"]).perform_async()).settings
        comments = []
        reject_reasons = []
        all_checks = [method for method in Checks.__dict__.items() if isinstance(method[1], staticmethod)]
        checks: list[staticmethod] = [method[1] for method in all_checks if (method[0] in game_data["checks"])]
        
        if (guild := self.bot.get_guild(game_data["guild"])) is None:
            guild = await self.bot.fetch_guild(game_data["guild"])
        
        for check in checks:
            await check.__func__(run, run_settings, comments, reject_reasons)
        
        if len(comments) != 0:
            run_settings.comment = run_settings.get("comment", "") + "\r\n\r\n// Hornet Comments: " + " & ".join(comments)
            self._log.info(f"Run {run['id']} given comments {comments}")
            await self.bot.guild_log(guild, f"Run {run['id']} edited w/ comments:\r\n```{comments}```", source="SRCManagement")
            await speedruncompy.PutRunSettings(autoverify=False, csrfToken=self.csrf, settings=run_settings, _api=src.CLIENT).perform_async()

        if len(reject_reasons) != 0:
            self._log.debug(run)
            self._log.info(f"Run {run['id']} rejected with reasons {reject_reasons}")
            await self.bot.guild_log(guild, f"Run {run['id']} rejected w/ reasons:\r\n```{reject_reasons}```", source="SRCManagement")
            reason = "Hornet Auto-Reject: Your run was rejected automatically for the following reason(s): " + " & ".join(reject_reasons) + ". | If you believe this is in error, please contact a moderator."
            await speedruncompy.PutRunVerification(run["id"], Verified.REJECTED, reason=reason, _api=src.CLIENT).perform_async()

    @loop(minutes=15)
    async def checkRuns(self):
        self._log.debug("checkRuns running...")
        mod_data = save.get_global_module(MODULE_NAME)
        for game_id in mod_data["games"]:
            game_data = mod_data["games"][game_id]
            if (guild := self.bot.get_guild(game_data["guild"])) is None:
                guild = await self.bot.fetch_guild(game_data["guild"])
            
            try:
                game_queue = deque(game_data["checked"], maxlen=200)
                if not self.checkGameModerated(game_id):
                    await self.bot.guild_log(guild, f"Hornet cannot moderate game w/ ID `{game_id}`, skipping", source="SRCManagement")
                    continue
                unverified = await speedruncompy.GetModerationRuns(game_id, 100, 1, verified=0).perform_async()
                for run in unverified.get("runs", []):
                    if run["id"] in game_queue: continue
                    await self.doChecks(game_data, run, unverified)
                    game_queue.append(run["id"])
                
                game_data["checked"] = list(game_queue)
                save.save()
            except Exception as e:
                self._log.error(f"Task checkRuns failed on game {game_id}")
                await self.bot.guild_log(guild, f"Task failed: checkRuns\r\n```{str(e.args)}```", source="SRCManagement")
                self._log.error(e, exc_info=True)
        self._log.debug("checkRuns done")
