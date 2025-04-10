from discord import Emoji, Message, TextChannel, RawReactionActionEvent
from discord.ext.commands import Cog, command
from discord.abc import Messageable
from discord.ext.tasks import loop
from discord.utils import escape_markdown
from srcomapi.datatypes import Game, Run
from datetime import timedelta
import time
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from Hornet import HornetBot, HornetContext

from components import auth, emojiUtil, src
import save

MODULE_NAME = __name__.split(".")[-1]

MODULE_TEMPLATE = {
    "trackedChannels": {},
    "claimEmoji": "\u2705",
    "unclaimEmoji": "\u274C"
}

async def setup(bot: 'HornetBot'):
    save.add_module_template(MODULE_NAME, MODULE_TEMPLATE)
    await bot.add_cog(GameTrackerCog(bot))

async def teardown(bot: 'HornetBot'):
    await bot.remove_cog("GameTracking")

class GameTrackerCog(Cog, name="GameTracking", description="Module tracking verification queues on speedrun.com"):
    def __init__(self, bot: 'HornetBot'):
        self.bot = bot
        self._log = bot._log.getChild("GameTracker")
        self.updateGames.start()

    async def cog_unload(self):
        self.updateGames.cancel()

    @command(help="Register a channel to track unverified runs for a game.")
    @auth.check_admin
    async def addgame(self, context: 'HornetContext', channel: TextChannel, *, gamename):
        if context.guild is None: return
        try:
            game = src.find_game(gamename)
        except src.NotFoundException:
            return
        
        mod_data = save.get_module_data(context.guild.id, MODULE_NAME)
        if str(channel.id) in mod_data["trackedChannels"]:
            mod_data["trackedChannels"][str(channel.id)].append(game.id)
        else:
            mod_data["trackedChannels"][str(channel.id)] = [game.id]
        save.save()
        await context.message.reply(f"Added game `{game.id}: {game.name}` to <#{channel.id}>", mention_author=False)

    @command(help="Unregister a channel from tracking unverified runs for this game.")
    @auth.check_admin
    async def removegame(self, context: 'HornetContext', channel: TextChannel, *, gamename):
        if context.guild is None: return
        try:
            game = src.find_game(gamename)
        except src.NotFoundException:
            return
        
        mod_data = save.get_module_data(context.guild.id, MODULE_NAME)
        if str(channel.id) in mod_data["trackedChannels"]:
            mod_data["trackedChannels"][str(channel.id)].remove(game.id)
        else:
            await context.message.reply(f"Could not find game `{game.id}: {game.name}` in  <#{channel.id}>", mention_author=False)
        save.save()
        await context.message.reply(f"Removed game `{game.id}: {game.name}` from <#{channel.id}>", mention_author=False)

    @command(help="Sets emoji used for claims (will not clear old reacts!)")
    @auth.check_admin
    async def setClaimEmoji(self, context: 'HornetContext', emoji: str):
        if context.guild is None: return
        emoji_clean: str | Emoji = await emojiUtil.to_emoji(context, emoji)
        emoji_ref = emojiUtil.to_string(emoji_clean)
        save.get_module_data(context.guild.id, MODULE_NAME)["claimEmoji"] = emoji_ref
        save.save()
        await context.message.delete()

    @command(help="Sets emoji used for unclaims (will not clear old reacts!)")
    @auth.check_admin
    async def setUnclaimEmoji(self, context: 'HornetContext', emoji: str):
        if context.guild is None: return
        emoji_clean: str | Emoji = await emojiUtil.to_emoji(context, emoji)
        emoji_ref = emojiUtil.to_string(emoji_clean)
        save.get_module_data(context.guild.id, MODULE_NAME)["unclaimEmoji"] = emoji_ref
        save.save()
        await context.message.delete()

    @Cog.listener()
    async def on_raw_reaction_add(self, payload: RawReactionActionEvent):
        """Handler on adding reacts in tracked verifier channels"""
        if payload.guild_id is None: return
        mod_data = save.get_module_data(payload.guild_id, MODULE_NAME)
        if str(payload.channel_id) not in mod_data["trackedChannels"]: return
        if payload.user_id == self.bot.user_id: return

        channel = self.bot.get_channel(payload.channel_id)
        if not isinstance(channel, (Messageable)): return
        message = await channel.fetch_message(payload.message_id)
        refstring = emojiUtil.to_string(payload.emoji)
        reactions = list(filter(lambda x: emojiUtil.to_string(x.emoji) == refstring, message.reactions))
        reaction = reactions[0]
        reacters = []
        async for user in reaction.users():
            if user.id != self.bot.user_id: reacters.append(user)

        if len(reacters) == 0: return
        user = self.bot.get_user(payload.user_id)
        if user is None: return

        if refstring == mod_data["claimEmoji"]:
            if message.content.endswith("**"): return  # don't claim if run already claimed
            
            await message.edit(content=f"{reaction.message.content}\r\n**Claimed by {escape_markdown(user.name)} <t:{int(time.time())}:R>**")
            await message.add_reaction(mod_data["unclaimEmoji"])
            await reaction.clear()
        elif refstring == mod_data["unclaimEmoji"]:
            if not message.content.endswith("**"): return  # don't unclaim if run is already unclaimed
            name = message.content.splitlines()[-1].split(" ")[-2]
            if name != user.name: return

            await message.edit(content="\r\n".join(message.content.splitlines()[:-1]))  # Cut off verifier line
            await message.add_reaction(mod_data["claimEmoji"])
            await reaction.clear()

    #TODO: add indicator for better times in same category
    @loop(minutes=1)
    async def updateGames(self):
        """Check tracked channels for games"""
        self._log.debug("updateGames running...")
        try:
            for guild_id in save.get_guild_ids():
                mod_data = save.get_module_data(guild_id, MODULE_NAME)
                claim_emoji = mod_data["claimEmoji"]
                unclaim_emoji = mod_data["unclaimEmoji"]
                for channel_id, game_IDs in mod_data["trackedChannels"].items():
                    channel = self.bot.get_channel_typed(int(channel_id), Messageable)
                    if channel is None: continue
                    for game_ID in game_IDs:
                        game = src.get_game(game_ID)
                        messages = channel.history(limit=200, oldest_first=True)
                        unverified = src.get_unverified_runs(game)

                        # Collate messages to Run IDs
                        message_runs: dict[Message, str] = {}
                        async for m in messages:
                            if m.author.id != self.bot.user_id: continue  # skip non-bot messages
                            if not m.content.startswith(f"`{game.name}:"): continue  # skip other game tracking messsages in same channel
                            message_runs[m] = m.content.splitlines()[1].split("/")[-1][:-1]  # get id from url in message (also slicing trailing >)
                        # Post new runs
                        for run in unverified:
                            if run.id not in message_runs.values():
                                await self.postRun(guild_id, channel, run, game)
                        # Remove stale runs
                        for m, runId in message_runs.items():
                            if runId not in [run.id for run in unverified]:
                                await m.delete()
                        # Ensure runs are reacted to (doing this on post risks reacts not actually getting added)
                        messages = channel.history(limit=200, oldest_first=True)
                        async for m in messages:
                            if m.content.endswith(">"):
                                if claim_emoji not in [r.emoji for r in m.reactions]:
                                    await m.add_reaction(claim_emoji)
                            else:  # run is claimed, ensure it has remove react
                                if unclaim_emoji not in [r.emoji for r in m.reactions]:
                                    await m.add_reaction(unclaim_emoji)
        except Exception as e:
            self._log.error("GameTracking.updateGames task failed! Ignoring...")
            self._log.error(e, exc_info=True)

    async def postRun(self, guild_id, channel: Messageable, run: Run, game: Game):
        player_names = {player.name.lower() for player in run.players}
        tag = "" if player_names.isdisjoint(save.get_guild_data(guild_id)["spoileredPlayers"]) else "||"
        await channel.send(f"`{game.name}: {get_category_name(run)}` in {format_time(run.times['primary_t'])} by {tag}{escape_markdown(run.players[0].name)}{tag}\r\n<{run.weblink}>")

def get_category_name(run: Run):
    cat = src.get_category(run.category)

    subcatname = ""
    for varid in run.values:
        var = src.get_variable(varid)
        if var.is_subcategory:
            subcatname += f" - {var.values['values'][run.values[varid]]['label']}"

    if cat.type == "per-level":
        level = src.get_level(run.level)
        return f"{level.name}{subcatname}"

    return f"{cat.name}{subcatname}"

def format_time(time):
    td = str(timedelta(seconds=time))
    if "." in td: td = td[:td.index(".") + 3]  # Strip microseconds if present bc timedelta shows micro- rather than milli-
    while td.startswith("0") or td.startswith(":"):
        td = td[1:]
    return td

def get_timestamp(time: int) -> str:
    return f"<t:{time}:R>"
