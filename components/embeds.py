from discord.ext.commands import Context
from discord import Embed, Message
from discord.abc import Messageable

import config


class EmbedContext(Context):
    @staticmethod
    def get_embed(message: str | None = None, title: str | None = None, fields: list[tuple[str, str] | tuple[str, str, bool]] | None = None):
        embed = Embed(description=message[:4096] if message is not None else None,
                      title=title[:256] if title is not None else None,
                      colour=config.HORNET_COLOUR)
        if fields:
            for i, f in zip(range(25), fields):  # 25 fields is the maximum
                inline = f[2] if len(f) == 3 else False
                embed.add_field(name=f[0][:256], value=f[1][:1024], inline=inline)
        return embed
    
    async def embed_reply(self, message: str | None = None, title: str | None = None, fields: list[tuple[str, str] | tuple[str, str, bool]] | None = None):
        await self.reply(embed=self.get_embed(message, title, fields), mention_author=False)
    
    async def embed_message(self, message: str | None = None, title: str | None = None, fields: list[tuple[str, str] | tuple[str, str, bool]] | None = None):
        await self.send(embed=self.get_embed(message, title, fields))

async def embed_reply(target: Message, message: str | None = None, title: str | None = None, fields: list[tuple[str, str] | tuple[str, str, bool]] | None = None):
    await target.reply(embed=EmbedContext.get_embed(message, title, fields), mention_author=False)
    
async def embed_message(target: Messageable, message: str | None = None, title: str | None = None, fields: list[tuple[str, str] | tuple[str, str, bool]] | None = None):
    await target.send(embed=EmbedContext.get_embed(message, title, fields))
