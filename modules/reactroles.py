import discord
from discord.ext import commands, tasks
from discord.ext.commands import Context
from discord import Message, Role, Emoji, PartialEmoji

from components import auth, embeds, emojiUtil
import save

MODULE_NAME = "reactRoles"

"""This is a weird schema, but it works and doesnt require storing 80 billion things
{
    "`channelid`_`messageid`<:`emojiname`:`emojiid`>" : `roleid`
}
"""

async def setup(bot: commands.Bot):
    save.addModuleTemplate(MODULE_NAME, {})
    await bot.add_cog(reactRolesCog(bot))

class reactRolesCog(commands.Cog, name="ReactRoles", description="Handles reaction roles"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    def cog_unload(self):
        pass

    @commands.command(help="Adds a react role to given message")
    @commands.check(auth.isAdmin)
    async def addReactRole(self, context: Context, message : Message, role : Role, emoji : str):
        emojiRef = await emojiUtil.toEmoji(context, emoji)
        modData = save.getModuleData(context.guild.id, MODULE_NAME)
        modData[f"{message.channel.id}_{message.id}_{emojiRef}"] = role.id
        save.save()
        await message.add_reaction(emoji)
        await embeds.embedReply(context, message=f"Added reaction role <@&{role.id}> for {emojiUtil.toString(emojiRef)} on {message.jump_url}")
    
    @commands.command(help="Removes react role from a message")
    @commands.check(auth.isAdmin)
    async def removeReactRole(self, context: Context, message : Message, emoji : str):
        emojiRef = await emojiUtil.toEmoji(context, emoji)
        modData = save.getModuleData(context.guild.id, MODULE_NAME)
        exitrole = modData.pop([f"{message.channel.id}_{message.id}_{emojiRef}>"])
        save.save()
        await embeds.embedReply(context, message=f"Removed reaction role <@&{exitrole}> for {emojiUtil.toString(emojiRef)} on {message.jump_url}")

    @commands.command(help="List react roles")
    @commands.check(auth.isAdmin)
    async def listReactRoles(self, context: Context):
        modData = save.getModuleData(context.guild.id, MODULE_NAME)
        roleTuples = []
        for reactstr, role_id in modData.items():
            channel_id, _, reactstr = str(reactstr).partition("_")
            msg_id, _, emoji_ref = reactstr.partition("_")
            emoji = await emojiUtil.toEmoji(emoji_ref)
            roleTuples.append(("Message", f"https://discord.com/channels/{context.guild.id}/{channel_id}/{msg_id}", True))
            roleTuples.append(("Emoji", f"{emojiUtil.toString(emoji)}", True))
            roleTuples.append(("Role", f"<@&{role_id}>", True))
        save.save()
        await embeds.embedReply(context, title="React Roles", fields=roleTuples)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        emoji_id = payload.emoji.name if payload.emoji.is_unicode_emoji() else emojiUtil.toString(payload.emoji)
        key = f"{payload.channel_id}_{payload.message_id}_{emoji_id}"
        modData = save.getModuleData(payload.guild_id, MODULE_NAME)
        if key not in modData: return
        if payload.user_id == self.bot.user.id: return

        guild = self.bot.get_guild(payload.guild_id)
        role = guild.get_role(modData[key])
        user = guild.get_member(payload.user_id)

        await user.add_roles(role, reason="Reactrole add")
    
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        emoji_id = payload.emoji.name if payload.emoji.is_unicode_emoji() else emojiUtil.toString(payload.emoji)
        key = f"{payload.channel_id}_{payload.message_id}_{emoji_id}"
        modData = save.getModuleData(payload.guild_id, MODULE_NAME)
        if key not in modData: return
        if payload.user_id == self.bot.user.id: return

        guild = self.bot.get_guild(payload.guild_id)
        role = guild.get_role(modData[key])
        user = guild.get_member(payload.user_id)

        await user.remove_roles(role, reason="Reactrole remove")