from discord import TextChannel, RawReactionActionEvent
from discord.ext.commands import Bot, Cog, Context, command
from discord.ext.tasks import loop
from srcomapi.datatypes import Game, Run
from datetime import timedelta
import logging

from components import auth, emojiUtil, src
import save

MODULE_NAME = __name__.split(".")[-1]

MODULE_TEMPLATE = {
    "channels": [],
    "claimEmoji": "\u2705",
    "unclaimEmoji": "\u274C"
}

async def setup(bot: Bot):
    save.add_module_template(MODULE_NAME, MODULE_TEMPLATE)
    await bot.add_cog(GameTrackerCog(bot))

async def teardown(bot: Bot):
    await bot.remove_cog("GameTracking")

class GameTrackerCog(Cog, name="GameTracking", description="Module tracking verification queues on speedrun.com"):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.updateGames.start()

    def cog_unload(self):
        self.updateGames.cancel()

    @command(help="Register a channel to track unverified runs for a game.")
    @auth.check_admin
    async def addgame(self, context: Context, channel: TextChannel, *, gamename):
        save.get_module_data(context.guild.id, MODULE_NAME)["channels"].append({str(channel.id): gamename})
        save.save()
        await context.message.delete()

    @command(help="Unregister a channel from tracking unverified runs for this game.")
    @auth.check_admin
    async def removegame(self, context: Context, channel: TextChannel, *, gamename):
        save.get_module_data(context.guild.id, MODULE_NAME)["channels"].remove({str(channel.id): gamename})
        save.save()
        await context.message.delete()

    @command(help="Sets emoji used for claims (will not clear old reacts!)")
    @auth.check_admin
    async def setClaimEmoji(self, context: Context, emoji: str):
        emoji = await emojiUtil.to_emoji(context, emoji)
        emoji_ref = emojiUtil.to_string(emoji)
        save.get_module_data(context.guild.id, MODULE_NAME)["claimEmoji"] = emoji_ref
        save.save()
        await context.message.delete()

    @command(help="Sets emoji used for unclaims (will not clear old reacts!)")
    @auth.check_admin
    async def setUnclaimEmoji(self, context: Context, emoji: str):
        emoji = await emojiUtil.to_emoji(context, emoji)
        emoji_ref = emojiUtil.to_string(emoji)
        save.get_module_data(context.guild.id, MODULE_NAME)["unclaimEmoji"] = emoji_ref
        save.save()
        await context.message.delete()

    @Cog.listener()
    async def on_raw_reaction_add(self, payload: RawReactionActionEvent):
        """Handler on adding reacts in tracked verifier channels"""
        mod_data = save.get_module_data(payload.guild_id, MODULE_NAME)
        if str(payload.channel_id) not in [list(x.keys())[0] for x in mod_data["channels"]]: return
        if payload.user_id == self.bot.user.id: return

        message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
        refstring = emojiUtil.to_string(payload.emoji)
        reactions = list(filter(lambda x: emojiUtil.to_string(x.emoji) == refstring, message.reactions))
        reaction = reactions[0]
        reacters = []
        async for user in reaction.users():
            if user.id != self.bot.user.id: reacters.append(user)

        if not reacters: return

        if refstring == mod_data["claimEmoji"]: 
            if message.content.endswith("**"): return # don't claim if run already claimed
            
            await message.edit(content=f"{reaction.message.content}\r\n**Claimed by {self.bot.get_user(payload.user_id).name}**")
            await message.add_reaction(mod_data["unclaimEmoji"])
            await reaction.clear()
        elif refstring == mod_data["unclaimEmoji"]:
            if message.content.endswith(">"): return # don't unclaim if run is already unclaimed
            name = message.content.splitlines()[-1].split(" ")[-1].removesuffix("**")
            if name != self.bot.get_user(payload.user_id).name: return

            await message.edit(content="\r\n".join(message.content.splitlines()[:-1])) # Cut off verifier line
            await message.add_reaction(mod_data["claimEmoji"])
            await reaction.clear()

    #TODO: add indicator for better times in same category
    @loop(minutes=1)
    async def updateGames(self):
        """Check tracked channels for games"""
        logging.log(logging.DEBUG, "updateGames running...")
        try:
            for guild_id in save.data["guilds"]:
                mod_data = save.get_module_data(guild_id, MODULE_NAME)
                claim_emoji = mod_data["claimEmoji"]
                unclaim_emoji = mod_data["unclaimEmoji"]
                for singleton_dict in mod_data["channels"]:
                    channel_id = list(singleton_dict.keys())[0]
                    game = src.get_game(singleton_dict[channel_id])
                    channel = self.bot.get_channel(int(channel_id))
                    messages = channel.history(limit=200, oldest_first=True)
                    unverified = src.get_unverified_runs(game)

                    # Collate messages to Run IDs
                    message_runs = {}
                    async for m in messages:
                        if m.author.id != self.bot.user.id: continue # skip non-bot messages
                        message_runs[m] = m.content.splitlines()[1].split("/")[-1][:-1] # get id from url in message (also slicing trailing >)
                    # Post new runs
                    for run in unverified:
                        if run.id not in message_runs.values():
                            await self.postRun(channel, run, game)
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
                        else: # run is claimed, ensure it has remove react
                            if unclaim_emoji not in [r.emoji for r in m.reactions]:
                                await m.add_reaction(unclaim_emoji)
        except Exception as e:
            logging.log(logging.ERROR, "GameTracking.updateGames task failed! Ignoring...")
            logging.log(logging.ERROR, e, exc_info=True)

    async def postRun(self, channel: TextChannel, run: Run, game: Game):
        player_names = { player.name.lower() for player in run.players }
        tag = "" if player_names.isdisjoint(save.get_guild_data(channel.guild.id)["spoileredPlayers"]) else "||"
        await channel.send(f"`{game.name}: {get_category_name(run)}` in {format_time(run.times['primary_t'])} by {tag}{run.players[0].name}{tag}\r\n<{run.weblink}>")

def get_category_name(run: Run):
    cat = src.get_category(run.category)

    subcatname = ""
    for varid in run.values:
        var = src.get_variable(varid)
        if var.is_subcategory:
            subcatname = f" - {var.values['values'][run.values[varid]]['label']}"
            break

    if cat.type == "per-level":
        level = src.get_level(run.level)
        return f"{level.name}{subcatname}"

    return f"{cat.name}{subcatname}"

def format_time(time):
    td = str(timedelta(seconds=time))
    if "." in td: td = td[:td.index(".") + 3] # Strip microseconds if present bc timedelta shows micro- rather than milli-
    while td.startswith("0") or td.startswith(":"):
        td = td[1:]
    return td
