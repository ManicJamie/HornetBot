# Adding Modules

To add a module (discord.py [extension](https://discordpy.readthedocs.io/en/stable/ext/commands/extensions.html#ext-commands-extensions)), place any loading code into a global `async def setup(bot):`. Note this function must be present (even if it does nothing) for the extension to load. This will be called on bot-admin calls to `reloadExtensions`.

Please add commands as a `Cog` unless the module is meant to explicitly extend base functionality. This will provide commands in a submenu of `help`. You can use a `GroupCog` for commands to be added as subcommands, while `Cog` commands will be called as normal.

Please provide commands with `brief` so the help command can correctly display it. If you wish for `help <command>` to return a more detailed command description set the more detailed text as `description`.

`help` will automatically display commands with their parameters obtained from the canonical parameter names; make these human-readable or manually set `usage` to override the auto-generated names.

Useful components include:
- `components.embeds.EmbedContext`, which can be used to slightly more tidily construct embed replies
- `components.auth`, which can check if the user is a registered admin role or if the server has been registered to Hornet
    - NB: these methods should be added using the `commands.check()` decorator, allowing the help command to correctly identify whether the command can be executed