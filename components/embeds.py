from discord.abc import Messageable
from discord.embeds import Embed
from discord.ext.commands import Context
from discord.colour import Colour

HORNET_COLOUR = Colour(0x79414B)

def get_embed(message=None, title=None, fields=None):
    embed = Embed(description=message[:4096] if message is not None else None,
                  title=title[:256] if title is not None else None,
                  colour=HORNET_COLOUR)
    if fields:
        for i, f in enumerate(fields):
            if i > 23: return # Guard against too many fields
            inline = f[2] if len(f) == 3 else False
            embed.add_field(name=f[0][:256], value=f[1][:1024], inline=inline)
    return embed

async def embed_reply(context: Context, message=None, title=None, fields=None):
    await context.reply(embed=get_embed(message, title, fields), mention_author=False)

async def embed_message(dest: Messageable, message=None, title=None, fields=None):
    """Send an embed message to the destination channel/context, with optional fields as a List[Tuple[str, str]]"""
    await dest.send(embed=get_embed(message, title, fields))

class EmbedContext:
    def __init__(self, context: Context):
        self.context = context

    async def embed_reply(self, message=None, title=None, fields=None):
        await embed_reply(self.context, message, title, fields)

    async def embed_message(self, message=None, title=None, fields=None):
        await embed_message(self.context, message, title, fields)
