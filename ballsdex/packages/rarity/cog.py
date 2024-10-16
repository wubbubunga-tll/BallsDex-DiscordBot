import discord
from discord import app_commands
from discord.ext import commands
from ballsdex.core.models import Ball, balls
from ballsdex.core.utils.paginator import FieldPageSource, Pages
from ballsdex.core.utils.transformers import BallTransform
from ballsdex.settings import settings

def format_rarity(rarity: float) -> str:
    if rarity >= 1:
        return f"{rarity:.1f}%"
    elif rarity >= 0.1:
        return f"{rarity:.2f}%"
    else:
        return f"{rarity:.{max(3, -int(rarity.as_integer_ratio()[1].bit_length() / 3.32) + 1)}f}%"

class Rarity(commands.GroupCog, group_name="rarity"):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(description="View the rarity list of the dex - created by Venus")
    @app_commands.describe(
        descending="If true, list goes from common to rare. If false, rare to common.",
        monsters_per_page="Number of monsters to show per page."
    )
    @app_commands.checks.cooldown(1, 10)
    async def list(
        self, 
        interaction: discord.Interaction, 
        descending: bool = False, 
        monsters_per_page: app_commands.Range[int, 5, 15] = 6
    ):
        await interaction.response.defer(thinking=True)

        sorted_balls = sorted(
            [ball for ball in balls.values() if ball.enabled],
            key=lambda x: (x.rarity, x.country.lower()),
            reverse=not descending
        )
        
        entries = []
        for ball in sorted_balls:
            emoji = self.bot.get_emoji(ball.emoji_id)
            emoji_str = str(emoji) if emoji else ""
            entries.append((
                f"{emoji_str} {ball.country}",
                f"Rarity: {format_rarity(ball.rarity)}"
            ))

        source = FieldPageSource(entries, per_page=monsters_per_page)
        source.embed.title = f"{settings.bot_name} Rarity List"
        source.embed.description = "Sorted from most common to rarest" if descending else "Sorted from rarest to most common"
        source.embed.color = discord.Color.blurple()
        pages = Pages(source=source, interaction=interaction, compact=True)
        await pages.start()

    @app_commands.command(description="View the rarity of a specific monster - created by Venus")
    @app_commands.describe(
        monster="The monster to check the rarity of",
        shiny="Whether to show the rarity for the shiny version"
    )
    @app_commands.checks.cooldown(1, 5)
    async def search(
        self,
        interaction: discord.Interaction,
        monster: app_commands.Transform[Ball, BallTransform],
        shiny: bool = False,
    ):
        if not monster.enabled:
            await interaction.response.send_message(
                f"The monster {monster.country} is currently disabled.",
                ephemeral=True
            )
            return

        rarity = monster.rarity
        
        if shiny:
            shiny_chance = 1 / 2048
            rarity *= shiny_chance
        
        ball_name = f"Shiny {monster.country}" if shiny else monster.country
        formatted_rarity = format_rarity(rarity)
        
        emoji = self.bot.get_emoji(monster.emoji_id)
        emoji_str = str(emoji) if emoji else ""

        await interaction.response.send_message(
            f"{emoji_str} **{ball_name}**'s rarity: {formatted_rarity}",
            ephemeral=True,
        )