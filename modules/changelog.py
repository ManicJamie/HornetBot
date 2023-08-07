from discord import RawMessageDeleteEvent, RawMessageUpdateEvent, TextChannel
from discord.ext.commands import Bot, Cog, Context, command

from components import auth, embeds
import save

MODULE_NAME = __name__.split(".")[-1]

async def setup(bot: Bot):
    save.add_module_template(MODULE_NAME, {"logChannel": 0, "excludeChannels": []})
    await bot.add_cog(ChangelogCog(bot))

async def teardown(bot: Bot):
    await bot.remove_cog("Changelog")

class ChangelogCog(Cog, name="Changelog", description="Tracks message edits and deletes"):
    """Tracks message edits and deletes. NOTE: can only show message contents from cached messages ie. fewer than 10k messages ago"""
    def __init__(self, bot: Bot):
        self.bot = bot

    def cog_unload(self):
        pass

    @command(help="Set this channel to track message edits and deletes")
    @auth.check_admin
    async def setChangelogChannel(self, context: Context, channel: TextChannel):
        save.get_module_data(context.guild.id, MODULE_NAME)["logChannel"] = channel.id
        save.get_module_data(context.guild.id, MODULE_NAME)["excludeChannels"].append(channel.id)
        save.save()
        await context.message.delete()

    @command(help="Exclude a channel from this server's changelog")
    @auth.check_admin
    async def excludeChannel(self, context: Context, channel: TextChannel):
        excludes = save.get_module_data(context.guild.id, MODULE_NAME)["excludeChannels"]
        if channel.id in excludes:
            await embeds.embed_reply(context, message="This channel is already excluded!")
            return
        excludes.append(channel.id)
        save.save()
        await context.message.delete()

    @command(help="Remove a changelog channel exclusion")
    @auth.check_admin
    async def includeChannel(self, context: Context, channel: TextChannel):
        save.get_module_data(context.guild.id, MODULE_NAME)["excludeChannels"].remove(channel.id)
        save.save()
        await context.message.delete()

    @command(help="List excluded channels")
    @auth.check_admin
    async def listExcludes(self, context: Context):
        channels = save.get_module_data(context.guild.id, MODULE_NAME)["excludeChannels"]
        await embeds.embed_reply(context, title="Excluded Channels", message='\r\n'.join([f"<#{x}> ({x})" for x in channels]))

    @Cog.listener()
    async def on_raw_message_edit(self, payload: RawMessageUpdateEvent):
        mod_data = save.get_module_data(payload.guild_id, MODULE_NAME)
        if payload.channel_id in mod_data["excludeChannels"]: return
        cached = payload.cached_message

        target = self.bot.get_channel(mod_data["logChannel"])
        if target is None: return

        data = payload.data

        fields = [("Channel", f"<#{payload.channel_id}>"),
                  ("Author", f"<@{data['author']['id']}>" if "author" in data.keys() else "Not Found"),
                  ("Link", f"https://discord.com/channels/{payload.guild_id}/{payload.channel_id}/{data['id']}")]
        
        if cached is not None: # exclusion clause for spurious edit events when possible
            if "content" in data.keys() and cached.content == data["content"]:
                if "attachments" in data.keys() and cached.attachments == data["attachments"] and len(data["attachments"]) >= len(cached.attachments):
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
        mod_data = save.get_module_data(payload.guild_id, MODULE_NAME)
        if payload.channel_id in mod_data["excludeChannels"]: return

        target = self.bot.get_channel(mod_data["logChannel"])
        if target is None: return

        fields = [("Channel", f"<#{payload.channel_id}>")]
        embed_message = ""

        cached = payload.cached_message
        if cached is not None:
            fields.append(("Author", f"<@{cached.author.id}> - {cached.author.name}"))
            if len(cached.content) > 0:
                embed_message = cached.content
            if len(cached.attachments) > 0:
                fields.append(("Attachments", "\r\n".join([a.url for a in cached.attachments])[:1024], False))
        else:
            embed_message = "Message was not found in cache!"
            fields.append(("Message ID", f"{payload.message_id}"))
        await embeds.embed_message(target, title="Message Deleted", fields=fields, message=embed_message)
