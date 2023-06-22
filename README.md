# Hornet

A highly functional speedrunning discord bot initially made for the [Hollow Knight Speedrunning Community](https://discord.gg/3JtHPsBjHD), rewritten using [discord.py](https://github.com/Rapptz/discord.py).

- Highly modular, using [discord.py](https://github.com/Rapptz/discord.py)'s extension and cog systems (See [moduleguide.md](/modules/module_guide.md))
- Including Speedrun.com api handling using [srcomapi](https://github.com/blha303/srcomapi)

## Using the bot
Host, add to server and use `;help` to initialise your server's persistent storage.

### Existing modules
- `GameTracking` automatically posts unverified runs to a dedicated channel, allowing verifiers to claim runs
- `Srroles` allows verified runners to claim a runner role
- `ReactRoles` & `Moderation` implements most basic bot behaviour, including leveled muting
- `Changelog` to track message edits and deletes
- `CustomCommands` to add basic reply commands

## Credit
Original bot made by Serena and maintained by Slaurent.