import discord
from discord import app_commands
from discord.ext import commands

from ballsdex.core.models import Ball
from ballsdex.core.utils.transformers import BallTransform

SUGGESTION_CHANNEL_ID = 1292957072962355363

class SuggestAbility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command()
    @app_commands.checks.cooldown(1, 20)
    async def suggest_ability(
        self,
        interaction: discord.Interaction,
        monster: app_commands.Transform[Ball, BallTransform],
        name: str,
        description: str
    ):
        """
        Suggest a new ability for a monster.

        Parameters
        ----------
        monster: Ball
            The monster for this ability
        name: str
            The name of the suggested ability
        description: str
            A description of what the ability does
        """
        await interaction.response.defer(ephemeral=True)

        embed = discord.Embed(title="New Ability Suggestion", color=discord.Color.blurple())
        embed.add_field(name="Suggested by", value=f"{interaction.user.display_name} ({interaction.user.name} - {interaction.user.id})", inline=False)
        embed.add_field(name="Monster", value=monster.country, inline=False)
        embed.add_field(name="Ability Name", value=name, inline=False)
        embed.add_field(name="Description", value=description, inline=False)

        channel = self.bot.get_channel(SUGGESTION_CHANNEL_ID)
        if channel:
            await channel.send(embed=embed)
            await interaction.followup.send("Your ability suggestion has been submitted!", ephemeral=True)
        else:
            await interaction.followup.send("There was an error submitting your suggestion. Please try again later.", ephemeral=True)