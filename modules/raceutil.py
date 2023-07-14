from discord import VoiceChannel, AllowedMentions
from discord.ext.commands import Bot, Context, Cog, command, check
from pytimeparse.timeparse import timeparse
import asyncio, time

from components import embeds, auth

import save

MODULE_NAME = "RaceUtil"

async def setup(bot: Bot):
    save.addModuleTemplate(MODULE_NAME, {"raceVCs" : []})
    bot.add_command(count)
    bot.add_command(pause)
    await bot.add_cog(RaceUtilCog(bot))

async def teardown(bot: Bot):
    bot.remove_command("count")
    bot.remove_command("pause")
    await bot.remove_cog(MODULE_NAME)

@command(help="Start a countdown (default 15s)", \
                     aliases=["c", "cd", "countdown"])
async def count(context: Context, duration: str = "15s"):
    if duration.isnumeric(): duration += "s" # For unformatted times, we expect
    duration = timeparse(duration)
    if duration is None:
        await embeds.embedReply(context, message="Could not parse time string! Enter in format `60s`")
        return
    exittime = int(time.time() + duration)
    sendTime = time.time()
    msg = await context.reply(f"<t:{exittime}:R>", mention_author=False)
    await asyncio.sleep(duration - (2*(time.time() - sendTime)))
    await msg.edit(content=msg.content + f" Go!", allowed_mentions=AllowedMentions().none())

@command(help="Ping everyone in racing vcs to tell them to pause")
async def pause(context: Context):
    modData = save.getModuleData(context.guild.id, MODULE_NAME)
    racers = []
    for vc_id in modData["raceVCs"]:
        vc : VoiceChannel = context.guild.get_channel(vc_id)
        racers += vc.members
    await context.send(content=f"Pause {' '.join([f'<@{r.id}>' for r in racers])}", allowed_mentions=AllowedMentions.all())

class RaceUtilCog(Cog, name=MODULE_NAME, description="Commands for configuring race util commands"):
    def __init__(self, bot: Bot):
        self.bot = bot

    def cog_unload(self):
        pass
    
    @command(help="Add a race VC")
    @check(auth.isAdmin)
    async def addRaceVC(self, ctx: Context, channel: VoiceChannel):
        modData = save.getModuleData(ctx.guild.id, MODULE_NAME)
        if channel.id in modData["raceVCs"]:
            await embeds.embedReply(ctx, message=f"Voice channel is already set as a race VC!")
            return
        modData["raceVCs"].append(channel.id)
        save.save()
        await embeds.embedReply(ctx, message=f"Voice channel {channel.jump_url} set as a race VC")

    @command(help="Remove a race vc")
    @check(auth.isAdmin)
    async def removeRaceVC(self, ctx: Context, channel: VoiceChannel):
        modData = save.getModuleData(ctx.guild.id, MODULE_NAME)
        modData["raceVCs"].remove(channel.id)
        save.save()
        await embeds.embedReply(ctx, message=f"Race channel {channel.jump_url} removed")
