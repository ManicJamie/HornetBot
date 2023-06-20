import discord
from discord.ext import commands

import save, config

async def isAdmin(context: commands.Context) -> bool:
    if not await guildExists(context): return False
    if context.author.guild.owner == context.author: return True # server owner is an admin
    for role in context.author.roles:
        if role.id in save.data["guilds"][str(context.guild.id)]["adminRoles"]:
            return True
    return False

async def isOwner(context: commands.Context) -> bool:
    if not await guildExists(context): return False
    if context.author.guild.owner == context.author: return True # server owner is an admin
    else: return False

async def isGlobalAdmin(context: commands.Context) -> bool:
    return context.author.id in config.admins

async def guildExists(context: commands.Context) -> bool:
    if str(context.guild.id) not in save.data["guilds"].keys():
        save.initGuildData(context.guild.id)
    return True