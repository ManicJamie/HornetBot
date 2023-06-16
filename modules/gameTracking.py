import discord
from discord.ext import commands, tasks
import srcomapi.datatypes as dt
from datetime import timedelta

from components import src, auth
import save

async def setup(bot: commands.Bot):
    await bot.add_cog(gameTrackerCog(bot))

@commands.check(auth.isAdmin)
class gameTrackerCog(commands.Cog, name="Verification Tracking"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.updateGames.start()
    
    def cog_unload(self):
        self.updateGames.cancel()

    @commands.command()
    @commands.check(auth.isAdmin)
    async def addgame(self, context: commands.Context, *args):
        """Register this channel to track unverified runs for a game."""
        args = " ".join(args)
        save.getModuleData(context.guild.id, "gameTracking")["channels"].append({str(context.channel.id): args})
        save.save()
        await context.message.delete()

    @commands.command()
    @commands.check(auth.isAdmin)
    async def removegame(self, context: commands.Context, *args):
        """Unregister this channel from tracking unverified runs for this game."""
        args = " ".join(args)
        save.getModuleData(context.guild.id, "gameTracking")["channels"].remove({str(context.channel.id): args})
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
        if reaction.count < 2: return

        await reaction.message.edit(content=f"{reaction.message.content}\r\n**Claimed by {self.bot.get_user(payload.user_id).display_name}**")
        await reaction.clear()

    #TODO: add indicator for better times in same category
    @tasks.loop(minutes=1)
    async def updateGames(self):
        """Check tracked channels for games"""
        print("updateGames task")
        for guildID in save.data["guilds"]:
            for singletonDict in save.getModuleData(guildID, "gameTracking")["channels"]:
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
    
    async def postRun(self, channel: discord.TextChannel, run: dt.Run, game: dt.Game):
        await channel.send(f"`{game.name}: {categoryName(run)}` in {formatTime(run.times['primary_t'])} by {run.players[0].name}\r\n<{run.weblink}>")
        await channel.last_message.add_reaction(self.bot.get_emoji(save.getModuleData(channel.guild.id, "gameTracking")["claimEmoji"]))

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
    if td.startswith("0:"): 
        td = td[3:]
    return td