import discord
from discord.ext import commands, tasks
import srcomapi.datatypes as dt
from datetime import timedelta

from components import src, auth
import save

MODULE_NAME = "gameTracking"

async def setup(bot: commands.Bot):
    save.addModuleTemplate(MODULE_NAME, {"channels": [], "claimEmoji": 1118829405658157178})
    await bot.add_cog(gameTrackerCog(bot))

class gameTrackerCog(commands.Cog, name="GameTracking", description="Module tracking verification queues on speedrun.com"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.updateGames.start()
    
    def cog_unload(self):
        self.updateGames.cancel()

    @commands.command(help="Register this channel to track unverified runs for a game.")
    @commands.check(auth.isAdmin)
    async def addgame(self, context: commands.Context, *, gamename):
        save.getModuleData(context.guild.id, MODULE_NAME)["channels"].append({str(context.channel.id): gamename})
        save.save()
        await context.message.delete()

    @commands.command(help="Unregister this channel from tracking unverified runs for this game.")
    @commands.check(auth.isAdmin)
    async def removegame(self, context: commands.Context, *, gamename):
        save.getModuleData(context.guild.id, MODULE_NAME)["channels"].remove({str(context.channel.id): gamename})
        save.save()
        await context.message.delete()

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """Handler on adding reacts in tracked verifier channels"""
        if str(payload.channel_id) not in [list(x.keys())[0] for x in save.getModuleData(payload.guild_id, "gameTracking")["channels"]]:
            return

        message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
        reaction = list(filter(lambda x: x.emoji == payload.emoji, message.reactions))[0]

        if reaction.emoji.id != save.getModuleData(payload.guild_id, "gameTracking")["claimEmoji"]: return

        reacters = []
        async for user in reaction.users():
            if user.id != self.bot.user.id: reacters.append(user)

        if len(reacters) == 0: return
        if message.content.endswith("**"): return
        
        await reaction.message.edit(content=f"{reaction.message.content}\r\n**Claimed by {self.bot.get_user(payload.user_id).display_name}**")
        await reaction.clear()

    #TODO: add indicator for better times in same category
    @tasks.loop(minutes=1)
    async def updateGames(self):
        """Check tracked channels for games"""
        for guildID in save.data["guilds"].keys():
            for singletonDict in save.getModuleData(guildID, MODULE_NAME)["channels"]:
                channelID = list(singletonDict.keys())[0]
                game = src.getGame(singletonDict[channelID])
                channel = self.bot.get_channel(int(channelID))
                messages = channel.history(limit=200)
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
                messages = channel.history(limit=200)
                async for m in messages:
                    if m.content.endswith(">"):
                        await m.add_reaction(self.bot.get_emoji(save.getModuleData(channel.guild.id, "gameTracking")["claimEmoji"]))
    
    async def postRun(self, channel: discord.TextChannel, run: dt.Run, game: dt.Game):
        await channel.send(f"`{game.name}: {categoryName(run)}` in {formatTime(run.times['primary_t'])} by {run.players[0].name}\r\n<{run.weblink}>")

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