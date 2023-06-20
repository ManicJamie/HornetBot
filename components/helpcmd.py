from typing import Mapping, Optional, List
from discord.ext import commands
from discord.ext.commands import Cog, Command, HelpCommand
from discord.ext.commands.context import Context
import discord
import discord.embeds as e

from components import embeds

class HornetHelpCommand(HelpCommand):
    def __init__(self, **options):
        self.brief = "Displays this message, or detailed help on a command/module"
        super().__init__(**options)

    async def send_bot_help(self, mapping: Mapping[Optional[Cog], List[Command]]):
        cmdFields = []
        cmdPrefix = self.context.prefix

        cmds = mapping[None]
        for cmd in cmds:
            if await cmd.can_run(self.context):
                cmdFields.append((f"{cmdPrefix}{cmd.qualified_name} {getParams(cmd)}", cmd.brief, False))
        
        cmdFields.append(("__Modules__", "Type ;help <module> for module commands", False))
        
        modules = []
        for cog in mapping:
            if cog is None: continue
            cmds = mapping[cog]
            
            module_allowed = False
            for cmd in cmds:
                if await cmd.can_run(self.context):
                    module_allowed = True
            if module_allowed:
                modules.append((cog.qualified_name, cog.description, True))
            
        await embeds.embedMessage(self.get_destination(), title="Help", fields=cmdFields + modules)

    async def send_cog_help(self, cog: Cog):
        commandtuples = []
        cmdPrefix = await self.context.bot.get_prefix(self.context)
        cmds = cog.get_commands()
        for cmd in cmds:
            if await cmd.can_run(self.context):
                commandtuples.append((f"{cmdPrefix}{cmd.qualified_name} {getParams(cmd)}", cmd.brief, False))
                
        await embeds.embedMessage(self.get_destination(), title=f"Help: {cog.qualified_name} module", fields=commandtuples)

def getParams(cmd: Command):
    paramstring = ""
    for name, param in cmd.params.items():
        if not param.required: 
            paramstring += f"*<{param.name}>* "
        else: 
            paramstring += f"<{param.name}> "
    print(f"{cmd.name} {paramstring}")
    return cmd.usage if cmd.usage is not None else paramstring