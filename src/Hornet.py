from typing import TypeVar
from discord import Game, Guild, Intents, Role, User, TextChannel
from discord.ext import commands
from discord.ext.commands import Bot, Command, Context, Cog, command
from discord.utils import setup_logging

from datetime import datetime, timedelta, UTC
import logging, os, time

from components import auth, helpcmd, embeds
from modules.customCommands import CustomCommandsCog
import config, save

LOGGING_LEVEL = logging.INFO

# Move old log and timestamp
if not os.path.exists(config.LOG_FOLDER): os.mkdir(f"./{config.LOG_FOLDER}")
if os.path.exists(config.LOG_PATH): os.rename(config.LOG_PATH, f"{config.LOG_FOLDER}/{datetime.now(UTC).strftime('%Y-%m-%d_%H-%M-%S_hornet.log')}")
# Setup logging
filehandler = logging.FileHandler(filename=config.LOG_PATH, encoding="utf-8", mode="w")
filehandler.setFormatter(logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', '%Y-%m-%d %H:%M:%S', style='{'))
logging.getLogger().addHandler(filehandler)  # file log

setup_logging(level=LOGGING_LEVEL)  # add stream to stderr & set for discord.py

def get_params(cmd: Command):
    paramstring = ""
    for param in cmd.params.values():
        if not param.required:
            paramstring += f"*<{param.name}>* "
        else:
            paramstring += f"<{param.name}> "
    return cmd.usage if cmd.usage is not None else paramstring

class HornetContext(embeds.EmbedContext, Context):
    """A mixin of context extensions for useful functionality."""
    bot: 'HornetBot'


T = TypeVar("T")

class HornetBot(Bot):
    def __init__(self, **kwargs):
        self._log = logging.getLogger("Hornet")
        self.case_insensitive = True
        super().__init__(intents=Intents.all(), help_command=helpcmd.HornetHelpCommand(), case_insensitive=True, max_messages=config.cache_size, **kwargs)
    
    async def get_context(self, message, *, cls: type[Context] = HornetContext):
        # Override command context for custom commands
        return await super().get_context(message, cls=cls)
    
    async def guild_log(self, guild: Guild | int, msg: str, source: str = ""):
        """Log a message to this guild's channel. `source` is appended to the title, ideally for modules to self-identify in logs."""
        if isinstance(guild, int): guild = self.get_guild(guild)  # type:ignore
        
        guild_data = save.get_guild_data(guild.id)  # type:ignore
        guild_channel_id: int = guild_data.get("logChannel", 0)
        guild_channel: TextChannel = guild.get_channel_or_thread(guild_channel_id)  # type:ignore # TODO: actually guard here
        if guild_channel is None:
            self._log.warning(f"Guild {guild} ({guild_data['nick']}) does not have logging channel! Skipping guild log...")
            self._log.warning(f"Ignored message: {msg}")
            return
        await embeds.embed_message(guild_channel, msg, title=f"Log: {source}")

    async def setup_hook(self):
        """Load modules after load"""
        self.base = BaseCog(self)
        await self.add_cog(self.base)
        
        self.user_id: int = self.user.id  # type:ignore
        self.start_time = time.time()
        
        modules = []
        for file in os.listdir(os.path.dirname(__file__) + "/modules/"):
            if not file.endswith(".py"): continue
            mod_name = file[:-3]   # strip .py at the end
            modules.append(mod_name)

        # Add extensions from /modules/
        for ext in modules:
            try:
                await self.load_extension(f"modules.{ext}")
                self._log.info(f"Loaded {ext}")
                save.init_module(ext)
                self._log.info(f"Module {ext} save template enforced")
            except commands.ExtensionError as e:
                self._log.error(f"Failed to load {ext}", exc_info=e)
                self._log.error(e)
            except save.TemplateEnforcementError as e:
                await self.unload_extension(ext)
                self._log.error(f"Module {ext} failed to enforce template in save.json, unloaded", exc_info=e)

    async def on_command_error(self, ctx: HornetContext, error: commands.CommandError):  # type: ignore
        command = ctx.command
        cog = ctx.cog
        if command and command.has_error_handler(): return
        if cog and cog.has_error_handler(): return

        if isinstance(error, commands.CommandNotFound):
            failed_cmd: str = ctx.invoked_with  # type:ignore
            custom_cog: CustomCommandsCog = self.get_cog("CustomCommands")  # type:ignore
            if custom_cog and await custom_cog.try_custom_cmd(ctx, failed_cmd): return
            await ctx.embed_reply(title=f"Command {ctx.prefix}{failed_cmd} not found")
            return

        if isinstance(error, commands.CheckFailure):
            await ctx.embed_reply(title="Not permitted", message="You are not allowed to run this command")
            return

        cmd: Command = ctx.command  # type:ignore

        if isinstance(error, commands.UserInputError):
            if isinstance(error, commands.MissingRequiredArgument):
                await ctx.embed_reply(
                    title=f"Command: {ctx.prefix}{cmd} {get_params(cmd)}",
                    message=f"Required parameter `{error.param.name}` is missing"
                )
                return
            
            if isinstance(error, commands.BadArgument):
                await ctx.embed_reply(
                    title=f"{type(error).__name__}",
                    message=f"{error.args[0]}"
                )
                return
        
        if isinstance(error, commands.CommandOnCooldown):
            # ignore cooldown (we could inform the user, but for short cooldowns this should be fine)
            return

        await ctx.embed_reply(
            title="Unhandled exception in Hornet!",
            message=f"```{str(error.args)[:4090]}```",
            fields=[("If this message doesn't help, consider reporting to <@196347053100630016>", "")]
        )
        return await super().on_command_error(ctx, error)
    
    def get_channel_typed(self, id: int, channel_type: type[T]) -> T | None:
        channel = self.get_channel(id)
        return channel if isinstance(channel, channel_type) else None

class BaseCog(Cog):
    def __init__(self, bot: HornetBot) -> None:
        self.bot = bot
        super().__init__()
    
    # Base bot commands
    @command(help="pong!", hidden=True)
    async def ping(self, context: HornetContext):
        await context.reply('pong!', mention_author=False)

    @command(help="ping!", hidden=True)
    async def pong(self, context: HornetContext):
        await context.reply('ping!', mention_author=False)

    @command(help="Time since bot went up", hidden=True)
    async def uptime(self, context: HornetContext):
        await context.embed_reply(title="Uptime:", message=f"{timedelta(seconds=int(time.time() - self.bot.start_time))}")

    @command(help="Get user's avatar by id")
    async def avatar(self, context: HornetContext, user: User | None = None):
        toCheck = context.author if user is None else user
        await context.reply(toCheck.display_avatar.url, mention_author=False)

    @command(help="Sets up a log channel for various errors, such as background tasks")
    @auth.check_admin
    async def setHornetLogChannel(self, context: HornetContext, channel: TextChannel):
        if context.guild is None: return
        if not channel.permissions_for(channel.guild.me).send_messages:
            await context.reply("Hornet does not have permissions to send messages to this channel")
            return
        save.get_guild_data(context.guild.id)["logChannel"] = channel.id
        save.save()
        await context.reply(f"Log channel set to <#{channel.id}>")

    @command(help="Add admin role (owner only)")
    @auth.check_owner
    async def addAdminRole(self, context: HornetContext, role: Role):
        if context.guild is None: return
        save.get_guild_data(context.guild.id)["adminRoles"].append(role.id)
        save.save()
        await context.message.delete()

    @command(help="Remove admin role (owner only)")
    @auth.check_owner
    async def removeAdminRole(self, context: HornetContext, role: Role):
        if context.guild is None: return
        save.get_guild_data(context.guild.id)["adminRoles"].remove(role.id)
        save.save()
        await context.message.delete()

    @command(help="Set server nickname in save.json (global admin only)")
    @auth.check_global_admin
    async def setNick(self, context: HornetContext, nickname: str):
        if context.guild is None: return
        save.get_guild_data(context.guild.id)["nick"] = nickname
        save.save()
        await context.message.delete()

    @command(help="Reload modules (global admin only)")
    @auth.check_global_admin
    async def reloadModules(self, context: HornetContext):
        extension_names = list(self.bot.extensions.keys())
        failed = []
        for extension in extension_names:
            try:
                await self.bot.reload_extension(extension, package="modules")
                self.bot._log.info(f"Loaded {extension}")
            except commands.ExtensionError as e:
                self.bot._log.error(f"Failed to load {extension}; ignoring")
                self.bot._log.error(e)
                failed.append(extension)
        if not failed:
            await context.reply("Reloaded all modules!", mention_author=False)
        else:
            await context.reply(f"Modules {', '.join(failed)} failed to reload")

def main():
    bot_instance = HornetBot(command_prefix=';', activity=Game(name="Hollow Knight: Silksong"))
    bot_instance.run(config.token)


if __name__ == "__main__":
    main()
