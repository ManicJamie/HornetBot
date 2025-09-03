from discord import Forbidden, Member, Role, Streaming, Game
from discord.ext.commands import Cog, command
from discord.ext.tasks import loop
import time
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from Hornet import HornetBot, HornetContext

from components import twitch, auth
import save

MODULE_NAME = __name__.split(".")[-1]

async def setup(bot: 'HornetBot'):
    save.add_global_module_template(MODULE_NAME, {"channel": 0, "guild": 0, "role": 0})
    await twitch.setup()
    await bot.add_cog(HKCListenerCog(bot))

async def teardown(bot: 'HornetBot'):
    await bot.remove_cog("ReactRoles")

class HKCListenerCog(Cog, name="HKCListener", description="Manages Hornet's Live status"):
    def __init__(self, bot: 'HornetBot'):
        self.bot = bot
        self._log = bot._log.getChild("HKCListener")
        self.live = False

    async def cog_load(self) -> None:
        self.HKCListen.start()

    async def cog_unload(self) -> None:
        self.HKCListen.stop()

    @command()
    @auth.check_global_admin
    async def set_hkc_channel(self, ctx: 'HornetContext', channel_id: int):
        save.get_global_module(MODULE_NAME)["channel"] = channel_id
        save.save()
        await ctx.embed_reply(f"Set HKC channel ID to {channel_id}!")
    
    @command()
    @auth.check_global_admin
    async def set_hkc_role(self, ctx: 'HornetContext', role: Role):
        if ctx.guild is None: return
        mod_data = save.get_global_module(MODULE_NAME)
        if not role.is_assignable():
            await ctx.embed_reply("Hornet can't use this role! Move Hornet's role above this one!")
            return
        mod_data["role"] = role.id
        mod_data["guild"] = ctx.guild.id
        save.save()
        await ctx.embed_reply(f"Set role to {role.id}, set guild to {ctx.guild.id}")

    @loop(minutes=1)
    async def HKCListen(self):
        try:
            channel_id = save.get_global_module(MODULE_NAME)["channel"]
            guild_id = save.get_global_module(MODULE_NAME)["guild"]
            role_id = save.get_global_module(MODULE_NAME)["role"]
            if channel_id == 0:
                self._log.info("No channel specified for HKCListen, ignoring")
                return
            
            role = None
            guild = self.bot.get_guild(guild_id)
            if guild is None:
                self._log.warning("Guild could not be found! Ignoring role...")
            else:
                role = guild.get_role(role_id)
                if role is None:
                    self._log.warning("Role could not be found! Ignoring role...")
            
            bot_user: Member = guild.me  # type:ignore
            
            if await twitch.check_channel_live(channel_id):
                title = await twitch.get_title(channel_id)
                username = await twitch.get_username(channel_id)
                activity = Streaming(details=title, name="Twitch", created_at=int(time.time() * 1000),
                                     state="Hollow Knight", url=await twitch.get_channel_url(channel_id),
                                     assets={"large_image": f"twitch:{username}"})
                await self.bot.change_presence(activity=activity)
                if self.live is False:
                    self._log.info(f"Updated live w/ title {title}")
                if role is not None and role not in bot_user.roles:
                    try:
                        await bot_user.add_roles(role, reason="Hornet: Going live...")
                        self._log.info("Live role given")
                    except Forbidden:
                        self._log.error("Hornet isn't allowed to add this role! Ensure her role is higher than the role to be removed.")
                self.live = True

            else:
                activity = Game(name="Hollow Knight: Silksong")
                await self.bot.change_presence(activity=activity)
                if self.live is True:
                    self._log.info("Went offline.")

                if role in bot_user.roles:
                    try:
                        await bot_user.remove_roles(role, reason="Hornet: Going offline...")
                        self._log.info("Live role removed")
                    except Forbidden:
                        self._log.error("Hornet isn't allowed to remove this role! Ensure her role is higher than the role to be removed.")
                self.live = False
        except Exception as e:
            self._log.error("HKCListener.HKCListen task failed! Ignoring...")
            self._log.error(e, exc_info=True)
