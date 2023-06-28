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
    print(f"Loaded {MODULE_NAME}")

async def teardown(bot: commands.Bot):
    await bot.remove_cog("CustomCommands")

class customCmdsCog(commands.Cog, name="CustomCommands", description="Handles adding basic custom commands"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.commands = []
    
    def cog_unload(self):
        pass
    
    async def try_custom_cmd(self, ctx: Context, cmdName : str) -> bool:
        modData = save.getModuleData(ctx.guild.id, MODULE_NAME)
        tryDict = {k.lower():v for k, v in modData.items()}
        if cmdName.lower() in tryDict.keys():
            await ctx.reply(tryDict[cmdName.lower()], mention_author=False)
            return True
        return False

    @commands.command(help="Adds a custom command")
    @commands.check(auth.isAdmin)
    async def addCommand(self, context: Context, commandName : str, *, response : str):
        ectx = embeds.EmbedContext(context)
        modData = save.getModuleData(context.guild.id, MODULE_NAME)
        if commandName.lower() in [x.lower() for x in modData.keys()] or \
           commandName.lower() in [x.lower() for x in self.bot.all_commands.keys()]:
            await ectx.embedReply(message=f"Command {commandName} already exists")
            return

        modData[commandName] = response
        save.save()
        await ectx.embedReply(title=f"Added custom command {commandName}", message=response)
    
    @commands.command(help="Removes a custom command")
    @commands.check(auth.isAdmin)
    async def removeCommand(self, context: Context, commandName : str):
        ectx = embeds.EmbedContext(context)
        modData = save.getModuleData(context.guild.id, MODULE_NAME)
        if commandName not in modData.keys():
            ectx.embedReply(message=f"Command {commandName} doesn't exist")
            return
        exitval = modData.pop(commandName)
        save.save()
        await ectx.embedReply(title=f"Removed command {commandName}", message=exitval)

    @commands.command(help="Display a list of all custom commands", \
                      aliases=["listCommands", "listCommand", "commandList", "list"])
    async def listCustomCommands(self, context: Context):
        modData = save.getModuleData(context.guild.id, MODULE_NAME)
        msgstr = ""
        for cmd, response in sorted(modData.items()):
            response = escapechars(response)
            msgstr += f";{cmd} | {response if len(response) < 50 else (response[:60] + '...')}\r\n"

        await embeds.embedReply(context, title=f"Custom commands:", message=msgstr)
    
def escapechars(message):
    newmsg = ""
    for char in message:
        if char == "`": newmsg += "\\"
        if char == "\r": newmsg += " "
        if not (char == "\r" or char == "\n"):
            newmsg += char
    return newmsg
