from discord import Forbidden, Role, Streaming, Game, Status
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
    save.add_global_module_template(MODULE_NAME, {"channel": 0, "guild": 0, "role": 0})
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
    async def set_hkc_channel(self, ctx: Context, channel_id: int):
        save.get_global_module(MODULE_NAME)["channel"] = channel_id
        save.save()
        await embeds.embed_reply(ctx, f"Set HKC channel ID to {channel_id}!")
    
    @command()
    @auth.check_global_admin
    async def set_hkc_role(self, ctx: Context, role: Role):
        mod_data = save.get_global_module(MODULE_NAME)
        if not role.is_assignable():
            await embeds.embed_reply(ctx, "Hornet can't use this role! Move Hornet's role above this one!")
            return
        mod_data["role"] = role.id
        mod_data["guild"] = ctx.guild.id
        save.save()
        await embeds.embed_reply(ctx, f"Set role to {role.id}, set guild to {ctx.guild.id}")

    @loop(minutes=1)
    async def HKCListen(self):
        try:
            channel_id = save.get_global_module(MODULE_NAME)["channel"]
            guild_id = save.get_global_module(MODULE_NAME)["guild"]
            role_id = save.get_global_module(MODULE_NAME)["role"]
            if channel_id == 0: 
                self._log.info("No channel specified for HKCListen, ignoring")
                return
            
            set_role = False
            if (guild_id == 0 or role_id == 0):
                self._log.info("Guild id or role id not set! Ignoring role...")
            else:
                guild = self.bot.get_guild(guild_id)
                if guild is None:
                    self._log.warning("Guild could not be found! Ignoring role...")
                else:
                    role = guild.get_role(role_id)
                    if role is None:
                        self._log.warning("Role could not be found! Ignoring role...")
                    else:
                        bot_user = guild.get_member(self.bot.user.id)
                        set_role = True
            
            if await twitch.check_channel_live(channel_id):
                title = await twitch.get_title(channel_id)
                username = await twitch.get_username(channel_id)
                activity = Streaming(details=title, name="Twitch", created_at=int(time.time() * 1000),
                                        state="Hollow Knight", url=await twitch.get_channel_url(channel_id),
                                        assets={"large_image": f"twitch:{username}"})
                await self.bot.change_presence(activity=activity)
                self._log.info(f"Updated live w/ title {title}")

                if set_role:
                    try:
                        await bot_user.add_roles(role, reason=f"Hornet: Going live...")
                        self._log.info("Live role given")
                    except Forbidden:
                        self._log.error("Hornet isn't allowed to add this role! Ensure her role is higher than the role to be removed.")

            else:
                activity = Game(name="Hollow Knight: Silksong")
                await self.bot.change_presence(activity=activity)
                self._log.info("Went offline.")

                if set_role:
                    try:
                        await bot_user.remove_roles(role, reason=f"Hornet: Going offline...")
                        self._log.info("Live role removed")
                    except Forbidden:
                        self._log.error("Hornet isn't allowed to remove this role! Ensure her role is higher than the role to be removed.")
        except Exception as e:
            self._log.error("HKCListener.HKCListen task failed! Ignoring...")
            self._log.error(e, exc_info=True)

