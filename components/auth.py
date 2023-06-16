import discord
from discord.ext import commands
import asyncio

import save, config

async def isAdmin(context: commands.Context) -> bool:
    if not await guildExists(context):
        return False
    #if context.author.guild.owner == context.author: return True # server owner is an admin #TODO: uncomment when testing done
    for role in context.author.roles:
        if role.id in save.data["guilds"][str(context.guild.id)]["admins"]:
            return True
    return False

async def isGlobalAdmin(context: commands.Context) -> bool:
    return context.author.id in config.admins

async def guildExists(context: commands.Context) -> bool:
    if str(context.guild.id) not in save.data["guilds"].keys():
        await context.reply("This server isn't registered to Hornet! Contact an admin to register this server")
        return False
    return True