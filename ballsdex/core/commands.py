<<<<<<< HEAD
import logging
import time
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands
from tortoise import Tortoise

log = logging.getLogger("ballsdex.core.commands")

if TYPE_CHECKING:
    from .bot import BallsDexBot


class Core(commands.Cog):
    """
    Core commands of BallsDexBot
    """

    def __init__(self, bot: "BallsDexBot"):
        self.bot = bot

    @app_commands.command(name="ping")
    async def ping(self, interaction: discord.Interaction):
        """Ping!"""
        await interaction.response.send_message("Pong")

    @app_commands.command(name="reloadtree")
    @commands.is_owner()
    async def reloadtree(self, interaction: discord.Interaction):
        """Sync the application commands with Discord"""
        await self.bot.tree.sync()
        await interaction.response.send_message("Application commands tree reloaded.")

    @app_commands.command(name="reload")
    @commands.is_owner()
    async def reload(self, interaction: discord.Interaction, package: str):
        """Reload an extension"""
        package = "ballsdex.packages." + package
        try:
            try:
                await self.bot.reload_extension(package)
            except commands.ExtensionNotLoaded:
                await self.bot.load_extension(package)
        except commands.ExtensionNotFound:
            await interaction.response.send_message("Extension not found")
        except Exception:
            await interaction.response.send_message("Failed to reload extension.")
            log.error(f"Failed to reload extension {package}", exc_info=True)
        else:
            await interaction.response.send_message("Extension reloaded.")

    @app_commands.command(name="reloadcache")
    @commands.is_owner()
    async def reloadcache(self, interaction: discord.Interaction):
        """
        Reload the cache of database models.

        This is needed each time the database is updated, otherwise changes won't reflect until
        next start.
        """
        await self.bot.load_cache()
        await interaction.response.send_message("✅ Cache reloaded")

    @app_commands.command(name="analyzedb")
    @commands.is_owner()
    async def analyzedb(self, interaction: discord.Interaction):
        """
        Analyze the database. This refreshes the counts displayed by the `/about` command.
        """
        connection = Tortoise.get_connection("default")
        t1 = time.time()
        await connection.execute_query("ANALYZE")
        t2 = time.time()
        await interaction.response.send_message(f"Analyzed database in {round((t2 - t1) * 1000)}ms.")
=======
import logging
import time
from typing import TYPE_CHECKING

from discord.ext import commands
from tortoise import Tortoise

log = logging.getLogger("ballsdex.core.commands")

if TYPE_CHECKING:
    from .bot import BallsDexBot


class Core(commands.Cog):
    """
    Core commands of BallsDex bot
    """

    def __init__(self, bot: "BallsDexBot"):
        self.bot = bot

    @commands.command()
    async def ping(self, ctx: commands.Context):
        """
        Ping!
        """
        await ctx.send("Pong")

    @commands.command()
    @commands.is_owner()
    async def reloadtree(self, ctx: commands.Context):
        """
        Sync the application commands with Discord
        """
        await self.bot.tree.sync()
        await ctx.send("Application commands tree reloaded.")

    @commands.command()
    @commands.is_owner()
    async def reload(self, ctx: commands.Context, package: str):
        """
        Reload an extension
        """
        package = "ballsdex.packages." + package
        try:
            try:
                await self.bot.reload_extension(package)
            except commands.ExtensionNotLoaded:
                await self.bot.load_extension(package)
        except commands.ExtensionNotFound:
            await ctx.send("Extension not found.")
        except Exception:
            await ctx.send("Failed to reload extension.")
            log.error(f"Failed to reload extension {package}", exc_info=True)
        else:
            await ctx.send("Extension reloaded.")

    @commands.command()
    @commands.is_owner()
    async def reloadcache(self, ctx: commands.Context):
        """
        Reload the cache of database models.

        This is needed each time the database is updated, otherwise changes won't reflect until
        next start.
        """
        await self.bot.load_cache()
        await ctx.message.add_reaction("✅")

    @commands.command()
    @commands.is_owner()
    async def analyzedb(self, ctx: commands.Context):
        """
        Analyze the database. This refreshes the counts displayed by the `/about` command.
        """
        connection = Tortoise.get_connection("default")
        t1 = time.time()
        await connection.execute_query("ANALYZE")
        t2 = time.time()
        await ctx.send(f"Analyzed database in {round((t2 - t1) * 1000)}ms.")
>>>>>>> bd/master
