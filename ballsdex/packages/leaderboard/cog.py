import discord
from discord import app_commands
from discord.ext import commands
from tortoise.functions import Count
from tortoise.expressions import Q
from typing import List, Tuple
import asyncio
import time

from ballsdex.core.models import Player, BallInstance
from ballsdex.core.utils.paginator import FieldPageSource, Pages
from ballsdex.settings import settings

class Leaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.leaderboard_cache: dict[str, List[Tuple[int, int]]] = {
            "all": [],
            "shiny": []
        }
        self.last_update = 0

    async def update_leaderboard_cache(self):
        all_players = await Player.all().annotate(monster_count=Count('balls')).order_by('-monster_count').limit(50)
        shiny_players = await Player.all().annotate(
            shiny_count=Count('balls', _filter=Q(balls__shiny=True))
        ).filter(shiny_count__gt=0).order_by('-shiny_count').limit(50)

        self.leaderboard_cache["all"] = [(int(player.discord_id), player.monster_count) for player in all_players]
        self.leaderboard_cache["shiny"] = [(int(player.discord_id), player.shiny_count) for player in shiny_players]
        self.last_update = time.time()

    @app_commands.command()
    @app_commands.checks.cooldown(1, 10)
    async def leaderboard(
        self, 
        interaction: discord.Interaction, 
        top: app_commands.Range[int, 1, 50] | None = None,
        shiny_only: bool = False,
        ascending: bool = False
    ):
        """
        Display the FanmadeDex leaderboard.

        Parameters
        ----------
        top: int
            The number of top players to display (optional, default 10, max 50)
        shiny_only: bool
            Whether to show only shiny monsters (default False)
        ascending: bool
            Whether to show the leaderboard in ascending order (default False)
        """
        await interaction.response.defer(thinking=True)

        current_time = time.time()
        if current_time - self.last_update > 120:  # 2 minutes cache
            await self.update_leaderboard_cache()

        cache_key = "shiny" if shiny_only else "all"
        leaderboard_data = self.leaderboard_cache[cache_key]
        
        if top is None:
            top = 10
        leaderboard_data = leaderboard_data[:top]
        
        if ascending:
            leaderboard_data = list(reversed(leaderboard_data))

        entries = []
        user_ids_to_fetch = []

        for index, (discord_id, monster_count) in enumerate(leaderboard_data, start=1):
            if shiny_only and monster_count == 0:
                continue
            user = self.bot.get_user(discord_id)
            if user:
                username = user.name
            else:
                username = f"Unknown User ({discord_id})"
                user_ids_to_fetch.append(discord_id)
            
            entries.append((
                f"{index}. {username}",
                f"{monster_count} {'shiny ' if shiny_only else ''}{settings.collectible_name}s"
            ))

        if user_ids_to_fetch:
            fetched_users = await asyncio.gather(*[self.bot.fetch_user(uid) for uid in user_ids_to_fetch])
            for user in fetched_users:
                for i, (entry_title, entry_value) in enumerate(entries):
                    if f"Unknown User ({user.id})" in entry_title:
                        entries[i] = (entry_title.replace(f"Unknown User ({user.id})", user.name), entry_value)
                        break

        source = FieldPageSource(entries, per_page=10)
        
        title_parts = ["FanmadeDex Leaderboard ("]
        if shiny_only:
            title_parts.append("Shiny Only, ")
        title_parts.append(f"Top {len(entries)}")
        if ascending:
            title_parts.append(", Ascending")
        title_parts.append(")")
        
        source.embed.title = "".join(title_parts)
        source.embed.color = discord.Color.gold()

        pages = Pages(source=source, interaction=interaction, compact=True)
        await pages.start()

    @commands.Cog.listener()
    async def on_ballsdex_settings_change(self, guild: discord.Guild, channel: discord.TextChannel | None = None, enabled: bool | None = None):
        await self.update_leaderboard_cache()

def setup(bot):
    bot.add_cog(Leaderboard(bot))
