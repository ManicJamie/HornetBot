from discord import Role
from discord.ext.commands import Bot, Cog, Context, command
from srcomapi.datatypes import Game
import logging

from components import auth, embeds, src
import save

MODULE_NAME = __name__.split(".")[-1]

async def setup(bot: Bot):
    save.add_module_template(MODULE_NAME, {"games" : [], "srrole": 0 })
    await bot.add_cog(SrRolesCog(bot))

async def teardown(bot: Bot):
    await bot.remove_cog("SrcRoles")

class SrRolesCog(Cog, name="SrcRoles", description="Commands to verify runners from their SRC profile"):
    def __init__(self, bot):
        self.bot = bot

    @command(help="Grants the speedrunner role to verified runners given your SRC username",
             aliases=["getsrrole", "grantsrole"])
    async def grantsrrole(self, context: Context, src_username: str):
        ectx = embeds.EmbedContext(context)
        guild_id = str(context.guild.id)

        srrole_id = save.get_module_data(guild_id, MODULE_NAME)["srrole"]
        srrole = context.guild.get_role(srrole_id)
        if srrole is None:
            await ectx.embed_reply("SRRoles module is not set up! Ask an admin to use ;setsrrole")
            return

        games = [src.find_game(game) for game in save.get_module_data(guild_id, MODULE_NAME)["games"]]
        try:
            user = src.find_user(src_username)
        except src.NotFoundException:
            await ectx.embed_reply(f"No SRC user with name {src_username}")
            return

        try:
            dc = src.get_discord(user)
        except src.NotFoundException:
            await ectx.embed_reply(f"Please link your discord in your Speedrun.com profile")
            return

        discord_name = context.author.name
        if context.author.discriminator != "0":
            discord_name += f"#{context.author.discriminator}"
        if dc.lower() != discord_name.lower():
            logging.warn(f"SRC name: {dc} != Discord name: {discord_name}")
            await ectx.embed_reply(f"Your Discord username doesn't match SRC! Update the Discord username on your SRC profile to `{discord_name}` (currently `{dc}`)")
            return

        runs = src.get_runs_from_user(games, user)

        if len(runs) > 0:
            if srrole in context.author.roles:
                await ectx.embed_reply("You are already verified")
            else:
                await context.author.add_roles(srrole)
                await ectx.embed_reply(f"Runner {src_username} verified")
        else:
            await ectx.embed_reply("You must have a verified run on speedrun.com!")

    @command(help="Set the role given by ;grantsrrole")
    @auth.check_admin
    async def setsrrole(self, context: Context, role: Role):
        save.get_module_data(context.guild.id, MODULE_NAME)["srrole"] = role.id
        save.save()
        await embeds.embed_reply(context, f"Speedrun role set to {role.name}")

    @command(help="Sets up games for runner role. Supply game names in quotes.")
    @auth.check_admin
    async def setsrgames(self, context: Context, *game_names: str):
        games : list[Game] = []
        not_found = []
        for game_name in game_names:
            try:
                games.append(src.find_game(game_name))
            except src.NotFoundException:
                not_found.append(game_name)

        save.get_module_data(context.guild.id, MODULE_NAME)["games"] = [game.name for game in games]
        save.save()

        games = [g.name for g in games]
        await embeds.embed_reply(
            context,
            message=("Verified:\r\n" + '\r\n'.join(games) + \
                     (f"\r\n\r\nCould not find: \r\n {' '.join(not_found)}" if len(not_found) != 0 else ''))
        )

    @command(help="Get the list of games the speedrunner role checks for runs with")
    async def listsrgames(self, context: Context):
        ectx = embeds.EmbedContext(context)
        games = save.get_module_data(context.guild.id, "srroles")["games"]
        await ectx.embed_reply(title= "Verified Games:", message="\r\n".join(games))
