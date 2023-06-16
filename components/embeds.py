import discord.embeds as e
import discord.ext.commands as commands

class EmbedContext():
    def __init__(self, context: commands.Context):
        self.context = context

    async def embedReply(self, message=None, title=None):
        await self.context.reply(embed=e.Embed(description=message, title=title))

async def embedReply(context, message=None, title=None):
    await context.reply(embed=e.Embed(description=message, title=title))

async def embedMessage(dest, message=None, title=None, fields=None):
    construct = e.Embed(description=message, title=title)
    for f in fields:
        construct.add_field(name=f[0], value=f[1])
    await dest.send(construct)

