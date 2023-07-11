from typing import Any, Mapping, Optional, List
from discord.ext import commands
from discord.ext.commands import Cog, Command, HelpCommand
from discord.ext.commands.context import Context
import discord
import discord.embeds as e
from discord.ext.commands.core import Command

from discord.ext.commands._types import BotT

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
    
    async def command_callback(self, ctx: Context[BotT], /, *, command: Optional[str] = None) -> None:
        """Override of default callback for case-insensitive cog help implementation"""
        await self.prepare_help_command(ctx, command)

        bot : commands.Bot = ctx.bot

        if command is None:
            mapping = self.get_bot_mapping()
            return await self.send_bot_help(mapping)

        # Check if it's a cog
        cogs = bot.cogs
        cogs = {k.lower():v for (k, v) in bot.cogs.items()}
        if command.lower() in cogs.keys():
            return await self.send_cog_help(cogs[command.lower()])

        maybe_coro = discord.utils.maybe_coroutine

        # If it's not a cog then it's a command.
        # Since we want to have detailed errors when someone
        # passes an invalid subcommand, we need to walk through
        # the command group chain ourselves.
        keys = command.split(' ')
        cmd = bot.all_commands.get(keys[0])
        if cmd is None:
            string = await maybe_coro(self.command_not_found, self.remove_mentions(keys[0]))
            return await self.send_error_message(string)

        for key in keys[1:]:
            try:
                found = cmd.all_commands.get(key)  # type: ignore
            except AttributeError:
                string = await maybe_coro(self.subcommand_not_found, cmd, self.remove_mentions(key))
                return await self.send_error_message(string)
            else:
                if found is None:
                    string = await maybe_coro(self.subcommand_not_found, cmd, self.remove_mentions(key))
                    return await self.send_error_message(string)
                cmd = found

        if isinstance(cmd, commands.Group):
            return await self.send_group_help(cmd)
        else:
            return await self.send_command_help(cmd)

def getParams(cmd: Command):
    paramstring = ""
    for name, param in cmd.params.items():
        if not param.required: 
            paramstring += f"*<{param.name}>* "
        else: 
            paramstring += f"<{param.name}> "
    return cmd.usage if cmd.usage is not None else paramstring