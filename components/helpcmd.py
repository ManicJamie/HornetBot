from typing import Any, Mapping, Optional, List
from discord.ext import commands
from discord.ext.commands import Cog, Command, HelpCommand
from discord.ext.commands.context import Context
import discord
import discord.embeds as e
from discord.ext.commands.core import Command

from components import embeds

class HornetHelpCommand(HelpCommand):
    def __init__(self, **options):
        super().__init__(**options)

    async def parseCommands(self, cmds : list[Command]) -> list[tuple]:
        """Parse commands from a list into a set of fields."""
        cmdFields = []
        for cmd in cmds:
            if await cmd.can_run(self.context) and not cmd.hidden:
                cmdFields.append((f"{self.context.prefix}{cmd.qualified_name} {getParams(cmd)}", cmd.help if cmd.help is not None else "", False))
        return sorted(cmdFields, key=lambda a: a[0])

    async def send_bot_help(self, mapping: Mapping[Optional[Cog], List[Command]]):
        cmdFields = await self.parseCommands(mapping[None])
        
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
        commandtuples = await self.parseCommands(cog.get_commands())
        await embeds.embedMessage(self.get_destination(), title=f"Help: {cog.qualified_name} module", fields=commandtuples)

    async def send_command_help(self, command: Command):
        aliases = f"*Aliases: {', '.join(command.aliases)}*\r\n" if len(command.aliases) > 0 else ""
        helpmessage = command.description if command.description else (command.help if command.help else "")
        await embeds.embedMessage(self.get_destination(), title=f"{self.context.prefix}{command.qualified_name} {getParams(command)}", \
                                    message=aliases+helpmessage)

def getParams(cmd: Command):
    paramstring = ""
    for name, param in cmd.params.items():
        if not param.required: 
            paramstring += f"*<{param.name}>* "
        else: 
            paramstring += f"<{param.name}> "
    return cmd.usage if cmd.usage is not None else paramstring