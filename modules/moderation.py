from discord import Member, Message, Role, TextChannel, Thread
from discord.ext.commands import Cog, command
from discord.ext.tasks import loop
from pytimeparse.timeparse import timeparse
import time
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from Hornet import HornetBot, HornetContext

from components import auth, embeds, emojiUtil
import save

MODULE_NAME = __name__.split(".")[-1]

async def setup(bot: 'HornetBot'):
    save.add_module_template(MODULE_NAME, {"mutes": {}, "muteRoles": {}, "defaultMute": ""})
    await bot.add_cog(ModerationCog(bot))

async def teardown(bot: 'HornetBot'):
    await bot.remove_cog("Moderation")

class ModerationCog(Cog, name="Moderation", description="Commands used for server moderation"):
    def __init__(self, bot: 'HornetBot'):
        self.bot = bot
        self._log = bot._log.getChild("Moderation")
        self.checkMutes.start()

    async def cog_unload(self):
        self.checkMutes.stop()

    @command(help="DM a member a warning")
    @auth.check_admin
    async def warn(self, context: 'HornetContext', target: Member, *, reason=""):
        if context.guild is None: return
        await embeds.embed_message(target, title=f"You have been warned in {context.guild.name}:", message=reason)

    @command(help="Mute a member at a given level for a given time period. Member is informed via DM")
    @auth.check_admin
    async def muteLevel(self, context: 'HornetContext', target: Member, duration: str, level: str, *, reason):
        if context.guild is None: return
        if level == -1:
            unmute_time = -1
        else:
            if (unmute_time := timeparse(duration)) is None:
                return
            else:
                unmute_time = int(unmute_time)

        mod_data = save.get_module_data(context.guild.id, MODULE_NAME)

        if level not in mod_data["muteRoles"]:
            await context.embed_reply(message="Mute level not found! Check in listMuteLevels!")
            return

        mute_role_id: int = mod_data["muteRoles"][level]
        mute_role = context.guild.get_role(mute_role_id)
        if not mute_role:
            await context.embed_reply(message=f"Mute role id {mute_role_id} not found! Was it deleted?")
            return

        await target.add_roles(mute_role)
        mod_data["mutes"][str(target.id)] = [level, unmute_time]
        save.save()
        await context.embed_reply(f"User muted until <t:{unmute_time}>")
        await embeds.embed_message(
            target,
            title=f"You have been muted at level {level} in {context.guild.name}",
            message=f"Lasts until <t:{unmute_time}>\r\nReason: {reason}"
        )

    @command(help="Mute a member at the default level for a given time period")
    @auth.check_admin
    async def mute(self, context: 'HornetContext', target: Member, duration: str, *, reason):
        if context.guild is None: return
        level = save.get_module_data(context.guild.id, MODULE_NAME)["defaultMute"]
        await self.muteLevel(context, target, duration, level, reason=reason)

    @command(help="Unmute a muted member")
    @auth.check_admin
    async def unmute(self, context: 'HornetContext', target: Member):
        if context.guild is None: return
        mutes: dict[int, list[int]] = save.get_module_data(context.guild.id, MODULE_NAME)["mutes"]
        if target.id not in mutes:
            await context.embed_reply(f"{target.name} isn't muted!")
            return

        exitmute = mutes.pop(target.id)
        save.save()
        await context.embed_reply(f"{target.name} was unmuted from level {exitmute[0]} lasting until <t:{exitmute[1]}>")

    @command(help="Lists active mutes")
    @auth.check_admin
    async def listMutes(self, context: 'HornetContext'):
        if context.guild is None: return
        mutes: dict[int, list[int]] = save.get_module_data(context.guild.id, MODULE_NAME)["mutes"]
        fields = []
        for muted, mute_args in mutes.items():
            user = self.bot.get_user(muted)
            if user is None: return
            fields.append((f"{user.name} ({muted})", f"Level {mute_args[0]} until <t:{mute_args[1]}>"))
        await context.embed_reply(title="Muted members:", fields=fields)

    @command(help="Add a mute level")
    @auth.check_admin
    async def addMuteLevel(self, context: 'HornetContext', level: str, role: Role):
        if context.guild is None: return
        levels: dict = save.get_module_data(context.guild.id, MODULE_NAME)["muteRoles"]
        if level in levels:
            await context.embed_reply(f"Mute level {level} already exists!")
            return

        levels[level] = role.id
        save.save()
        await context.embed_reply(f"Added mute level {level} on role {role.name}")

    @command(help="Remove a mute level")
    @auth.check_admin
    async def removeMuteLevel(self, context: 'HornetContext', level: str):
        if context.guild is None: return
        levels: dict = save.get_module_data(context.guild.id, MODULE_NAME)["muteRoles"]
        if level not in levels:
            await context.embed_reply(f"Mute level {level} doesn't exist!")
            return

        exit_level = levels[level].pop()
        save.save()
        role = context.guild.get_role(exit_level[1])
        role_name = role.name if role is not None else "(Deleted Role)"
        await context.embed_reply(f"Removed mute level {level} on role {role_name}")

    @command(help="Set the default mute level for ;mute")
    @auth.check_admin
    async def setDefaultMuteLevel(self, context: 'HornetContext', level: str):
        if context.guild is None: return
        mod_data = save.get_module_data(context.guild.id, MODULE_NAME)

        if level not in mod_data["muteRoles"]:
            await context.embed_reply("Mute level not found! Check in listMuteLevels!")
            return

        mod_data["defaultMute"] = level
        await context.embed_reply(f"Set default mute level to {level}")

    @command(help="Show a list of mute levels")
    @auth.check_admin
    async def listMuteLevels(self, context: 'HornetContext'):
        if context.guild is None: return
        mod_data = save.get_module_data(context.guild.id, MODULE_NAME)

        level_fields: list[tuple] = []
        for level, id in mod_data["muteRoles"].items():
            role = context.guild.get_role(id)
            if role is None: continue
            level_fields.append((level[0], role, True))

        level_fields.append(("Default Role", mod_data["defaultMute"], False))

        await context.embed_reply(title="Mute levels:", fields=level_fields)

    @command(help="Repost a message to a given channel in this server")
    @auth.check_admin
    async def relay(self, context: 'HornetContext', channel: Thread | TextChannel, *, message):
        if context.guild != channel.guild:
            await context.send("You must run this command in the guild in question!")
            return
        await channel.send(message)

    @command(help="Edit a message posted by Hornet")
    @auth.check_admin
    async def edit_message(self, context: 'HornetContext', message: Message, *, content):
        if message.author != self.bot.user:
            await context.embed_reply(message="Cannot edit a message I did not send!")
            return
        await message.edit(content=content)

    @command(help="Add a reaction to a message")
    @auth.check_admin
    async def react(self, context: 'HornetContext', message: Message, emoji: str):
        emoji_ref = await emojiUtil.to_emoji(context, emoji)
        await message.add_reaction(emoji_ref)

    @command(help="List users that reacted with given emoji. Must be emoji from this server!")
    @auth.check_admin
    async def listreactions(self, context: 'HornetContext', message: Message, emoji: str):
        parsed_emoji = await emojiUtil.to_emoji(context, emoji)
        if parsed_emoji not in [r.emoji for r in message.reactions]:
            await context.embed_reply(message="Reaction not found!")
            return
        index = [r.emoji for r in message.reactions].index(parsed_emoji)
        reaction = message.reactions[index]

        desc = "```\r\n" + ",".join([f"{user.name}" async for user in reaction.users()]) + "```"

        await context.embed_reply(title=f"{reaction.count} reactions on {emojiUtil.to_string(parsed_emoji)} to {message.jump_url}", message=desc)

    @loop(minutes=1)
    async def checkMutes(self):
        for guild_id in save.get_guild_ids():
            guild = self.bot.get_guild(int(guild_id))
            if guild is None: continue
            roles = save.get_module_data(guild_id, MODULE_NAME)["muteRoles"]
            mutes: dict[str, list] = save.get_module_data(guild.id, MODULE_NAME)["mutes"]

            dict_items = list(mutes.items())  # copy dict items to allow mutation during iteration
            for user, mute in dict_items:
                if int(mute[1]) >= int(time.time()) or int(mute[1]) == -1: continue
                member = guild.get_member(int(user))
                role = guild.get_role(roles[mute[0]])
                if role is None:
                    continue
                if member is not None:
                    await member.remove_roles(role, reason="Timed unmute")
                exit_mute = mutes.pop(user)
                print(exit_mute)
                save.save()
