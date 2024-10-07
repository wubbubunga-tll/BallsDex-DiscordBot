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
from ballsdex.settings import settings
from ballsdex.packages.countryballs.countryball import CountryBall
import ballsdex.packages.config.components as Components
from typing import TYPE_CHECKING, cast

last_claim_times = {}
last_boost_claim_times = {}
last_staff_claim_times = {}

COOLDOWN_DURATION = timedelta(minutes=90)
BOOST_COOLDOWN_DURATION = timedelta(hours=2)
STAFF_COOLDOWN_DURATION = timedelta(hours=1, minutes=45)

class Claim(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def give_monster(self, interaction: discord.Interaction, cobs: list[CountryBall], claim_type: str):
        UserID = str(interaction.user.id)
        player, created = await Player.get_or_create(discord_id=UserID)
        
        monster_info = []
        shiny_chance_buff = 1

        if claim_type == "boost" and random.random() < 0.2:
            shiny_chance_buff = 1.5
        elif claim_type == "staff" and random.random() < 0.1:
            shiny_chance_buff = 1.5

        for cob in cobs:
            shiny_roll = random.randint(1, int(2048 / shiny_chance_buff))
            instance = await BallInstance.create(
                ball=cob.model,
                player=player,
                shiny = shiny_roll == 1,
                attack_bonus=random.randint(-20, 20),
                health_bonus=random.randint(-20, 20),
            )

            emoji_id = cob.model.emoji_id
            monster_info.append(
                f"<:_:{emoji_id}> **{cob.name}**\n"
                f"**Info:** ⚔️ `{instance.attack_bonus:+}` ❤️ `{instance.health_bonus:+}` ✨ `{instance.shiny}`"
            )

        monsters_text = "\n\n".join(monster_info)
        
        if claim_type == "boost":
            message = (
                f"{interaction.user.mention} received the following monsters:\n\n"
                f"{monsters_text}\n\n"
                f"from a boostclaim!\n"
                f"Thank you for supporting FanmadeDex!"
            )
        elif claim_type == "staff":
            if len(monster_info) == 1:
                message = (
                    f"{interaction.user.mention} received a {monster_info[0]} from a staffclaim!"
                )
            else:
                message = (
                    f"{interaction.user.mention} received the following monsters:\n\n"
                    f"{monsters_text}\n\n"
                    f"from a staffclaim!\n"
                    f"Thank you for being a great staff!"
                )
        else:
            if len(monster_info) == 1:
                message = (
                    f"{interaction.user.mention} received a {monster_info[0]} from a free claim!"
                )
            else:
                message = (
                    f"{interaction.user.mention} received the following monsters:\n\n"
                    f"{monsters_text}\n\n"
                    f"from a free claim!"
                )

        await interaction.followup.send(message)


    @app_commands.command(name="claim", description="Claim a random monster - made by Venus")
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

        last_claim_times[user_id] = now
        
        await interaction.response.defer(thinking=True)
        cob = await CountryBall.get_random()
        await self.give_monster(interaction, [cob], "free")

    @app_commands.command(name="boostclaim", description="Claim two random monsters - made by Venus")
    @app_commands.checks.has_any_role(1274848370833494017)
    async def boostclaim(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        now = datetime.now()

        if user_id in last_boost_claim_times:
            last_claim_time = last_boost_claim_times[user_id]
            elapsed_time = now - last_claim_time

            if elapsed_time < BOOST_COOLDOWN_DURATION:
                remaining_time = BOOST_COOLDOWN_DURATION - elapsed_time
                hours, remainder = divmod(remaining_time.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                
                if hours > 0:
                    await interaction.response.send_message(
                        f'You cannot boostclaim for {hours} hour{"s" if hours != 1 else ""}, {minutes} minute{"s" if minutes != 1 else ""}, and {seconds} second{"s" if seconds != 1 else ""}',
                        ephemeral=True
                    )
                elif minutes > 0:
                    await interaction.response.send_message(
                        f'You cannot boostclaim for {minutes} minute{"s" if minutes != 1 else ""} and {seconds} second{"s" if seconds != 1 else ""}',
                        ephemeral=True
                    )
                else:
                    await interaction.response.send_message(
                        f'You cannot boostclaim for {seconds} second{"s" if seconds != 1 else ""}',
                        ephemeral=True
                    )
                return

        last_boost_claim_times[user_id] = now
        
        await interaction.response.defer(thinking=True)
        num_monsters = 3 if random.random() < 0.1 else 2
        cobs = [await CountryBall.get_random() for _ in range(num_monsters)]
        await self.give_monster(interaction, cobs, "boost")
    
    @app_commands.command(name="staffclaim", description="Claim one or two random monsters - made by Venus")
    @app_commands.checks.has_any_role(*settings.root_role_ids, *settings.admin_role_ids)
    async def staffclaim(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        now = datetime.now()

        if user_id in last_staff_claim_times:
            last_claim_time = last_staff_claim_times[user_id]
            elapsed_time = now - last_claim_time

            if elapsed_time < STAFF_COOLDOWN_DURATION:
                remaining_time = STAFF_COOLDOWN_DURATION - elapsed_time
                hours, remainder = divmod(remaining_time.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                
                if hours > 0:
                    await interaction.response.send_message(
                        f'You cannot staffclaim for {hours} hour{"s" if hours != 1 else ""}, {minutes} minute{"s" if minutes != 1 else ""}, and {seconds} second{"s" if seconds != 1 else ""}',
                        ephemeral=True
                    )
                elif minutes > 0:
                    await interaction.response.send_message(
                        f'You cannot staffclaim for {minutes} minute{"s" if minutes != 1 else ""} and {seconds} second{"s" if seconds != 1 else ""}',
                        ephemeral=True
                    )
                else:
                    await interaction.response.send_message(
                        f'You cannot staffclaim for {seconds} second{"s" if seconds != 1 else ""}',
                        ephemeral=True
                    )
                return

        last_staff_claim_times[user_id] = now
        
        await interaction.response.defer(thinking=True)
        num_monsters = 2 if random.random() < 0.45 else 1
        cobs = [await CountryBall.get_random() for _ in range(num_monsters)]
        await self.give_monster(interaction, cobs, "staff")

async def setup(bot):
    await bot.add_cog(Claim(bot))
