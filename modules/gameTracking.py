import discord
from discord.ext import commands, tasks
import srcomapi.datatypes as dt
from datetime import timedelta

from components import src, auth
import save

async def setup(bot: commands.Bot):
    global games
    games = [src.getGame("Hollow Knight"), src.getGame("Hollow Knight Category Extensions"), src.getGame("Hollow Knight Mod")]
    bot.add_command(addGame)
    bot.add_command(removeGame)
    await bot.add_cog(gameTrackerCog(bot))

@commands.command()
@commands.check(auth.isAdmin)
async def addGame(context: commands.Context, *args):
    args = " ".join(args)
    save.data["guilds"][str(context.guild.id)]["modules"]["gameTracking"]["channels"].append({context.channel.id: args})
    save.save()
    await context.message.delete()

@commands.command()
@commands.check(auth.isAdmin)
async def removeGame(context: commands.Context, *args):
    args = " ".join(args)
    save.data["guilds"][str(context.guild.id)]["modules"]["gameTracking"]["channels"].remove({context.channel.id: args})
    save.save()
    await context.message.delete()

class gameTrackerCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.updateGames.start()
    
    def cog_unload(self):
        self.updateGames.cancel()

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        message : discord.Message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
        reaction = list(filter(lambda x: x.emoji == payload.emoji, message.reactions))[0]
        if reaction.count < 2: return
        await reaction.message.edit(content=f"{reaction.message.content}\r\n**Claimed by {self.bot.get_user(payload.user_id).display_name}**")
        await reaction.clear()

    @tasks.loop(minutes=1)
    async def updateGames(self):
        for guildID in save.data["guilds"]:
            guildData = save.data["guilds"][guildID]
            for singletonDict in guildData["modules"]["gameTracking"]["channels"]:
                channelID = list(singletonDict.keys())[0]
                game = src.getGame(singletonDict[channelID])
                channel = self.bot.get_channel(int(channelID))
                messages = channel.history(limit=200)
                unverified = src.getUnverifiedRuns(game)

                # Collate messages to Run IDs
                messageRuns = {}
                async for m in messages:
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
        await channel.send(f"{game.name}: {src.getCategory(run.category).name} in {formatTime(run.times['primary_t'])} by {run.players[0].name}\r\n<{run.weblink}>")
        await channel.last_message.add_reaction(self.bot.get_emoji(save.data["guilds"][str(channel.guild.id)]["modules"]["gameTracking"]["claimEmoji"]))

def formatTime(time):
    td = str(timedelta(seconds=time))
    # Strip microseconds if present (why on earth timedelta defaults to showing microseconds is beyond me)
    if "." in td: td = td[:td.index(".") + 4]
    return td