from discord import AllowedMentions, VoiceChannel
from discord.ext.commands import Bot, Cog, Context, command
from pytimeparse.timeparse import timeparse
import asyncio, time

from components import auth, embeds
import save

MODULE_NAME = __name__.split(".")[-1]

async def setup(bot: Bot):
    save.add_module_template(MODULE_NAME, {"raceVCs" : []})
    bot.add_command(count)
    bot.add_command(pause)
    await bot.add_cog(RaceUtilCog(bot))

async def teardown(bot: Bot):
    bot.remove_command("count")
    bot.remove_command("pause")
    await bot.remove_cog("RaceUtil")

@command(help="Start a countdown (default 15s)",
         aliases=["c", "cd", "countdown"])
async def count(context: Context, duration: str = "15s"):
    if duration.isnumeric(): duration += "s" # For unformatted times, we expect
    duration = timeparse(duration)
    if duration is None:
        await embeds.embed_reply(context, message="Could not parse time string! Enter in format `60s`")
        return
    exit_time = int(time.time() + duration)
    send_time = time.time()
    msg = await context.reply(f"<t:{exit_time}:R>", mention_author=False)
    await asyncio.sleep(duration - (2*(time.time() - send_time)))
    await msg.edit(content=f"{msg.content} Go!", allowed_mentions=AllowedMentions().none())

@command(help="Ping everyone in racing vcs to tell them to pause")
async def pause(context: Context):
    mod_data = save.get_module_data(context.guild.id, MODULE_NAME)
    racers = []
    for vc_id in mod_data["raceVCs"]:
        vc: VoiceChannel = context.guild.get_channel(vc_id)
        racers += vc.members
    await context.send(content=f"Pause {' '.join([f'<@{r.id}>' for r in racers])}", allowed_mentions=AllowedMentions.all())

class RaceUtilCog(Cog, name="RaceUtil", description="Commands for configuring race util commands"):
    def __init__(self, bot: Bot):
        self.bot = bot

    def cog_unload(self):
        pass

    @command(help="Add a race VC")
    @auth.check_admin
    async def addRaceVC(self, ctx: Context, channel: VoiceChannel):
        mod_data = save.get_module_data(ctx.guild.id, MODULE_NAME)
        if channel.id in mod_data["raceVCs"]:
            await embeds.embed_reply(ctx, message=f"Voice channel is already set as a race VC!")
            return
        mod_data["raceVCs"].append(channel.id)
        save.save()
        await embeds.embed_reply(ctx, message=f"Voice channel {channel.jump_url} set as a race VC")

    @command(help="Remove a race vc")
    @auth.check_admin
    async def removeRaceVC(self, ctx: Context, channel: VoiceChannel):
        mod_data = save.get_module_data(ctx.guild.id, MODULE_NAME)
        mod_data["raceVCs"].remove(channel.id)
        save.save()
        await embeds.embed_reply(ctx, message=f"Race channel {channel.jump_url} removed")
