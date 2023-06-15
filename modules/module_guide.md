# Adding Modules

To add a module (discord.py [extension](https://discordpy.readthedocs.io/en/stable/ext/commands/extensions.html#ext-commands-extensions)), place any loading code into a global `async def setup(bot):`. Note this function must be present (even if it does nothing) for the extension to load. This will be called on bot-admin calls to `reloadExtensions`.

Simply decorate commands using the `discord.ext.command()` decorator, then use `bot.add_command(cmd)`. You can also add cogs this way (useful for periodic tasks)

Useful components include:
- `components.embeds.EmbedContext`, which can be used to tidily construct embed replies
- `components.auth`, which can check if the user is a registered admin role or if the server has been registered to Hornet
    - NB: these methods should be added using the `commands.check()` decorator