from typing import Mapping, Optional, List
from discord.ext import commands
from discord.ext.commands.context import Context
import discord
import discord.embeds as e

from components import embeds

class HornetHelpCommand(commands.HelpCommand):
    def __init__(self, **options):
        super().__init__(**options)

    def checkCog(self, cog: commands.Cog):
        cog.cog_check(self.context)

    async def send_bot_help(self, mapping: Mapping[Optional[commands.Cog], List[commands.Command]]):
        response = ""
        fields = []

        cmds = mapping[None]
        for cmd in cmds:
            perms = True
            for check in cmd.checks:
                if not await check(self.context): 
                    perms = False
                    break
            if perms:
                response += f"{cmd.qualified_name}    {cmd.description}\r\n"
        response += "\r\n"
                
        for cog in mapping:
            if cog == None: continue
            cmds = mapping[cog]

            strs = []
            for cmd in cmds:
                perms = True
                for check in cmd.checks:
                    if not await check(self.context): 
                        perms = False
                        break
                if perms:
                    strs.append(f"{cmd.qualified_name}    {cmd.description}")
            if len(strs) > 0:
                response += f"**{cog.qualified_name}:**\r\n" +"\r\n".join(strs) + "\r\n\r\n"
            
        await self.get_destination().send(embed=e.Embed(title="Help", fields=[]))
        await embeds.embedMessage(self.get_destination(), message=response, title="Help")