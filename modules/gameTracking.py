import discord
from discord.ext import commands, tasks
import srcomapi.datatypes as dt
from datetime import timedelta
import logging, time

from components import src, auth, emojiUtil
import save

MODULE_NAME = __name__.split(".")[-1]

MODULE_TEMPLATE = {
    "channels": [],
    "claimEmoji": "\u2705",
    "unclaimEmoji": "\u274C"
}

async def setup(bot: commands.Bot):
    save.addModuleTemplate(MODULE_NAME, MODULE_TEMPLATE)
    await bot.add_cog(gameTrackerCog(bot))

async def teardown(bot: commands.Bot):
    await bot.remove_cog("GameTracking")

class gameTrackerCog(commands.Cog, name="GameTracking", description="Module tracking verification queues on speedrun.com"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.updateGames.start()
    
    def cog_unload(self):
        self.updateGames.cancel()

    @commands.command(help="Register a channel to track unverified runs for a game.")
    @commands.check(auth.isAdmin)
    async def addgame(self, context: commands.Context, channel : discord.TextChannel, *, gamename):
        save.getModuleData(context.guild.id, MODULE_NAME)["channels"].append({str(channel.id): gamename})
        save.save()
        await context.message.delete()

    @commands.command(help="Unregister a channel from tracking unverified runs for this game.")
    @commands.check(auth.isAdmin)
    async def removegame(self, context: commands.Context, channel : discord.TextChannel, *, gamename):
        save.getModuleData(context.guild.id, MODULE_NAME)["channels"].remove({str(channel.id): gamename})
        save.save()
        await context.message.delete()

    @commands.command(help="Sets emoji used for claims (will not clear old reacts!)")
    @commands.check(auth.isAdmin)
    async def setClaimEmoji(self, context: commands.Context, emoji : str):
        emoji = await emojiUtil.toEmoji(context, emoji)
        emoji_ref = emojiUtil.toString(emoji)
        save.getModuleData(context.guild.id, MODULE_NAME)["claimEmoji"] = emoji_ref
        save.save()
        await context.message.delete()

    @commands.command(help="Sets emoji used for unclaims (will not clear old reacts!)")
    @commands.check(auth.isAdmin)
    async def setUnclaimEmoji(self, context: commands.Context, emoji : str):
        emoji = await emojiUtil.toEmoji(context, emoji)
        emoji_ref = emojiUtil.toString(emoji)
        save.getModuleData(context.guild.id, MODULE_NAME)["unclaimEmoji"] = emoji_ref
        save.save()
        await context.message.delete()

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """Handler on adding reacts in tracked verifier channels"""
        modData = save.getModuleData(payload.guild_id, MODULE_NAME)
        if str(payload.channel_id) not in [list(x.keys())[0] for x in modData["channels"]]: return
        if payload.user_id == self.bot.user.id: return

        message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
        refstring = emojiUtil.toString(payload.emoji)
        reactions = list(filter(lambda x: emojiUtil.toString(x.emoji) == refstring, message.reactions))
        reaction = reactions[0]
        reacters = []
        async for user in reaction.users():
            if user.id != self.bot.user.id: reacters.append(user)

        if len(reacters) == 0: return

        if refstring == modData["claimEmoji"]: 
            if message.content.endswith("**"): return # don't claim if run already claimed
            
            await message.edit(content=f"{reaction.message.content}\r\n**Claimed by {self.bot.get_user(payload.user_id).name}**")
            await message.add_reaction(modData["unclaimEmoji"])
            await reaction.clear()
        elif refstring == modData["unclaimEmoji"]:
            if message.content.endswith(">"): return # don't unclaim if run is already unclaimed
            name = message.content.splitlines()[-1].split(" ")[-1].removesuffix("**")
            if name != self.bot.get_user(payload.user_id).name: return

            await message.edit(content="\r\n".join(message.content.splitlines()[:-1])) # Cut off verifier line
            await message.add_reaction(modData["claimEmoji"])
            await reaction.clear()

    #TODO: add indicator for better times in same category
    @tasks.loop(minutes=1)
    async def updateGames(self):
        """Check tracked channels for games"""
        logging.log(logging.DEBUG, "updateGames running...")
        try:
            for guildID in save.data["guilds"].keys():
                modData = save.getModuleData(guildID, MODULE_NAME)
                claimEmoji = modData["claimEmoji"]
                unclaimEmoji = modData["unclaimEmoji"]
                for singletonDict in modData["channels"]:
                    channelID = list(singletonDict.keys())[0]
                    game = src.getGame(singletonDict[channelID])
                    channel = self.bot.get_channel(int(channelID))
                    messages = channel.history(limit=200, oldest_first=True)
                    unverified = src.getUnverifiedRuns(game)

                    # Collate messages to Run IDs
                    messageRuns = {}
                    async for m in messages:
                        if m.author.id != self.bot.user.id: continue # skip non-bot messages
                        messageRuns[m] = m.content.splitlines()[1].split("/")[-1][:-1] # get id from url in message (also slicing trailing >)
                    # Post new runs
                    for run in unverified:
                        if run.id not in messageRuns.values():
                            await self.postRun(channel, run, game)
                    # Remove stale runs
                    for m, runId in messageRuns.items():
                        if runId not in [run.id for run in unverified]:
                            await m.delete()
                    # Ensure runs are reacted to (doing this on post risks reacts not actually getting added)
                    messages = channel.history(limit=200, oldest_first=True)
                    async for m in messages:
                        if m.content.endswith(">"):
                            if claimEmoji not in [r.emoji for r in m.reactions]:
                                await m.add_reaction(claimEmoji)
                        else: # run is claimed, ensure it has remove react
                            if unclaimEmoji not in [r.emoji for r in m.reactions]:
                                await m.add_reaction(unclaimEmoji)
        except Exception as e:
            logging.log(logging.ERROR, "GameTracking.updateGames task failed! Ignoring...")
            logging.log(logging.ERROR, e, exc_info=True)
    
    async def postRun(self, channel: discord.TextChannel, run: dt.Run, game: dt.Game):
        playernames = {p.name.lower() for p in run.players}
        tag = "" if playernames.isdisjoint(save.getGuildData(channel.guild.id)["spoileredPlayers"]) else "||"
        await channel.send(f"`{game.name}: {categoryName(run)}` in {formatTime(run.times['primary_t'])} by {tag}{run.players[0].name}{tag}\r\n<{run.weblink}>")

def categoryName(run: dt.Run):
    cat = src.getCategory(run.category)

    subcatname = ""
    for varid in list(run.values.keys()):
        var = src.getVariable(varid)
        if var.is_subcategory: 
            subcatname = f" - {var.values['values'][run.values[varid]]['label']}"
            break
    
    if cat.type == "per-level":
        level = src.getLevel(run.level)
        return f"{level.name}{subcatname}"

    return f"{cat.name}{subcatname}"

def formatTime(time):
    td = str(timedelta(seconds=time))
    if "." in td: td = td[:td.index(".") + 3] # Strip microseconds if present bc timedelta shows micro- rather than milli-
    while td.startswith("0") or td.startswith(":"):
        td = td[1:]
    return td