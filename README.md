# Hornet

A bot initially made for the [Hollow Knight Speedrunning Community](https://discord.gg/3JtHPsBjHD), rewritten using [discord.py](https://github.com/Rapptz/discord.py).

- Fully modular, using [discord.py](https://github.com/Rapptz/discord.py)'s extension and cog systems
- Including Speedrun.com api handling using [srcomapi](https://github.com/blha303/srcomapi)

## Making modules
See [moduleguide.md](/modules/module_guide.md).

## Using the bot
Host, add to server and use `;help` to initialise your server's persistent storage.

### Existing modules
- `GameTracking` automatically posts unverified runs to a dedicated channel, allowing verifiers to claim runs
- `Srroles` to allow verified runners to claim a runner role
- `ReactRoles` & `Moderation` for most basic behaviour
- `Changelog` to track message edits and deletes 
- `CustomCommands` to add basic reply commands
