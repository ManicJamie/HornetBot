from discord import Streaming, Game, Status
from discord.ext.commands import Bot, Cog, Context, command
from discord.ext.tasks import *
import logging, time
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from Hornet import HornetBot

from components import twitch, auth, embeds
import save

MODULE_NAME = __name__.split(".")[-1]

async def setup(bot: Bot):
    save.add_global_module_template(MODULE_NAME, {"channel": 0})
    await twitch.setup()
    await bot.add_cog(HKCListenerCog(bot))

async def teardown(bot: Bot):
    await bot.remove_cog("ReactRoles")

class HKCListenerCog(Cog, name="HKCListener", description="Manages Hornet's Live status"):
    def __init__(self, bot: 'HornetBot'):
        self.bot = bot
        self._log = bot._log.getChild("HKCListener")
        self.HKCListen.start()

    def cog_unload(self):
        self.HKCListen.stop()

    @command()
    @auth.check_global_admin
    async def set_hkc_channel(self, context: Context, channel_id: int):
        save.get_global_module(MODULE_NAME)["channel"] = channel_id
        save.save()
        await embeds.embed_reply(context, f"Set HKC channel ID to {channel_id}!")

    @loop(minutes=1)
    async def HKCListen(self):
        channel_id = save.get_global_module(MODULE_NAME)["channel"]
        if channel_id == 0: 
            self._log.info("No channel specified for HKCListen, ignoring")
            return
        live = await twitch.check_channel_live(channel_id)
        if live:
            title = await twitch.get_title(channel_id)
            username = await twitch.get_username(channel_id)
            activity = Streaming(details=title, name="Twitch", created_at=int(time.time() * 1000),
                                    state="Hollow Knight", url=await twitch.get_channel_url(channel_id),
                                    assets={"large_image": f"twitch:{username}"})
            await self.bot.change_presence(activity=activity, status=Status.online)
            self._log.info(f"Updated live w/ title {title}")
        else:
            activity = Game(name="Hollow Knight: Silksong")
            await self.bot.change_presence(activity=activity, status=Status.online)
            self._log.info("Went offline.")

