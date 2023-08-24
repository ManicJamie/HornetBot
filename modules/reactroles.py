from discord import Message, RawReactionActionEvent, Role
from discord.ext.commands import Bot, Cog, Context, command
import logging
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from Hornet import HornetBot

from components import auth, embeds, emojiUtil
import save

MODULE_NAME = __name__.split(".")[-1]

"""This is a weird schema, but it works and doesnt require storing 80 billion things
{
    "`channelid`_`messageid`<:`emojiname`:`emojiid`>" : `roleid`
}
"""

async def setup(bot: Bot):
    save.add_module_template(MODULE_NAME, {})
    await bot.add_cog(ReactRolesCog(bot))

async def teardown(bot: Bot):
    await bot.remove_cog("ReactRoles")

class ReactRolesCog(Cog, name="ReactRoles", description="Handles reaction roles"):
    def __init__(self, bot: 'HornetBot'):
        self.bot = bot
        self._log = bot._log.getChild("ReactRoles")

    def cog_unload(self):
        pass

    @command(help="Adds a react role to given message")
    @auth.check_admin
    async def addReactRole(self, context: Context, message: Message, role: Role, emoji: str):
        emoji_ref = await emojiUtil.to_emoji(context, emoji)
        mod_data = save.get_module_data(context.guild.id, MODULE_NAME)
        mod_data[f"{message.channel.id}_{message.id}_{emoji_ref}"] = role.id
        save.save()
        await message.add_reaction(emoji)
        await embeds.embed_reply(context, message=f"Added reaction role <@&{role.id}> for {emojiUtil.to_string(emoji_ref)} on {message.jump_url}")

    @command(help="Removes react role from a message")
    @auth.check_admin
    async def removeReactRole(self, context: Context, message: Message, emoji: str):
        emoji_ref = await emojiUtil.to_emoji(context, emoji)
        mod_data = save.get_module_data(context.guild.id, MODULE_NAME)
        exit_role = mod_data.pop(f"{message.channel.id}_{message.id}_{emoji_ref}")
        save.save()
        await message.remove_reaction(emoji_ref)
        await embeds.embed_reply(context, message=f"Removed reaction role <@&{exit_role}> for {emojiUtil.to_string(emoji_ref)} on {message.jump_url}")

    @command(help="List react roles")
    @auth.check_admin
    async def listReactRoles(self, context: Context):
        mod_data = save.get_module_data(context.guild.id, MODULE_NAME)
        message = ""
        for react_str, role_id in mod_data.items():
            channel_id, _, react_str = str(react_str).partition("_")
            msg_id, _, emoji = react_str.partition("_")
            message += f"https://discord.com/channels/{context.guild.id}/{channel_id}/{msg_id} | {emoji} | <@&{role_id}>\r\n"
        save.save()
        await embeds.embed_reply(context, title="React Roles", message=message)

    @Cog.listener()
    async def on_raw_reaction_add(self, payload: RawReactionActionEvent):
        emoji_id = payload.emoji.name if payload.emoji.is_unicode_emoji() else emojiUtil.to_string(payload.emoji)
        key = f"{payload.channel_id}_{payload.message_id}_{emoji_id}"
        mod_data = save.get_module_data(payload.guild_id, MODULE_NAME)
        if key not in mod_data: return
        if payload.user_id == self.bot.user.id: return

        guild = self.bot.get_guild(payload.guild_id)
        role = guild.get_role(mod_data[key])
        if not role:
            self._log.error(f"React role could not find role: {key}")
        user = guild.get_member(payload.user_id)

        await user.add_roles(role, reason="Reactrole add")

    @Cog.listener()
    async def on_raw_reaction_remove(self, payload: RawReactionActionEvent):
        emoji_id = payload.emoji.name if payload.emoji.is_unicode_emoji() else emojiUtil.to_string(payload.emoji)
        key = f"{payload.channel_id}_{payload.message_id}_{emoji_id}"
        mod_data = save.get_module_data(payload.guild_id, MODULE_NAME)
        if key not in mod_data: return
        if payload.user_id == self.bot.user.id: return

        guild = self.bot.get_guild(payload.guild_id)
        role = guild.get_role(mod_data[key])
        user = guild.get_member(payload.user_id)

        await user.remove_roles(role, reason="Reactrole remove")
