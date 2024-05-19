from typing import TYPE_CHECKING, Mapping, Optional, List
from discord.ext import commands
from discord.ext.commands import Bot, Cog, Command, HelpCommand, AutoShardedBot
from discord.ext.commands.context import Context
from discord.ext.commands._types import BotT
from discord.utils import maybe_coroutine

if TYPE_CHECKING:
    from Hornet import HornetBot

from components import embeds

class HornetHelpCommand(HelpCommand):
    async def parse_commands(self, cmds: list[Command]) -> list[tuple]:
        """Parse commands from a list into a set of fields."""
        cmd_fields = []
        for cmd in cmds:
            if await cmd.can_run(self.context) and not cmd.hidden:
                cmd_fields.append((
                    f"{self.context.prefix}{cmd.qualified_name} {get_params(cmd)}",
                    cmd.help if cmd.help is not None else "",
                    False
                ))
        return sorted(cmd_fields, key=lambda a: a[0])

    async def send_bot_help(self, mapping: Mapping[Optional[Cog], List[Command]]):
        bot: 'HornetBot' = self.context.bot  # type:ignore
        cmd_fields = await self.parse_commands(mapping[bot.base])

        cmd_fields.append(("__Modules__", "Type ;help <module> for module commands", False))

        modules = []
        for cog, cmds in mapping.items():
            if cog is None: continue
            module_allowed = False
            for cmd in cmds:
                if await cmd.can_run(self.context):
                    module_allowed = True
            if module_allowed:
                modules.append((cog.qualified_name, cog.description, True))

        await embeds.embed_message(self.get_destination(), title="Help", fields=cmd_fields + modules)

    async def send_cog_help(self, cog: Cog):
        cmd_tuples = await self.parse_commands(cog.get_commands())
        await embeds.embed_message(self.get_destination(), title=f"Help: {cog.qualified_name} module", fields=cmd_tuples)

    async def send_command_help(self, command: Command):
        aliases = f"*Aliases: {', '.join(command.aliases)}*\r\n" if len(command.aliases) > 0 else ""
        help_message = command.description if command.description else (command.help if command.help else "")
        await embeds.embed_message(
            self.get_destination(),
            title=f"{self.context.prefix}{command.qualified_name} {get_params(command)}",
            message=aliases + help_message
        )

    async def command_callback(self, ctx: Context[BotT], /, *, command: Optional[str] = None) -> None:
        """Override of default callback for case-insensitive cog help implementation"""
        await self.prepare_help_command(ctx, command)

        bot: Bot | AutoShardedBot = ctx.bot

        if command is None:
            mapping = self.get_bot_mapping()
            return await self.send_bot_help(mapping)

        # Check if it's a cog
        cogs = {k.lower(): v for (k, v) in bot.cogs.items()}
        cog = cogs.get(command.lower(), None)
        if cog is not None:
            return await self.send_cog_help(cog)

        # If it's not a cog then it's a command.
        # Since we want to have detailed errors when someone
        # passes an invalid subcommand, we need to walk through
        # the command group chain ourselves.
        keys = command.split(" ")
        cmd = bot.all_commands.get(keys[0])
        if cmd is None:
            string = await maybe_coroutine(self.command_not_found, self.remove_mentions(keys[0]))
            return await self.send_error_message(string)

        for key in keys[1:]:
            try:
                found = cmd.all_commands.get(key)  # type: ignore
            except AttributeError:
                string = await maybe_coroutine(self.subcommand_not_found, cmd, self.remove_mentions(key))
                return await self.send_error_message(string)
            else:
                if found is None:
                    string = await maybe_coroutine(self.subcommand_not_found, cmd, self.remove_mentions(key))
                    return await self.send_error_message(string)
                cmd = found

        if isinstance(cmd, commands.Group):
            return await self.send_group_help(cmd)
        else:
            return await self.send_command_help(cmd)

def get_params(cmd: Command):
    param_string = ""
    for param in cmd.params.values():
        if not param.required:
            param_string += f"*<{param.name}>* "
        else:
            param_string += f"<{param.name}> "
    return cmd.usage if cmd.usage is not None else param_string
