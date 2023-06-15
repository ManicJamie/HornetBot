import discord.embeds as e
import discord.ext.commands as commands

class EmbedContext():
    def __init__(self, context: commands.Context):
        self.context = context

    async def embedReply(self, message=None, title=None):
        await self.context.reply(embed=e.Embed(description=message, title=title))
