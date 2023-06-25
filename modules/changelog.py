import discord
from discord.ext import commands
from discord.ext.commands import Context
from discord import Message

from components import auth, embeds
import save

MODULE_NAME = "changelog"

async def setup(bot: commands.Bot):
    save.addModuleTemplate(MODULE_NAME, {"logChannel": 0, "excludeChannels": []})
    await bot.add_cog(changelogCog(bot))

class changelogCog(commands.Cog, name="Changelog", description="Tracks message edits and deletes"):
    """Tracks message edits and deletes. NOTE: can only show message contents from cached messages ie. fewer than 10k messages ago"""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    def cog_unload(self):
        pass

    @commands.command(help="Set this channel to track message edits and deletes")
    @commands.check(auth.isAdmin)
    async def setChangelogChannel(self, context : Context, channel: discord.TextChannel):
        save.getModuleData(context.guild.id, MODULE_NAME)["logChannel"] = channel.id
        save.getModuleData(context.guild.id, MODULE_NAME)["excludeChannels"].append(channel.id)
        save.save()
        await context.message.delete()

    @commands.command(help="Exclude a channel from this server's changelog")
    @commands.check(auth.isAdmin)
    async def excludeChannel(self, context : Context, channel : discord.TextChannel):
        excludes = save.getModuleData(context.guild.id, MODULE_NAME)["excludeChannels"]
        if channel.id in excludes:
            await embeds.embedReply(context, message="This channel is already excluded!")
            return
        excludes.append(channel.id)
        save.save()
        await context.message.delete()

    @commands.command(help="Remove a changelog channel exclusion")
    @commands.check(auth.isAdmin)
    async def includeChannel(self, context : Context, channel : discord.TextChannel):
        save.getModuleData(context.guild.id, MODULE_NAME)["excludeChannels"].remove(channel.id)
        save.save()
        await context.message.delete()

    @commands.command(help="List excluded channels")
    @commands.check(auth.isAdmin)
    async def listExcludes(self, context : Context):
        channels = save.getModuleData(context.guild.id, MODULE_NAME)["excludeChannels"]
        await embeds.embedReply(context, title="Excluded Channels", message='\r\n'.join([f"<#{x}> ({x})" for x in channels]))

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload: discord.RawMessageUpdateEvent):
        modData = save.getModuleData(payload.guild_id, MODULE_NAME)
        if payload.channel_id in modData["excludeChannels"]: return
        cached = payload.cached_message

        target = self.bot.get_channel(modData["logChannel"])
        if target is None: return

        data = payload.data

        fields = [("Channel", f"<#{payload.channel_id}>"),
                  ("Author", f"<@{data['author']['id']}>" if "author" in data.keys() else "Not Found"),
                  ("Link", f"https://discord.com/channels/{payload.guild_id}/{payload.channel_id}/{data['id']}")]
        
        embedMessage = "Message was not found in cache!"
        if payload.cached_message is not None:
            embedMessage = ""
            if len(cached.content) > 0:
                fields.append(("Old Content", cached.content))
        if "content" in payload.data.keys():
            fields.append(("New Content", f"{data['content']}"))
        if payload.cached_message and len(cached.attachments) > 0:
            fields.append(("Old Attachments", "\r\n".join([a.url for a in cached.attachments]), False))
        if "attachments" in payload.data.keys() and len(payload.data["attachments"]):
            fields.append(("New Attachments", "\r\n".join([a["url"] for a in payload.data["attachments"]]), False))
        await embeds.embedMessage(target, title="Message Edited", fields=fields, message=embedMessage)
        
    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload : discord.RawMessageDeleteEvent):
        modData = save.getModuleData(payload.guild_id, MODULE_NAME)
        if payload.channel_id in modData["excludeChannels"]: return

        target = self.bot.get_channel(modData["logChannel"])
        if target is None: return

        fields = [("Channel", f"<#{payload.channel_id}>")]
        embedMessage = ""

        cached = payload.cached_message
        if cached is not None:
            fields.append(("Author", f"<@{cached.author.id}>"))
            if len(cached.content) > 0:
                fields.append(("Content", cached.content, False))
            if len(cached.attachments) > 0:
                fields.append(("Attachments", "\r\n".join([a.url for a in cached.attachments]), False))
        else:
            embedMessage = "Message was not found in cache!"
            fields.append(("Message ID", f"{payload.message_id}"))
        await embeds.embedMessage(target, title="Message Deleted", fields=fields, message=embedMessage)
