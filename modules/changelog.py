from discord import CategoryChannel, ForumChannel, RawMessageDeleteEvent, RawMessageUpdateEvent, TextChannel
from discord.ext.commands import Cog, command
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from Hornet import HornetBot, HornetContext

from components import auth, embeds
import save

MODULE_NAME = __name__.split(".")[-1]

async def setup(bot: 'HornetBot'):
    save.add_module_template(MODULE_NAME, {"logChannel": 0, "excludeChannels": []})
    await bot.add_cog(ChangelogCog(bot))

async def teardown(bot: 'HornetBot'):
    await bot.remove_cog("Changelog")

class ChangelogCog(Cog, name="Changelog", description="Tracks message edits and deletes"):
    """Tracks message edits and deletes. NOTE: can only show message contents from cached messages ie. fewer than 10k messages ago"""
    def __init__(self, bot: 'HornetBot'):
        self.bot = bot
        self._log = bot._log.getChild("Changelog")

    async def cog_unload(self):
        pass

    @command(help="Set this channel to track message edits and deletes")
    @auth.check_admin
    async def setChangelogChannel(self, context: 'HornetContext', channel: TextChannel):
        if context.guild is None: return
        save.get_module_data(context.guild.id, MODULE_NAME)["logChannel"] = channel.id
        save.get_module_data(context.guild.id, MODULE_NAME)["excludeChannels"].append(channel.id)
        save.save()
        await context.message.delete()

    @command(help="Exclude a channel from this server's changelog")
    @auth.check_admin
    async def excludeChannel(self, context: 'HornetContext', channel: TextChannel):
        if context.guild is None: return
        excludes = save.get_module_data(context.guild.id, MODULE_NAME)["excludeChannels"]
        if channel.id in excludes:
            await context.embed_reply("This channel is already excluded!")
            return
        excludes.append(channel.id)
        save.save()
        await context.message.delete()

    @command(help="Remove a changelog channel exclusion")
    @auth.check_admin
    async def includeChannel(self, context: 'HornetContext', channel: TextChannel):
        if context.guild is None: return
        save.get_module_data(context.guild.id, MODULE_NAME)["excludeChannels"].remove(channel.id)
        save.save()
        await context.message.delete()

    @command(help="List excluded channels")
    @auth.check_admin
    async def listExcludes(self, context: 'HornetContext'):
        if context.guild is None: return
        channels = save.get_module_data(context.guild.id, MODULE_NAME)["excludeChannels"]
        await context.embed_reply(title="Excluded Channels", message='\r\n'.join([f"<#{x}> ({x})" for x in channels]))

    @Cog.listener()
    async def on_raw_message_edit(self, payload: RawMessageUpdateEvent):
        if payload.guild_id is None: return
        mod_data = save.get_module_data(payload.guild_id, MODULE_NAME)
        if payload.channel_id in mod_data["excludeChannels"]: return
        cached = payload.cached_message

        guild = self.bot.get_guild(payload.guild_id)
        if guild is None: return
        target = guild.get_channel_or_thread(mod_data["logChannel"])
        if target is None or isinstance(target, (CategoryChannel, ForumChannel)): return

        data = payload.data

        fields = [("Channel", f"<#{payload.channel_id}>", True),
                  ("Author", f"<@{data['author']['id']}>" if "author" in data.keys() else "Not Found", True),
                  ("Link", f"https://discord.com/channels/{payload.guild_id}/{payload.channel_id}/{data['id']}", True)]
        
        if cached is not None:  # exclusion clause for spurious edit events when possible
            if "content" in data.keys() and cached.content == data["content"]:
                if "attachments" in data.keys() and len(data["attachments"]) >= len(cached.attachments):
                    return

        embed_message = "Old content unavailable"
        if cached is not None:
            embed_message = cached.content
        if "content" in data.keys():
            fields.append(("New Content", f"{data['content'][:1024]}"))
        if cached and len(cached.attachments) > 0:
            fields.append(("Old Attachments", "\r\n".join([a.url for a in cached.attachments]), False))
        if "attachments" in data.keys() and len(data["attachments"]) > 0:
            fields.append(("New Attachments", "\r\n".join([a["url"] for a in data["attachments"]]), False))
        await embeds.embed_message(target, title="Message Edited", fields=fields, message=embed_message)

    @Cog.listener()
    async def on_raw_message_delete(self, payload: RawMessageDeleteEvent):
        if payload.guild_id is None: return
        mod_data = save.get_module_data(payload.guild_id, MODULE_NAME)
        if payload.channel_id in mod_data["excludeChannels"]: return

        guild = self.bot.get_guild(payload.guild_id)
        if guild is None: return
        target = guild.get_channel_or_thread(mod_data["logChannel"])
        if target is None or isinstance(target, (CategoryChannel, ForumChannel)): return

        fields: list[tuple[str, str] | tuple[str, str, bool]] = [("Channel", f"<#{payload.channel_id}>", True)]

        cached = payload.cached_message
        if cached is not None:
            embed_message = ""
            fields.append(("Author", f"<@{cached.author.id}> - {cached.author.name}", True))
            if len(cached.content) > 0:
                embed_message = cached.content
            if len(cached.attachments) > 0:
                fields.append(("Attachments", "\r\n".join([a.url for a in cached.attachments])[:1024], False))
        else:
            embed_message = "Message was not found in cache!"
            fields.append(("Message ID", f"{payload.message_id}"))
        await embeds.embed_message(target, title="Message Deleted", fields=fields, message=embed_message)
