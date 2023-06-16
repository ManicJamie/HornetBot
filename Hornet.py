import discord
from discord.ext import commands, tasks
from discord.ext.commands import Context
import logging
import time, datetime
import os, re

from components import auth, helpcmd

import config
import save

class HornetBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        # Intents (all)
        intents = discord.Intents.default()
        intents.message_content = True
        intents.presences = True
        intents.members = True
        super().__init__(intents=intents, help_command=helpcmd.HornetHelpCommand(), **kwargs) # 

    async def on_ready(self):
        """Add commands & extensions"""

        # Add base commands
        bot.add_command(self.ping)
        bot.add_command(self.uptime)
        bot.add_command(self.avatar)
        bot.add_command(self.addCustomCommand)
        bot.add_command(self.cleanChannel)

        modules = []
        for file in os.listdir(f"{os.path.dirname(__file__)}/modules/"):
            if not file.endswith(".py"): continue
            mod_name = file[:-3]   # strip .py at the end
            modules.append(mod_name)
            
        # Add extensions from /modules/
        for ext in modules:
            await bot.load_extension(f"modules.{ext}")
    
    # Base bot commands
    @commands.command(help="Pong!")
    async def ping(self, context: Context):
        await context.reply('pong!')

    @commands.command(help="Time since bot went up")
    async def uptime(self, context: Context):
        await context.reply(f"Uptime: {datetime.timedelta(seconds=int(time.time() - startTime))}")

    @commands.command(help="Get user's avatar by id")
    async def avatar(self, context: Context, uid: int):
        await context.reply(context.bot.get_user(uid).display_avatar.url)

    @commands.command()
    @commands.check(auth.isAdmin)
    async def addCustomCommand(self, context: Context, *args):
        if len(args) < 2:
            await context.reply(f"Please give args")
            return

    #TODO: Remove this LONG before publishing. this exists just to make testing gameTracking easier
    @commands.command()
    @commands.check(auth.isAdmin)
    @commands.check(auth.isGlobalAdmin)
    async def cleanChannel(self, context: Context):
        async for m in context.channel.history():
            await m.delete()

bot = HornetBot(command_prefix =';', activity=discord.Game(name="Hollow Knight: Silksong"))
    
# Logging (both to console & file)
log_handler = logging.FileHandler(filename=config.LOG_PATH, encoding="utf-8", mode="w")
discord.utils.setup_logging(handler=log_handler, level=logging.DEBUG)

startTime = time.time()
bot.run(config.token)

