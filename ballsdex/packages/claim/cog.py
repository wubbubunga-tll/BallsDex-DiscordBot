# /code/ballsdex/packages/claim/cog.py
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta
import random
import ballsdex
from ballsdex.core.utils.transformers import (
    BallTransform,
    SpecialTransform,
)
from ballsdex.core.models import (
    Ball,
    BallInstance,
    BlacklistedGuild,
    BlacklistedID,
    GuildConfig,
    Player,
    Trade,
    TradeObject,
)
from ballsdex.packages.countryballs.countryball import CountryBall
import ballsdex.packages.config.components as Components
from typing import TYPE_CHECKING, cast


# dictionary 
last_claim_times = {}

# cooldown duration
COOLDOWN_DURATION = timedelta(minutes=90)

class Claim(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="claim", description="Claim a random monster - made by Hallow")
    async def claim(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        now = datetime.now()

        if user_id in last_claim_times:
            last_claim_time = last_claim_times[user_id]
            elapsed_time = now - last_claim_time

            if elapsed_time < COOLDOWN_DURATION:
                remaining_time = COOLDOWN_DURATION - elapsed_time
                hours, remainder = divmod(remaining_time.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                
                if hours > 0:
                    await interaction.response.send_message(
                        f'You cannot claim for {hours} hour{"s" if hours != 1 else ""}, {minutes} minute{"s" if minutes != 1 else ""}, and {seconds} second{"s" if seconds != 1 else ""}',
                        ephemeral=True
                    )
                elif minutes > 0:
                    await interaction.response.send_message(
                        f'You cannot claim for {minutes} minute{"s" if minutes != 1 else ""} and {seconds} second{"s" if seconds != 1 else ""}',
                        ephemeral=True
                    )
                else:
                    await interaction.response.send_message(
                        f'You cannot claim for {seconds} second{"s" if seconds != 1 else ""}',
                        ephemeral=True
                    )
                return

        # Update the last claim time 
        last_claim_times[user_id] = now
        UserID = str(interaction.user.id)
        cob = await CountryBall.get_random()
        player, created = await Player.get_or_create(discord_id=UserID)
        instance = await BallInstance.create(
            ball=cob.model,
            player=player,
            shiny = random.randint(1, 2048) == 1,
            attack_bonus=random.randint(-20, 20),
            health_bonus=random.randint(-20, 20),
        )
        await interaction.response.defer(thinking=True)

        special = ""
        if instance.shiny:
            special += f"✨ ***It's a shiny monster!*** ✨\n"

        emoji_id = cob.model.emoji_id

        await interaction.followup.send(
            f"{interaction.user.mention} received a <:_:{emoji_id}> **{cob.name}** from a free claim!\n"
            f"**Info:** ⚔️ `{instance.attack_bonus:+}` ❤️ `{instance.health_bonus:+}` ✨ `{instance.shiny}`\n\n"
        )


async def setup(bot):
    await bot.add_cog(Claim(bot))
