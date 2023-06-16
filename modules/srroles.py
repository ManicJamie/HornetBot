import discord
from discord.ext import commands

from components import src, auth, embeds
import save

async def setup(bot: commands.Bot):
    global games
    games = [src.getGame("Hollow Knight"), src.getGame("Hollow Knight Category Extensions"), src.getGame("Hollow Knight Mod")]
    await bot.add_cog(srrolesCog(bot))

class srrolesCog(commands.Cog, name="Speedrun Roles"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def grantsrrole(context: commands.Context, *args):
        ctx = embeds.EmbedContext(context)
        if len(args) == 0:
            await ctx.embedReply("Please call using your speedrun.com username (eg. `;grantsrrole Hornet`)")
            return
        name = args[0]
        guild = str(ctx.guild.id)

        srrole_id = save.getModuleData(guild, "srroles")["srrole"]
        srrole = ctx.guild.get_role(srrole_id)
        if srrole is None:
            await ctx.embedReply("SRRoles module is not set up! Ask an admin to use ;setsrrole")
            return

        games = save.data["guilds"][guild]["modules"]["srroles"]["games"]
        try:
            runs = src.getRunsFromUser(games, name)
        except src.UserNotFoundException:
            await ctx.embedReply(f"No SRC user with name {name}")
            return
        
        if len(runs) > 0:
            if context.author.get_role(srrole_id) is not None:
                await ctx.embedReply("You are already verified")
            else:
                await context.author.add_roles(context.guild.get_role(srrole_id))
                await ctx.embedReply(f"User {name} verified")
        else:
            await ctx.embedReply("You must have a verified run on speedrun.com!")
        
    @commands.command()
    @commands.check(auth.isAdmin)
    async def setsrrole(context: commands.Context, *args):
        ctx = embeds.EmbedContext(context)
        role_id = args[0]

        role = context.guild.get_role(role_id)
        if role is None:
            await ctx.embedReply("Role not found!")
            return
        else:
            save.data["guilds"][context.guild.id]["modules"]["srroles"]["srrole"] = role_id
            save.save()
            await ctx.embedReply(f"Speedrun role set to {role.name}")

    #TODO: setsrrolegames
    