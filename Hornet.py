import discord
from discord.ext import commands
import logging

import config

import modules

# Intents (all - members)
intents = discord.Intents.default()
intents.message_content = True
intents.presences = True

# Logging (both to console & file)
log_handler = logging.FileHandler(filename=config.LOG_PATH, encoding="utf-8", mode="w")
discord.utils.setup_logging(handler=log_handler, level=logging.DEBUG)

bot = commands.Bot(command_prefix =';', intents=intents, activity=discord.Game(name="Hollow Knight: Silksong"))

for cmd in modules.modules_commands: # add all module commands
    bot.add_command(cmd)

@bot.command()
async def ping(context):
    await context.send('pong')

print(bot.all_commands)

bot.run(config.token)

