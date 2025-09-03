import json
from discord import Emoji, Guild, Message, TextChannel, RawReactionActionEvent
from discord.ext.commands import Cog, command
from discord.abc import Messageable
from discord.ext.tasks import loop
from discord.utils import escape_markdown
from datetime import timedelta
import time
from typing import TYPE_CHECKING, AsyncIterator
if TYPE_CHECKING:
    from Hornet import HornetBot, HornetContext

import re

import speedruncompy
from speedruncompy import Run, Game, Variable, Value, Category, Level, Player, Verified

from components import auth, emojiUtil, src
import save

MODULE_NAME = __name__.split(".")[-1]

MODULE_TEMPLATE = {
    "trackedChannels": {},
    "claimEmoji": "\u2705",
    "unclaimEmoji": "\u274C"
}

RE_RUN_MSG_PATTERN = re.compile(r"\`(?P<category_name>.*)\` in (?P<run_time>.*) by .*\n<https:\/\/www.speedrun.com\/(?P<game_url>.*)\/run\/(?P<run_id>[\w\d]*)>(?:\n\*\*Claimed by (?P<claimant_name>.*) <t:(?P<claim_time>\d*):R>\*\*)?")

async def setup(bot: 'HornetBot'):
    save.add_module_template(MODULE_NAME, MODULE_TEMPLATE)
    await bot.add_cog(GameTrackerCog(bot))

async def teardown(bot: 'HornetBot'):
    await bot.remove_cog("GameTracking")

class GameTrackerCog(Cog, name="GameTracking", description="Module tracking verification queues on speedrun.com"):
    def __init__(self, bot: 'HornetBot'):
        self.bot = bot
        self._log = bot._log.getChild("GameTracker")
        self.update_games.start()

    async def cog_unload(self):
        self.update_games.cancel()

    @command(help="Register a channel to track unverified runs for a game.")
    @auth.check_admin
    async def addgame(self, context: 'HornetContext', channel: TextChannel, *, gamename):
        if context.guild is None: return
        try:
            game = await src.find_game(gamename)
        except src.NotFoundException:
            await context.message.reply(f"Cannot find game `{gamename}`")
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
            game = await src.find_game(gamename)
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
    
    async def get_message_run_dict(self, messages: AsyncIterator[Message], game: Game):
        message_runs: dict[Message, str] = {}
        async for m in messages:
            if m.author.id != self.bot.user_id: continue  # skip non-bot messages
            if not m.content.startswith(f"`{game['name']}:"): continue  # skip other game tracking messsages in same channel
            message_runs[m] = m.content.splitlines()[1].split("/")[-1][:-1]  # get id from url in message (also slicing trailing >)
        return message_runs
    
    @loop(minutes=1)
    async def update_games(self):
        """"""
        try:
            # First, get the games we can moderate
            moderation_games = await speedruncompy.GetModerationGames(_api=src.CLIENT).perform_async()
            if moderation_games.games is None:
                if src.CLIENT.PHPSESSID is None:
                    raise Exception("Client not logged in - updateGames cancelled")
                self._log.error("SRC failed to return moderation games, skipping iteration...")
                return

            moderated_games = {game["id"]: game for game in moderation_games.games}
            
            for guild_id in save.get_guild_ids():
                mod_data = save.get_module_data(guild_id, MODULE_NAME)
                guild: Guild = self.bot.get_guild(int(guild_id))  # type:ignore
                claim_emoji = mod_data["claimEmoji"]
                unclaim_emoji = mod_data["unclaimEmoji"]
                for channel_id, game_ids in mod_data["trackedChannels"].items():
                    channel = self.bot.get_channel_typed(int(channel_id), TextChannel)
                    if channel is None:
                        self._log.error("Log channel inaccessible, skipping...")
                        continue
                    
                    for game_id in game_ids:
                        if game_id not in moderated_games:
                            self._log.error(f"Hornet does not moderate {game_id}, skipping iteration...")
                            await self.bot.guild_log(guild, f"Hornet does not moderate {game_id}, skipping iteration...", "GameTracker")
                            continue
                        game = moderated_games[game_id]
                        
                        moderation_runs = await speedruncompy.GetModerationRuns(game_id, limit=100, verified=Verified.PENDING, _api=src.CLIENT).perform_all_async()  # type: ignore # This is always str
                        # TODO: downstream types of this should be updated once speedruncompy either fixes #8 or switches to pydantic
                        
                        # Extract associated values for lookup (nb: these will probably be moved to speedruncompy)
                        categories = {c.id: c for c in moderation_runs.categories}
                        levels = {l.id: l for l in moderation_runs.levels}
                        variables = {v.id: v for v in moderation_runs.variables}
                        values = {v.id: v for v in moderation_runs.values}
                        runs = {r.id: r for r in moderation_runs.runs}
                        players = {p.id: p for p in moderation_runs.players}
                        
                        # Collate run IDs from message history
                        messages = channel.history(limit=200, oldest_first=True)
                        message_runIDs = await self.get_message_run_dict(messages, game)
                        
                        # Post new runs
                        for run in moderation_runs.runs:
                            if run.id not in message_runIDs.values():
                                await channel.send(get_run_string(run, channel.guild.id, game, categories, variables, values, levels, players))
                        
                        # Remove stale runs
                        for m, run_id in message_runIDs.items():
                            if run_id not in runs:
                                await m.delete()  # TODO: Shouldn't be mass deleting individually but idc
                        
                        # Ensure runs are reacted to; we need to do this _after_ ensuring the messages exist
                        messages = channel.history(limit=200, oldest_first=True)
                        async for m in messages:
                            if m.author.id != self.bot.user_id: continue  # skip non-bot messages
                            match = RE_RUN_MSG_PATTERN.match(m.content)
                            if match is None:
                                self._log.warning(f"Could not process match for own message w/ content {m.content}")
                                continue
                            claimant_name = match.group("claimant_name")
                            if claimant_name is None:
                                if claim_emoji not in [r.emoji for r in m.reactions]:
                                    await m.add_reaction(claim_emoji)
                            else:  # run is claimed, ensure it has remove react
                                if unclaim_emoji not in [r.emoji for r in m.reactions]:
                                    await m.add_reaction(unclaim_emoji)
        except speedruncompy.exceptions.ServerException as e:
            self._log.error("GameTracking.updateGames task failed due to SRC error, ignoring...")
            self._log.error(e, exc_info=True)
        except speedruncompy.exceptions.ClientException as e:
            self._log.error("GameTracking.updateGames task failed due to client error, ignoring...")
            self._log.error(e, exc_info=True)

