import discord
from discord.ext import commands, tasks
from discord.ext.commands import Context
from discord import Message, Role, Emoji

from components import auth, embeds
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
    async def addReactRole(self, context: Context, message : Message, role : Role, emoji : Emoji):
        modData = save.getModuleData(context.guild.id, MODULE_NAME)
        modData[f"{message.channel.id}_{message.id}<:{emoji.name}:{emoji.id}>"] = role.id
        save.save()
        await message.add_reaction(emoji)
        await embeds.embedReply(context, message=f"Added reaction role <@&{role.id}> for <:{emoji.name}:{emoji.id}> on {message.jump_url}")
    
    @commands.command(help="Removes react role from a message")
    @commands.check(auth.isAdmin)
    async def removeReactRole(self, context: Context, message : Message, emoji : Emoji):
        modData = save.getModuleData(context.guild.id, MODULE_NAME)
        exitrole = modData.pop([f"{message.channel.id}_{message.id}<:{emoji.name}:{emoji.id}>"])
        save.save()
        await embeds.embedReply(context, message=f"Removed reaction role <@&{exitrole}> for <:{emoji.name}:{emoji.id}> on {message.jump_url}")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        key = f"{payload.channel_id}_{payload.message_id}<:{payload.emoji.name}:{payload.emoji.id}>"
        modData = save.getModuleData(payload.guild_id, MODULE_NAME)
        if key not in modData: return
        if payload.user_id == self.bot.user.id: return

        guild = self.bot.get_guild(payload.guild_id)
        role = guild.get_role(modData[key])
        user = guild.get_member(payload.user_id)

        await user.add_roles(role, reason="Reactrole add")
    
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        key = f"{payload.channel_id}_{payload.message_id}<:{payload.emoji.name}:{payload.emoji.id}>"
        modData = save.getModuleData(payload.guild_id, MODULE_NAME)
        if key not in modData: return
        if payload.user_id == self.bot.user.id: return

        guild = self.bot.get_guild(payload.guild_id)
        role = guild.get_role(modData[key])
        user = guild.get_member(payload.user_id)

        await user.remove_roles(role, reason="Reactrole remove")