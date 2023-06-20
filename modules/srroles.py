import discord
from discord.ext import commands
from discord.ext.commands import Context
from srcomapi import datatypes as dt

from typing import List

from components import src, auth, embeds
import save

# Module name as stored in save.json
MODULE_NAME = "srroles"

async def setup(bot: commands.Bot):
    await bot.add_cog(srrolesCog(bot))

class srrolesCog(commands.Cog, name="SrcRoles", description="Commands to verify runners"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(usage="<SRC username>", brief="Grants the speedrunner role to verified runners given your SRC username")
    async def grantsrrole(self, context: Context, src_username: str):
        ectx = embeds.EmbedContext(context)
        guild = str(context.guild.id)

        srrole_id = save.getModuleData(guild, MODULE_NAME)["srrole"]
        srrole = context.guild.get_role(srrole_id)
        if srrole is None:
            await ectx.embedReply("SRRoles module is not set up! Ask an admin to use ;setsrrole")
            return

        games = [src.getGame(game) for game in save.getModuleData(guild, MODULE_NAME)["games"]]
        try:
            user = src.findUser(src_username)
        except src.NotFoundException:
            await ectx.embedReply(f"No SRC user with name {src_username}")
            return
        
        try: 
            dc = src.getDiscord(user)
        except src.NotFoundException:
            await ectx.embedReply(f"Please link your discord in your Speedrun.com profile")
            return
        
        if context.author.discriminator != "0": discordname = f"{context.author.name}#{context.author.discriminator}"
        else: discordname = context.author.name
        if dc.lower() != discordname.lower():
            await ectx.embedReply(f"Your discord username doesn't match SRC! Update your SRC profile.")
            return
        
        runs = src.getRunsFromUser(games, user)
        
        if len(runs) > 0:
            if srrole in context.author.roles:
                await ectx.embedReply("You are already verified")
            else:
                await context.author.add_roles(srrole)
                await ectx.embedReply(f"Runner {src_username} verified")
        else:
            await ectx.embedReply("You must have a verified run on speedrun.com!")
        
    @commands.command(brief="Set the role given by ;grantsrrole")
    @commands.check(auth.isAdmin)
    async def setsrrole(self, context: Context, role: discord.Role):
        save.getModuleData(context.guild.id, MODULE_NAME)["srrole"] = role.id
        save.save()
        await embeds.embedReply(context, f"Speedrun role set to {role.name}")

    @commands.command(brief="Sets up games for runner role. Supply game names in quotes.")
    @commands.check(auth.isAdmin)
    async def setsrgames(self, context: Context, *game_names: str):
        games : list[dt.Game] = []
        not_found = []
        for game_name in game_names:
            try:
                games.append(src.getGame(game_name))
            except src.NotFoundException:
                not_found.append(game_name)

        save.getModuleData(context.guild.id, MODULE_NAME)["games"] = [game.name for game in games]
        save.save()

        games = [g.name for g in games]
        await embeds.embedReply(context, message=("Verified:\r\n" + '\r\n'.join(games) + \
                                                   (f"\r\n\r\nCould not find: \r\n {' '.join(not_found)}" if len(not_found) != 0 else '')))

    @commands.command(brief="Get the list of games the speedrunner role checks for runs with")
    async def listsrgames(self, context: Context):
        ectx = embeds.EmbedContext(context)
        games = save.getModuleData(context.guild.id, "srroles")["games"]
        await ectx.embedReply(title= "Verified Games:", message="\r\n".join(games))