def get_player_formatted(guild_id: int, name: str) -> str:
    return f"||{escape_markdown(name)}||" if name in save.get_guild_data(guild_id)["spoileredPlayers"] else escape_markdown(name)

def get_run_string(run: Run, guild_id: int, game: Game, categories: dict[str, Category], variables: dict[str, Variable], values: dict[str, Value], levels: dict[str, Level], players: dict[str, Player]):
    category = categories[run.categoryId]
    
    subcatname = ""
    for valId in run.valueIds:
        val = values[valId]
        var = variables[val.variableId]
        if var.isSubcategory: subcatname += f" - {val.name}"
    
    if category.isPerLevel:
        level = levels[run.levelId]
        category_str = f"{level.name}{subcatname}"
    else:
        category_str = f"{category.name}{subcatname}"
    
    primary_t = run.time if (run.time is not None) else run.timeWithLoads
    
    player_names = " & ".join([get_player_formatted(guild_id, players[p].name.lower()) for p in run.playerIds])
    
    return f"""`{game['name']}: {category_str}` in {format_time(primary_t)} by {player_names}
<https://www.speedrun.com/{game['url']}/run/{run.id}>"""

def format_time(time):
    # TODO: this feels stupid, think of a better way to do this
    td = str(timedelta(seconds=time))
    if "." in td: td = td[:td.index(".") + 3]  # Strip microseconds if present bc timedelta shows micro- rather than milli-
    while td.startswith("0") or td.startswith(":"):
        td = td[1:]
    return td
