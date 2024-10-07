import discord
from discord import app_commands
from discord.ext import commands
from tortoise.functions import Count

from ballsdex.core.models import Player, BallInstance
from ballsdex.core.utils.paginator import FieldPageSource, Pages
from ballsdex.settings import settings

class Leaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command()
    @app_commands.checks.cooldown(1, 30)
    async def leaderboard(
        self,
        interaction: discord.Interaction,
        shiny_only: bool = False,
        ascending: bool = False
    ):
        """
        Display the FanmadeDex leaderboard of players with the most monsters.

        Parameters
        ----------
        shiny_only: bool
            If True, only count shiny monsters
        ascending: bool
            If True, sort from lowest to highest
        """
        await interaction.response.defer(thinking=True)

        query = Player.all().annotate(monster_count=Count('balls'))

        if shiny_only:
            query = query.filter(balls__shiny=True)

        query = query.order_by(f"{'' if ascending else '-'}monster_count").limit(100)

        players = await query

        if not players:
            await interaction.followup.send("No players found with monsters.")
            return

        entries = []
        for index, player in enumerate(players, start=1):
            user = await self.bot.fetch_user(int(player.discord_id))
            display_name = user.display_name if user else f"Unknown User ({player.discord_id})"
            monster_text = f"{player.monster_count} monster" + ("s" if player.monster_count != 1 else "")
            entries.append((
                f"{index}. {display_name}",
                monster_text
            ))

        source = FieldPageSource(entries, per_page=10)
        source.embed.title = "FanmadeDex Leaderboard"
        if shiny_only:
            source.embed.title += " (Shiny Only)"
        source.embed.color = discord.Color.blurple()

        pages = Pages(source=source, interaction=interaction, compact=True)
        await pages.start()