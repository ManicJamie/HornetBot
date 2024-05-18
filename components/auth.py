from discord import Member
from discord.ext.commands import Context, check

import config, save

async def is_admin(context: Context) -> bool:
    if not isinstance(context.author, Member) or context.guild is None: return False
    if not await guild_exists(context): return False
    if context.author.guild.owner == context.author: return True  # server owner is an admin
    for role in context.author.roles:
        if role.id in save.data["guilds"][str(context.guild.id)]["adminRoles"]:
            return True
    return False

async def is_owner(context: Context) -> bool:
    if not isinstance(context.author, Member) or context.guild is None: return False
    if not await guild_exists(context): return False
    if context.author.guild.owner == context.author: return True  # server owner is an admin
    else: return False

async def is_global_admin(context: Context) -> bool:
    return context.author.id in config.admins

async def guild_exists(context: Context) -> bool:
    if not isinstance(context.author, Member) or context.guild is None: return False
    if str(context.guild.id) not in save.data["guilds"]:
        save.init_guild_data(str(context.guild.id))
    return True

check_admin = check(is_admin)

check_owner = check(is_owner)

check_global_admin = check(is_global_admin)
