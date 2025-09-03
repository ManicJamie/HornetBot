import json
from discord import Member, Role
from discord.ext.commands import Cog, command
from typing import TYPE_CHECKING, TypedDict
if TYPE_CHECKING:
    from Hornet import HornetBot, HornetContext

from speedruncompy import Game, GetUserLeaderboard, Verified

from components import auth, src
import save

MODULE_NAME = __name__.split(".")[-1]

class SRRolesModuleDict(TypedDict):
    roles: dict[str, list[str]]
    """role_id : list[game_id]"""


MODULE_TEMPLATE = {
    "roles": {}
}

async def setup(bot: 'HornetBot'):
    save.add_module_template(MODULE_NAME, MODULE_TEMPLATE)
    await bot.add_cog(SrRolesCog(bot))

async def teardown(bot: 'HornetBot'):
    await bot.remove_cog("SrcRoles")

class SrRolesCog(Cog, name="SrcRoles", description="Commands to verify runners from their SRC profile"):
    def __init__(self, bot: 'HornetBot'):
        self.bot = bot
        self._log = bot._log.getChild("SrcRoles")

    @command(help="Grants the speedrunner role to verified runners given your SRC username",
             aliases=["getsrrole", "grantsrole"])
    async def grantsrrole(self, context: 'HornetContext', src_username: str):
        if context.guild is None or not isinstance(context.author, Member): return
        guild_id = str(context.guild.id)
        
        try:
            user, src_discord = await src.get_src_user_discord(src_username)
        except src.UserNotFound:
            return await context.embed_reply(f"Could not find Speedrun.com user {src_username}")
        except src.NoDiscordUsername as e:
            return await context.embed_reply(f"No discord username found for {e.args[0]}")
        
        roles: dict[str, list[str]] = save.get_module_data(guild_id, MODULE_NAME)["roles"]

        discord_name = context.author.name
        if src_discord.lower() != discord_name.lower():
            return await context.embed_reply(f"Your Discord username doesn't match SRC! Update the Discord username on your SRC profile to `{discord_name}` (currently `{src_discord}`)")

        user_leaderboard = await GetUserLeaderboard(user.id, _api=src.CLIENT).perform_async()
        user_verified_games = set()
        for run in user_leaderboard.runs:
            if run.verified == Verified.VERIFIED:
                user_verified_games.add(run.gameId)
        
        assign_roles: list[Role] = []
        for role_id, games in roles.items():
            role = context.guild.get_role(int(role_id))
            if role is None:
                self._log.warning(f"Role {role_id} in guild {guild_id} not found!")
                continue
            
            for g in games:
                if g in user_verified_games:
                    assign_roles.append(role)
        
        
        if len(assign_roles) == 0:
            return await context.embed_reply("You need to have a verified run on Speedrun.com!")
        
        await context.author.add_roles(*assign_roles, reason="Grant SR Roles")
        await context.embed_reply(f"Runner {src_username} given roles {', '.join(r.name for r in assign_roles)}")

    @command(help="Sets up games for runner role. Supply game names in quotes.")
    @auth.check_admin
    async def setupsrrole(self, context: 'HornetContext', role: Role, *game_names: str):
        if context.guild is None or not isinstance(context.author, Member): return
        games: list[Game] = []
        not_found = []
        for game_name in game_names:
            try:
                games.append(await src.find_game(game_name))
            except src.NotFoundException:
                not_found.append(game_name)
        
        roles = save.get_module_data(context.guild.id, MODULE_NAME)["roles"]
        roles[str(role.id)] = [game.id for game in games]
        save.save()

        found_game_names: list[str] = [g.name for g in games]
        await context.embed_reply(message=("Verified:\r\n" + '\r\n'.join(found_game_names)
                                           + (f"\r\n\r\nCould not find: \r\n {' '.join(not_found)}" if len(not_found) != 0 else '')))

    @command(help="Get the list of games the speedrunner role checks for runs with")
    async def listsrgames(self, context: 'HornetContext'):
        if context.guild is None: return
        roles = save.get_module_data(context.guild.id, MODULE_NAME)["roles"]
        await context.embed_reply(title="Verified Games:", message=json.dumps(roles))
