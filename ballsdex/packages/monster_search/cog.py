
from typing import TYPE_CHECKING, Optional, Literal
import discord
from discord import app_commands
from discord.ext import commands
from ballsdex.core.models import BallInstance, Player
from ballsdex.settings import settings

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot

class MonsterSearch(commands.Cog):
    def __init__(self, bot: "BallsDexBot"):
        self.bot = bot

    @app_commands.command()
    @app_commands.describe(
        rarity="Search for the highest or lowest rarity monster",
        hp="Search for the monster with the highest or lowest HP",
        attack="Search for the monster with the highest or lowest attack",
        shiny="Search for shiny monsters only",
        rank="Rank of the monster to search for (default: 1)"
    )
    async def search(
        self,
        interaction: discord.Interaction,
        rarity: Optional[Literal["Highest", "Lowest"]] = None,
        hp: Optional[Literal["Highest", "Lowest"]] = None,
        attack: Optional[Literal["Highest", "Lowest"]] = None,
        shiny: Optional[bool] = None,
        rank: int = 1
    ):
        """
        Search for monsters based on various criteria.
        At least one option needs to be chosen.
        """
        if not any([rarity, hp, attack, shiny is not None]):
            await interaction.response.send_message("You need to choose at least one search criteria.", ephemeral=True)
            return

        await interaction.response.defer(thinking=True)

        try:
            player = await Player.get(discord_id=interaction.user.id)
        except Exception:
            await interaction.followup.send("You don't have any monsters yet!", ephemeral=True)
            return

        query = BallInstance.filter(player=player)

        if shiny is not None:
            query = query.filter(shiny=shiny)

        order_by = []
        if rarity:
            order_by.append(f"{'-' if rarity == 'Highest' else ''}ball__rarity")
        if hp:
            order_by.append(f"{'-' if hp == 'Highest' else ''}health_bonus")
        if attack:
            order_by.append(f"{'-' if attack == 'Highest' else ''}attack_bonus")

        if order_by:
            query = query.order_by(*order_by)

        monsters = await query.prefetch_related('ball')

        if not monsters:
            await interaction.followup.send("No monsters found with the specified criteria.", ephemeral=True)
            return

        try:
            selected_monster = monsters[rank - 1]
        except IndexError:
            await interaction.followup.send(f"No monster found at rank {rank} with the specified criteria.", ephemeral=True)
            return

        content, file = await selected_monster.prepare_for_message(interaction)
        

        await interaction.followup.send(content=content, file=file)

async def setup(bot):
    for attempt in range(3):
        monsters_group = bot.tree.get_command("monsters")
        if monsters_group and isinstance(monsters_group, app_commands.Group):
            monsters_group.add_command(MonsterSearch(bot).search)
            break
        elif attempt < 2:  
            await asyncio.sleep(1)
    else:
        bot.tree.add_command(MonsterSearch(bot).search)