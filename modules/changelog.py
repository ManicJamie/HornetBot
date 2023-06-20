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
        save.getModuleData(context.guild.id, MODULE_NAME)["excludeChannels"].append(channel.id)
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
    async def on_message_edit(self, before : Message, after : Message):
        modData = save.getModuleData(before.guild.id, MODULE_NAME)
        if before.channel.id in modData["excludeChannels"]: return

        target = self.bot.get_channel(modData["logChannel"])
        if target is None: return

        fields = [("Channel", f"<#{before.channel.id}>"),
                  ("Author", f"<@{before.author.id}>"),
                  ("Old Content", f"{before.content}"),
                  ("New Content", f"{after.content}"),
                  ("Link", f"https://discord.com/channels/{after.guild.id}/{after.channel.id}/{after.id}")]
        await embeds.embedMessage(target, title="Message Edited", fields=fields)
        
    @commands.Cog.listener()
    async def on_message_delete(self, message : Message):
        modData = save.getModuleData(message.guild.id, MODULE_NAME)
        if message.channel.id in modData["excludeChannels"]: return

        target = self.bot.get_channel(modData["logChannel"])
        if target is None: return

        fields = [("Channel", f"<#{message.channel.id}>"),
                  ("Author", f"<@{message.author.id}>")]
        if len(message.content) > 0:
            fields.append(("Content", message.content))
        if len(message.attachments) > 0:
            fields.append(("Attachments", "\r\n".join([a.url for a in message.attachments])))
        await embeds.embedMessage(target, title="Message Deleted", fields=fields)
