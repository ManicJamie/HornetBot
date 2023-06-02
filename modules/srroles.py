import components.src as src
import discord
from discord.ext import commands

games = [src.getGame("Hollow Knight"), src.getGame("Hollow Knight Category Extensions"), src.getGame("Hollow Knight Mod")]

async def grantsrrole(context, *args):
    name = args[0]
    try:
        if len(src.getRunsFromUser(games, name)) > 0:
            print(f"User {name} verified")
        else:
            print(f"User {name} failed to verify")
    except src.UserNotFoundException:
        print(f"No SRC user with name {name}")

module_commands = {commands.Command(grantsrrole)}