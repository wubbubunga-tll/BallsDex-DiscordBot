import os
import discord
import logging
import random
import re
import pathlib
from random import choice
from pathlib import Path
from datetime import date, datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from discord.ext import commands
from discord.ext.commands import Bot
import asyncio
import pytz

from discord.utils import get
from ballsdex.core.models import GuildConfig
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View, button
from typing import cast
from tortoise.functions import Count

from ballsdex.settings import settings
from ballsdex.core.utils.logging import log_action
from ballsdex.core.utils.paginator import FieldPageSource, Pages
from ballsdex.settings import settings
from ballsdex.core.utils.buttons import ConfirmChoiceView
from ballsdex.core.models import Player, Ball, BallInstance, Special, Regime, balls, specials 
from ballsdex.packages.countryballs.countryball import CountryBall
from ballsdex.packages.admin.cog import save_file
from PIL import Image, ImageDraw, ImageFont, ImageOps

from ballsdex.core.models import PrivacyPolicy

from ballsdex.core.models import (
    BallInstance,
    DonationPolicy,
    Player,
    PrivacyPolicy,
    Trade,
    TradeObject,
    balls,
)
from ballsdex.core.utils.paginator import FieldPageSource, Pages
from ballsdex.core.utils.transformers import (
    BallTransform,
    BallEnabledTransform,
    BallInstanceTransform,
    SpecialTransform,
    RegimeTransform,
    EconomyTransform,
    SpecialEnabledTransform,
    TradeCommandType,
)

from typing import TYPE_CHECKING, Iterable, Tuple, Type

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot
    from ballsdex.core.models import BallInstance
    from ballsdex.packages.countryballs.cog import CountryBallsSpawner

log = logging.getLogger("ballsdex.packages.Rarity")
FILENAME_RE = re.compile(r"^(.+)(\.\S+)$")

def format_rarity(rarity: float) -> str:
    if rarity >= 1:
        return f"{rarity:.1f}%"
    elif rarity >= 0.1:
        return f"{rarity:.2f}%"
    else:
        return f"{rarity:.3f}%"

class Rarity(commands.GroupCog, name="rarity"):
    """
    Simple vote commands.
    """

    def __init__(self, bot: "BallsDexBot"):
        self.bot = bot
    
    @app_commands.command()
    @app_commands.checks.cooldown(1, 60, key=lambda i: i.user.id)
    async def list(self, interaction: discord.Interaction):
        # DO NOT CHANGE THE CREDITS TO THE AUTHOR HERE!
        """
        View the rarity list - created by GamingadlerHD
        """
        # Filter enabled collectibles
        enabled_collectibles = [x for x in balls.values() if x.enabled]

        if not enabled_collectibles:
            await interaction.response.send_message(
                f"There are no collectibles registered in {settings.bot_name} yet.",
                ephemeral=True,
            )
            return

        # Sort collectibles by rarity in ascending order
        sorted_collectibles = sorted(enabled_collectibles, key=lambda x: x.rarity)

        entries = []

        for collectible in sorted_collectibles:
            name = f"{collectible.country}"
            emoji = self.bot.get_emoji(collectible.emoji_id)

            if emoji:
                emote = str(emoji)
            else:
                emote = "N/A"
            #if you want the Rarity to only show full numbers like 1 or 12 use the code part here:
            #rarity = int(collectible.rarity)
            # otherwise you want to display numbers like 1.5, 5.3, 76.9 use the normal part.
            rarity = str(collectible.rarity)
            
            entry = (name, f"{emote} Rarity: {rarity}")
            entries.append(entry)
        # This is the number of countryballs who are displayed at one page, 
        # you can change this, but keep in mind: discord has an embed size limit.
        per_page = 8

        source = FieldPageSource(entries, per_page=per_page, inline=False, clear_description=False)
        source.embed.description = (
            f"__**{settings.bot_name} rarity**__"
        )
        source.embed.colour = discord.Colour.blurple()
        source.embed.set_author(
            name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url
        )

        pages = Pages(source=source, interaction=interaction, compact=True)
        await pages.start()



    

    @app_commands.command()
    async def search(
        self,
        interaction: discord.Interaction,
        ball: app_commands.Transform[Ball, BallTransform],
        shiny: bool = False,
    ):
        """
        View the rarity of a specific ball - created by Hallow
        """
        
        rarity = ball.rarity
        
        if shiny:
            shiny_chance = 1 / 2048
            rarity *= shiny_chance
        
        ball_name = f"Shiny {ball.country}" if shiny else ball.country
        formatted_rarity = format_rarity(rarity)
        

        await interaction.response.send_message(
            f"{ball_name}'s rarity: {formatted_rarity}",
            ephemeral=True,
        )
    
