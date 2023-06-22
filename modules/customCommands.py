import discord
from discord.ext import commands, tasks
from discord.ext.commands import Context
from discord import Message, Role, Emoji

from components import auth, embeds
import save

MODULE_NAME = "CustomCommands"

"""Module json schema
{
    "`command_name`" : "`command_response`"
}
"""

async def setup(bot: commands.Bot):
    save.addModuleTemplate(MODULE_NAME, {})
    await bot.add_cog(customCmdsCog(bot))

class customCmdsCog(commands.Cog, name="CustomCommands", description="Handles adding basic custom commands"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.commands = []
    
    def cog_unload(self):
        pass
    
    async def try_custom_cmd(self, ctx: Context, cmdName : str) -> bool:
        modData = save.getModuleData(ctx.guild.id, MODULE_NAME)
        if cmdName in modData.keys():
            await ctx.reply(modData[cmdName])
            return True
        return False

    @commands.command(help="Adds a custom command")
    @commands.check(auth.isAdmin)
    async def addCommand(self, context: Context, commandName : str, *, response : str):
        ectx = embeds.EmbedContext(context)
        modData = save.getModuleData(context.guild.id, MODULE_NAME)
        if commandName in modData.keys() or commandName in self.bot.all_commands.keys():
            ectx.embedReply(message=f"Command {commandName} already exists")
            return

        modData[commandName] = response
        save.save()
        await ectx.embedReply(title=f"Added custom command {commandName}", message=response)
    
    @commands.command(help="Removes a custom command")
    @commands.check(auth.isAdmin)
    async def removeCommand(self, context: Context, commandName : str):
        ectx = embeds.EmbedContext(context)
        modData = dict(save.getModuleData(context.guild.id, MODULE_NAME))
        if commandName not in modData.keys():
            ectx.embedReply(message=f"Command {commandName} doesn't exist")
            return
        exitval = modData.pop(commandName)
        save.save()
        await embeds.embedReply(context, title=f"Removed command {commandName}", message=exitval)
