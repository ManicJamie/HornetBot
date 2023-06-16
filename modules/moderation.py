import discord
from discord.ext import commands, tasks

from components import src, auth, embeds
import save

async def setup(bot: commands.Bot):
    await bot.add_cog(ModerationCog(bot))

class ModerationCog(commands.Cog, name="Moderation"):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command()
    @commands.check(auth.isAdmin)
    async def warn(self, userid, *, reason):
        pass