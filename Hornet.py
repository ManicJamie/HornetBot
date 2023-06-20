import discord
from discord.ext import commands, tasks
from discord.ext.commands import Context, errors
import logging
import time, datetime
import os, re

from components import auth, helpcmd, embeds

import config
import save

# Logging (both to console & file)
log_handler = logging.FileHandler(filename=config.LOG_PATH, encoding="utf-8", mode="w")
discord.utils.setup_logging(handler=log_handler, level=logging.NOTSET)

def getParams(cmd: commands.Command):
    paramstring = ""
    for name, param in cmd.params.items():
        if not param.required: 
            paramstring += f"*<{param.name}>* "
        else: 
            paramstring += f"<{param.name}> "
    print(f"{cmd.name} {paramstring}")
    return cmd.usage if cmd.usage is not None else paramstring

class HornetBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        # Intents (all)
        intents = discord.Intents.default()
        intents.message_content = True
        intents.presences = True
        intents.members = True
        self.case_insensitive = True
        super().__init__(intents=intents, case_insensitive=True, **kwargs) # 

    async def on_ready(self):
        """Add commands & extensions"""
        modules = []
        for file in os.listdir(f"{os.path.dirname(__file__)}/modules/"):
            if not file.endswith(".py"): continue
            mod_name = file[:-3]   # strip .py at the end
            modules.append(mod_name)
            
        # Add extensions from /modules/
        for ext in modules:
            await self.load_extension(f"modules.{ext}")
    
    async def on_command_error(self, ctx: Context, error: commands.CommandError):
        ectx = embeds.EmbedContext(ctx)
        if isinstance(error, commands.errors.MissingRequiredArgument):
            cmd = ctx.command
            await ectx.embedReply(title=f"Command: {ctx.prefix}{cmd} {getParams(cmd)}", \
                                  message=f"Required parameter `{error.param.name}` is missing")
            return
        return await super().on_command_error(ctx, error)

botInstance = HornetBot(command_prefix =';', activity=discord.Game(name="Hollow Knight: Silksong"))

# Base bot commands
@botInstance.hybrid_command(brief="Pong!")
async def ping(context: Context):
    await context.reply('pong!')

@botInstance.command(brief="Time since bot went up")
async def uptime(context: Context):
    await context.reply(f"Uptime: {datetime.timedelta(seconds=int(time.time() - startTime))}")

@botInstance.command(brief="Get user's avatar by id")
async def avatar(context: Context, user: discord.User):
    await context.reply(user.display_avatar.url)

@botInstance.command(brief="Adds a custom text command")
@commands.check(auth.isAdmin)
async def addCustomCommand(context: Context, cmdName, *, cmdResponse):
    pass 

#TODO: Remove this LONG before publishing. this exists just to make testing gameTracking easier
@botInstance.command()
@commands.check(auth.isAdmin)
@commands.check(auth.isGlobalAdmin)
async def purge(context: Context):
    await context.channel.purge()

startTime = time.time()
botInstance.run(config.token)