from discord.ext.commands import Bot, Cog, Context, command

from components import auth, embeds
import save

MODULE_NAME = __name__.split(".")[-1]

"""Module json schema
{
    "`command_name`" : "`command_response`"
}
"""

async def setup(bot: Bot):
    save.add_module_template(MODULE_NAME, {})
    await bot.add_cog(CustomCommandsCog(bot))

async def teardown(bot: Bot):
    await bot.remove_cog("CustomCommands")

class CustomCommandsCog(Cog, name="CustomCommands", description="Handles adding basic custom commands"):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.commands = []
    
    def cog_unload(self):
        pass

    async def try_custom_cmd(self, ctx: Context, command_name: str) -> bool:
        mod_data = save.get_module_data(ctx.guild.id, MODULE_NAME)
        try_dict = { k.lower() : v for k, v in mod_data.items() }
        content = try_dict.get(command_name.lower(), None)
        if content is not None:
            await ctx.reply(content, mention_author=False)
            return True
        return False

    @command(help="Adds a custom command")
    @auth.check_admin
    async def addCommand(self, context: Context, command_name: str, *, response: str):
        ectx = embeds.EmbedContext(context)
        mod_data = save.get_module_data(context.guild.id, MODULE_NAME)
        command_keys = {k.lower() for k in mod_data} | {k.lower() for k in self.bot.all_commands}
        if command_name.lower() in command_keys:
            await ectx.embed_reply(message=f"Command {command_name} already exists")
            return

        mod_data[command_name] = response
        save.save()
        await ectx.embed_reply(title=f"Added custom command {command_name}", message=response)

    @command(help="Removes a custom command")
    @auth.check_admin
    async def removeCommand(self, context: Context, command_name: str):
        ectx = embeds.EmbedContext(context)
        mod_data = save.get_module_data(context.guild.id, MODULE_NAME)
        if command_name not in mod_data:
            ectx.embed_reply(message=f"Command {command_name} doesn't exist")
            return
        exit_val = mod_data.pop(command_name)
        save.save()
        await ectx.embed_reply(title=f"Removed command {command_name}", message=exit_val)

    @command(help="Display a list of all custom commands",
             aliases=["listCommands", "listCommand", "commandList", "list"])
    async def listCustomCommands(self, context: Context):
        mod_data = save.get_module_data(context.guild.id, MODULE_NAME)
        msgstr = ""
        for cmd, response in sorted(mod_data.items()):
            response = escape_chars(response)
            msgstr += f";{cmd} | {response if len(response) < 50 else (response[:60] + '...')}\r\n"

        await embeds.embed_reply(context, title=f"Custom commands:", message=msgstr)

def escape_chars(message):
    newmsg = ""
    for char in message:
        if char == "`": newmsg += "\\"
        if char == "\r": newmsg += " "
        if not (char == "\r" or char == "\n"):
            newmsg += char
    return newmsg
