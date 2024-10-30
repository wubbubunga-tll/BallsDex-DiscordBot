import logging
from typing import TYPE_CHECKING, Optional, cast

import discord
from discord import app_commands 
from discord.ext import commands

from tortoise.exceptions import DoesNotExist

from ballsdex.core.models import GuildConfig
from ballsdex.packages.countryballs.spawn import SpawnManager

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot

    

log = logging.getLogger("ballsdex.packages.countryballs")


class CountryBallsSpawner(commands.Cog):
    def __init__(self, bot: "BallsDexBot"):
        self.spawn_manager = SpawnManager()
        self.bot = bot

    async def load_cache(self):
        i = 0
        async for config in GuildConfig.all():
            if not config.enabled:
                continue
            if not config.spawn_channel:
                continue
            self.spawn_manager.cache[config.guild_id] = config.spawn_channel
            i += 1
        grammar = "" if i == 1 else "s"
        log.info(f"Loaded {i} guild{grammar} in cache.")

    @app_commands.command()
    async def forcespawn(
        self,
        interaction: discord.Interaction["BallsDexBot"],
        swarm: bool = False
    ):
        """
        Force a spawn in the current server (bot owner only)
        
        Parameters
        ----------
        swarm: bool
            Whether to spawn a swarm or single monster. Defaults to False.
        """
        if not await interaction.client.is_owner(interaction.user):
            await interaction.response.send_message("Only the bot owner can use this command.", ephemeral=True)
            return
        
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return
            
        await interaction.response.defer(ephemeral=True)
            
        cog = interaction.client.get_cog("CountryBallsSpawner")
        if not cog:
            await interaction.followup.send("Could not find the spawner cog.", ephemeral=True)
            return
            
        spawn_manager = cast("CountryBallsSpawner", cog).spawn_manager
            
        # Check if the guild has a spawn channel configured
        if interaction.guild_id not in spawn_manager.cache:
            await interaction.followup.send(
                "This server does not have a spawn channel configured.", ephemeral=True
            )
            return
            
        channel = interaction.guild.get_channel(spawn_manager.cache[interaction.guild_id])
        if not channel or not isinstance(channel, discord.TextChannel):
            await interaction.followup.send(
                "Could not find the spawn channel for this server.", ephemeral=True
            )
            return
            
        if swarm:
            result = await spawn_manager.spawn_swarm(channel)
            spawn_type = "swarm"
        else:
            result = await spawn_manager.spawn_countryball(interaction.guild)
            spawn_type = "monster"
            
        if result:
            await interaction.followup.send(f"Forced a {spawn_type} spawn in this server.", ephemeral=True)
        else:
            await interaction.followup.send(
                "Failed to spawn. Check if the bot has proper permissions.", ephemeral=True
            )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        guild = message.guild
        if not guild:
            return
        if guild.id not in self.spawn_manager.cache:
            return
        if guild.id in self.bot.blacklist_guild:
            return
        await self.spawn_manager.handle_message(message)

    @commands.Cog.listener()
    async def on_ballsdex_settings_change(
        self,
        guild: discord.Guild,
        channel: Optional[discord.TextChannel] = None,
        enabled: Optional[bool] = None,
    ):
        if guild.id not in self.spawn_manager.cache:
            if enabled is False:
                return  # do nothing
            if channel:
                self.spawn_manager.cache[guild.id] = channel.id
            else:
                try:
                    config = await GuildConfig.get(guild_id=guild.id)
                except DoesNotExist:
                    return
                else:
                    self.spawn_manager.cache[guild.id] = config.spawn_channel
        else:
            if enabled is False:
                del self.spawn_manager.cache[guild.id]
            elif channel:
                self.spawn_manager.cache[guild.id] = channel.id
