import discord
from discord.ext import commands, tasks
from discord.ext.commands import Context
import time

from components import auth, embeds, emojiUtil
import save

from pytimeparse.timeparse import timeparse

MODULE_NAME = "moderation"

async def setup(bot: commands.Bot):
    save.addModuleTemplate(MODULE_NAME, {"mutes": {}, "muteRoles": {}, "defaultMute": ""})
    await bot.add_cog(ModerationCog(bot))

async def teardown(bot: commands.Bot):
    await bot.remove_cog("Moderation")

class ModerationCog(commands.Cog, name="Moderation", description="Commands used for server moderation"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.checkMutes.start()

    def cog_unload(self):
        self.checkMutes.stop()
    
    @commands.command(help="DM a member a warning")
    @commands.check(auth.isAdmin)
    async def warn(self, context: Context, target: discord.Member, *, reason=""):       
        await embeds.embedMessage(target, title=f"You have been warned in {context.guild.name}:", message=reason)

    @commands.command(help="Mute a member at a given level for a given time period. Member is informed via DM")
    @commands.check(auth.isAdmin)
    async def muteLevel(self, context: Context, target: discord.Member, duration: str, level : str, *, reason):
        ectx = embeds.EmbedContext(context)

        if level == -1: unmute_time = -1
        else: unmute_time = int(time.time() + timeparse(duration))

        modData = save.getModuleData(context.guild.id, MODULE_NAME)

        if level not in modData["muteRoles"].keys():
            await ectx.embedReply(message="Mute level not found! Check in listMuteLevels!")
            return
        
        muterole_id : int = modData["muteRoles"][level]
        
        muterole = context.guild.get_role(muterole_id)
        if not muterole:
            await ectx.embedReply(message=f"Mute role id {muterole_id} not found! Was it deleted?")
            return
        
        await target.add_roles(muterole)
        modData["mutes"][str(target.id)] = [level, unmute_time]
        save.save()
        await ectx.embedReply(f"User muted until <t:{unmute_time}>")
        await embeds.embedMessage(target, title=f"You have been muted at level {level} in {context.guild.name}", \
                                  message=f"Lasts until <t:{unmute_time}>\r\nReason: {reason}")

    @commands.command(help="Mute a member at the default level for a given time period")
    @commands.check(auth.isAdmin)
    async def mute(self, context: Context, target: discord.Member, duration : str, *, reason):
        level = save.getModuleData(context.guild.id, MODULE_NAME)["defaultMute"]
        await self.muteLevel(context, target, duration, level, reason=reason)
    
    @commands.command(help="Unmute a muted member")
    @commands.check(auth.isAdmin)
    async def unmute(self, context: Context, target: discord.Member):
        ectx = embeds.EmbedContext(context)
        mutes : dict[list] = save.getModuleData(context.guild.id, MODULE_NAME)["mutes"]
        if target.id not in mutes:
            await ectx.embedReply(f"{target.name} isn't muted!")
            return
        
        exitmute = mutes.pop(target.id)
        save.save()
        await ectx.embedReply(f"{target.name} was unmuted from level {exitmute[0]} lasting until <t:{exitmute[1]}>")

    @commands.command(help="Lists active mutes")
    @commands.check(auth.isAdmin)
    async def listMutes(self, context: Context):
        mutes : dict[list] = save.getModuleData(context.guild.id, MODULE_NAME)["mutes"]
        fields = []
        for muted, muteargs in mutes.items():
            fields.append(f"{self.bot.get_user(muted).name} ({muted})", f"Level {muteargs[0]} until <t:{muteargs[1]}>")
        await embeds.embedReply(context, title="Muted members:", fields=fields)
    
    @commands.command(help="Add a mute level")
    @commands.check(auth.isAdmin)
    async def addMuteLevel(self, context: Context, level : str, role: discord.Role):
        ectx = embeds.EmbedContext(context)
        levels : dict = save.getModuleData(context.guild.id, MODULE_NAME)["muteRoles"]
        if level in levels.keys():
            await ectx.embedReply(f"Mute level {level} already exists!")
            return
        
        levels[level] = role.id
        save.save()
        await ectx.embedReply(f"Added mute level {level} on role {role.name}")
        
    @commands.command(help="Remove a mute level")
    @commands.check(auth.isAdmin)
    async def removeMuteLevel(self, context: Context, level : str):
        ectx = embeds.EmbedContext(context)
        levels : dict = save.getModuleData(context.guild.id, MODULE_NAME)["muteRoles"]
        if level not in levels.keys():
            await ectx.embedReply(f"Mute level {level} doesn't exist!")
            return

        exitlevel = levels[level].pop()
        save.save()
        await ectx.embedReply(f"Removed mute level {level} on role {context.guild.get_role(exitlevel[1]).name}")

    @commands.command(help="Set the default mute level for ;mute")
    @commands.check(auth.isAdmin)
    async def setDefaultMuteLevel(self, context: Context, level : str):
        ectx = embeds.EmbedContext(context)
        modData = save.getModuleData(context.guild.id, MODULE_NAME)

        if level not in modData["muteRoles"].keys():
            await ectx.embedReply(f"Mute level not found! Check in listMuteLevels!")
            return
        
        modData["defaultMute"] = level
        await ectx.embedReply(f"Set default mute level to {level}")

    @commands.command(help="Show a list of mute levels")
    @commands.check(auth.isAdmin)
    async def listMuteLevels(self, context: Context):
        modData = save.getModuleData(context.guild.id, MODULE_NAME)

        levelfields = []
        for level, id in modData["muteRoles"].items():
            levelfields.append((level[0], context.guild.get_role(id).name, True))
        
        levelfields.append(("Default Role", modData["defaultMute"], False))

        await embeds.embedReply(context, title="Mute levels:", fields=levelfields)

    @commands.command(help="Repost a message to a given channel in this server")
    @commands.check(auth.isAdmin)
    async def relay(self, context : Context, channel: discord.TextChannel, *, message):
        guildChannel = context.guild.get_channel(channel.id)
        if guildChannel is None:
            await embeds.embedReply(context, message="Channel not found in this guild!")
            return
        await guildChannel.send(message)

    @commands.command(help="Edit a message posted by Hornet")
    @commands.check(auth.isAdmin)
    async def editmsg(self, context : Context, message : discord.Message, *, content):
        if message.author != self.bot.user:
            await embeds.embedReply(context, message="Cannot edit a message I did not send!")
            return
        await message.edit(content=content)


    @commands.command(help="Add a reaction to a message")
    @commands.check(auth.isAdmin)
    async def react(self, context : Context, message: discord.Message, emoji: str):
        emojiRef = await emojiUtil.toEmoji(context, emoji)
        await message.add_reaction(emojiRef)

    @commands.command(help="List users that reacted with given emoji. Must be emoji from this server!")
    @commands.check(auth.isAdmin)
    async def listreactions(self, context : Context, message: discord.Message, emoji: str):
        emoji = await emojiUtil.toEmoji(context, emoji)
        if emoji not in [r.emoji for r in message.reactions]:
            await embeds.embedReply(context, message="Reaction not found!")
            return
        index = [r.emoji for r in message.reactions].index(emoji)
        reaction = message.reactions[index]

        desc = "\r\n".join([user.name async for user in reaction.users()])
        
        await embeds.embedReply(context, title=f"Reactions on {emojiUtil.toString(emoji)} to {message.jump_url}", message=desc)

    @tasks.loop(minutes=1)
    async def checkMutes(self):
        for guild_id in save.getGuildIds():
            guild = self.bot.get_guild(int(guild_id))
            if guild is None: continue
            roles = save.getModuleData(guild_id, MODULE_NAME)["muteRoles"]
            mutes : dict[list] = save.getModuleData(guild.id, MODULE_NAME)["mutes"]

            dictItems = list(mutes.items()) # copy dict items to allow mutation during iteration
            for user, mute in dictItems:
                if int(mute[1]) < int(time.time()) and int(mute[1]) != -1:
                    member = guild.get_member(int(user))
                    role = guild.get_role(roles[mute[0]])
                    if member is not None: await member.remove_roles(role, reason="Timed unmute")
                    exitmute = mutes.pop(user)
                    print(exitmute)
                    save.save()