import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import base64

class Credits(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def fetch_credits(self):
        url = "https://raw.githubusercontent.com/wubbubunga-tll/credits_Ddx/refs/heads/main/credits.txt"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    content = await response.text()
                    decoded_content = base64.b64decode(content).decode('utf-8')
                    return decoded_content
                else:
                    return None

    @app_commands.command()
    @app_commands.checks.cooldown(1, 10) 
    async def credits(self, interaction: discord.Interaction):
        """Display the credits for FanmadeDex"""
        try:
            content = await self.fetch_credits()
            if content is None:
                content = "Credits failed to load, please contact support if this error continues"
        except Exception as e:
            content = f"An error occurred while fetching credits: {str(e)}"

        embed = discord.Embed(
            title="",
            description=content,
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Credits(bot))