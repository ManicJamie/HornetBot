from typing import Union
import discord
from discord import Emoji
from discord.ext.commands import EmojiConverter, EmojiNotFound, Context, Bot
import discord.ext.commands.converter
import emoji

bot : Bot = None  # set up in Hornet.py

async def toEmoji(ctx : Context, reference: str) -> Union[str, Emoji]:
    """ID/emoji string to either Emoji or str if unicode emoji"""
    try:
        return await EmojiConverter().convert(ctx, reference)
    except EmojiNotFound as e:
        if emoji.is_emoji(reference): return reference # catch unicode emoji
        else: raise e

def toRefString(emoji: Union[Emoji, str]):
    """Emoji id or unicode string"""
    if isinstance(emoji, str): return emoji
    return emoji.id

def toDisplayString(emoji: Union[Emoji, str]) -> str:
    """Emoji client embed or unicode string"""
    if isinstance(emoji, str): return emoji
    return f"<:{emoji.name}:{emoji.id}>"

def refToEmoji(ref: str):
    if str(ref).isdigit(): return bot.get_emoji(ref)
    else: return ref