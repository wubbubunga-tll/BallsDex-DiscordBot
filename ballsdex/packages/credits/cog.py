import discord
from discord.ext import commands
from discord import app_commands

class Credits(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command()
    @app_commands.checks.cooldown(1, 10) 
    async def credits(self, interaction: discord.Interaction):
        """Display the credits for FanmadeDex"""
        try:
            channel = self.bot.get_channel(1263510238603116574)
            message = await channel.fetch_message(1293965631137382410)
            content = message.content
        except (discord.NotFound, discord.Forbidden, AttributeError):
            content = """Credits failed to load, please contact support if this error continues"""

        embed = discord.Embed(
            title="",
            description=content,
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Credits(bot))