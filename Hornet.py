from discord import Game, Intents, Role, User, TextChannel
from discord.ext import commands
from discord.ext.commands import Bot, Command, Context
from discord.utils import setup_logging
from datetime import datetime, timedelta
import logging, os, time

from components import auth, emojiUtil, helpcmd, embeds
import config, save

LOGGING_LEVEL = logging.INFO

# Move old log and timestamp
if not os.path.exists(config.LOG_FOLDER): os.mkdir(f"./{config.LOG_FOLDER}")
if os.path.exists(config.LOG_PATH): os.rename(config.LOG_PATH, f"{config.LOG_FOLDER}/{datetime.utcnow().strftime('%Y-%m-%d_%H-%M-%S_hornet.log')}")
# Setup logging
filehandler = logging.FileHandler(filename=config.LOG_PATH, encoding="utf-8", mode="w")
filehandler.setFormatter(logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', '%Y-%m-%d %H:%M:%S', style='{'))
logging.getLogger().addHandler(filehandler) # file log

setup_logging(level=LOGGING_LEVEL) # add stream to stderr & set for discord.py

def get_params(cmd: Command):
    paramstring = ""
    for param in cmd.params.values():
        if not param.required:
            paramstring += f"*<{param.name}>* "
        else:
            paramstring += f"<{param.name}> "
    return cmd.usage if cmd.usage is not None else paramstring

class HornetBot(Bot):
    def __init__(self, **kwargs):
        self._log = logging.getLogger("Hornet")
        # Intents (all)
        intents = Intents.default()
        intents.message_content = True
        intents.presences = True
        intents.members = True
        self.case_insensitive = True
        super().__init__(intents=intents, help_command=helpcmd.HornetHelpCommand(), case_insensitive=True, max_messages=config.cache_size, **kwargs)

    async def guild_log(self, guild_id, msg: str, source:str=None):
        """Log a message to this guild's channel. `source` is appended to the title, ideally for modules to self-identify in logs."""
        guild_data = save.get_guild_data(guild_id)
        guild_channel_id = guild_data.get("logChannel")
        guild_channel = self.get_channel(guild_channel_id)
        if guild_channel is None:
            self._log.warning(f"Guild {guild_id} ({guild_data['nick']}) does not have logging channel! Skipping guild log...")
            self._log.warning(f"Ignored message: {msg}")
            return
        await embeds.embed_message(guild_channel, msg, title=f"Log: {source}")

    async def on_ready(self):
        """Load modules after load"""
        modules = []
        for file in os.listdir(f"modules/"):
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

    async def on_command_error(self, ctx: Context, error: commands.CommandError):
        ectx = embeds.EmbedContext(ctx)

        command = ctx.command
        cog = ctx.cog
        if command and command.has_error_handler(): return
        if cog and cog.has_error_handler(): return

        if isinstance(error, commands.CommandNotFound):
            cmd = ctx.invoked_with
            cog = self.get_cog("CustomCommands")
            if cog and await cog.try_custom_cmd(ctx, cmd): return
            await ectx.embed_reply(title=f"Command {ctx.prefix}{cmd} not found")
            return

        if isinstance(error, commands.CheckFailure):
            await ectx.embed_reply(title="Not permitted", message="You are not allowed to run this command")
            return

        cmd = ctx.command

        if isinstance(error, commands.UserInputError):
            if isinstance(error, commands.MissingRequiredArgument):
                await ectx.embed_reply(
                    title=f"Command: {ctx.prefix}{cmd} {get_params(cmd)}",
                    message=f"Required parameter `{error.param.name}` is missing"
                )
                return
            typename = type(error).__name__
            if typename.endswith("NotFound"):
                typename = typename.removesuffix("NotFound")
                await ectx.embed_reply(
                    title=f"{typename} not found",
                    message=f"{typename} `{error.argument}` could not be found"
                )
                return
        
        if isinstance(error, commands.CommandOnCooldown):
            # ignore cooldown (we could inform the user, but for short cooldowns this should be fine)
            return

        await ectx.embed_reply(
            title=f"Unhandled exception in Hornet!",
            message=f"```{str(error.args)[:4000]}```\r\nIf this message doesn't help, consider reporting to <@196347053100630016>"
        )
        return await super().on_command_error(ctx, error)

bot_instance = HornetBot(command_prefix =';', activity=Game(name="Hollow Knight: Silksong"))

# Base bot commands
@bot_instance.command(help="pong!", hidden=True)
async def ping(context: Context):
    await context.reply('pong!', mention_author=False)

@bot_instance.command(help="ping!", hidden=True)
async def pong(context: Context):
    await context.reply('ping!', mention_author=False)

@bot_instance.command(help="Time since bot went up", hidden=True)
async def uptime(context: Context):
    await embeds.embed_reply(context, title="Uptime:", message=f"{timedelta(seconds=int(time.time() - start_time))}")

@bot_instance.command(help="Get user's avatar by id")
async def avatar(context: Context, user: User = None):
    if user is None: user = context.author
    await context.reply(user.display_avatar.url, mention_author=False)

@bot_instance.command(help="Sets up a log channel for various errors, such as background tasks")
@auth.check_admin
async def setHornetLogChannel(context: Context, channel: TextChannel):
    if not channel.permissions_for(context.guild.self_role):
        await context.reply("Hornet does not have permissions to send messages to this channel")
        return
    save.get_guild_data(context.guild.id)["logChannel"] = channel.id
    save.save()
    await context.reply(f"Log channel set to <#{channel.id}>")

@bot_instance.command(help="Add admin role (owner only)")
@auth.check_owner
async def addAdminRole(context: Context, role: Role):
    save.get_guild_data(context.guild.id)["adminRoles"].append(role.id)
    save.save()
    await context.message.delete()

@bot_instance.command(help="Remove admin role (owner only)")
@auth.check_owner
async def removeAdminRole(context: Context, role: Role):
    save.get_guild_data(context.guild.id)["adminRoles"].remove(role.id)
    save.save()
    await context.message.delete()

@bot_instance.command(help="Set server nickname in save.json (global admin only)")
@auth.check_global_admin
async def setNick(context: Context, nickname: str):
    save.get_guild_data(context.guild.id)["nick"] = nickname
    save.save()
    await context.message.delete()

@bot_instance.command(help="Reload modules (global admin only)")
@auth.check_global_admin
async def reloadModules(context: Context):
    extension_names = list(bot_instance.extensions.keys())
    failed = []
    for extension in extension_names:
        try:
            await bot_instance.reload_extension(extension, package="modules")
            bot_instance._log.info(f"Loaded {extension}")
        except commands.ExtensionError as e:
            bot_instance._log.error(f"Failed to load {extension}; ignoring")
            bot_instance._log.error(e)
            failed.append(extension)
    if not failed:
        await context.reply("Reloaded all modules!", mention_author=False)
    else:
        await context.reply(f"Modules {', '.join(failed)} failed to reload")

start_time = time.time()
bot_instance.run(config.token)
