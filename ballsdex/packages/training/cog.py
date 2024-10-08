import discord
from discord.ext import commands
from discord import app_commands
import random
from datetime import datetime, timedelta
from ballsdex.core.models import BallInstance, Player, Ball
from ballsdex.core.utils.transformers import BallInstanceTransform
from ballsdex.settings import settings

class Training(commands.GroupCog, group_name="monsters"):
    def __init__(self, bot):
        self.bot = bot
        self.last_training_times = {}

    @app_commands.command(name="train")
    @app_commands.checks.cooldown(1, 3) 
    async def train(self, interaction: discord.Interaction, monster: BallInstanceTransform):
        """
        Train one of your monsters to increase its stats.

        Parameters
        ----------
        monster: BallInstance
            The monster you want to train
        """
        if not monster:
            return
        
        user_id = interaction.user.id
        now = datetime.now()

        if user_id in self.last_training_times:
            last_training_time = self.last_training_times[user_id]
            if now - last_training_time < timedelta(hours=12):
                remaining_time = timedelta(hours=12) - (now - last_training_time)
                hours, remainder = divmod(remaining_time.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                await interaction.response.send_message(
                    f"You can train again in {hours} hours and {minutes} minutes.",
                    ephemeral=True
                )
                return

        self.last_training_times[user_id] = now

        stat_to_increase = random.choice(["attack", "health"])
        increase_amount = 2 if random.random() < 0.1 else 1

        if stat_to_increase == "attack":
            monster.attack_bonus = min(25, monster.attack_bonus + increase_amount)
            stat_name = "ATK"
        else:
            monster.health_bonus = min(25, monster.health_bonus + increase_amount)
            stat_name = "HP"

        await monster.save()

        ball = await Ball.get(id=monster.ball_id)

        emoji = self.bot.get_emoji(ball.emoji_id)
        emoji_str = f"<:_:{emoji.id}>" if emoji else ""

        await interaction.response.send_message(
            f"{interaction.user.mention} your {emoji_str} **{ball.country}** battled against "
            f"some monsters, causing its {stat_name} stat to increase by +{increase_amount}%!"
        )

async def setup(bot):
    await bot.add_cog(Training(bot))