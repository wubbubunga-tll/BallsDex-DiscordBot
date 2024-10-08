import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
from datetime import datetime, timedelta
from ballsdex.core.models import BallInstance, Player, Ball
from ballsdex.core.utils.transformers import BallInstanceTransform
from ballsdex.settings import settings

class Training(commands.Cog):
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
                minutes, seconds = divmod(remainder, 60)
                
                if hours > 0:
                    await interaction.response.send_message(
                        f'You can train again in {hours} hour{"s" if hours != 1 else ""}, {minutes} minute{"s" if minutes != 1 else ""}, and {seconds} second{"s" if seconds != 1 else ""}',
                        ephemeral=True
                    )
                elif minutes > 0:
                    await interaction.response.send_message(
                        f'You can train again in {minutes} minute{"s" if minutes != 1 else ""} and {seconds} second{"s" if seconds != 1 else ""}',
                        ephemeral=True
                    )
                else:
                    await interaction.response.send_message(
                        f'You can train again in {seconds} second{"s" if seconds != 1 else ""}',
                        ephemeral=True
                    )
                return

        self.last_training_times[user_id] = now
        
        await interaction.response.defer(thinking=True)
        
        increase_both = random.random() < 0.10
        increase_amount = 2 if random.random() < 0.25 else 1

        old_attack = monster.attack
        old_health = monster.health
        old_attack_bonus = monster.attack_bonus
        old_health_bonus = monster.health_bonus

        if increase_both:
            monster.attack_bonus = min(25, monster.attack_bonus + increase_amount)
            monster.health_bonus = min(25, monster.health_bonus + increase_amount)
            stat_message = f"ATK and HP stats to increase by +{increase_amount}%!"
        else:
            stat_to_increase = random.choice(["attack", "health"])
            if stat_to_increase == "attack":
                monster.attack_bonus = min(25, monster.attack_bonus + increase_amount)
                stat_message = f"ATK stat to increase by +{increase_amount}%!"
            else:
                monster.health_bonus = min(25, monster.health_bonus + increase_amount)
                stat_message = f"HP stat to increase by +{increase_amount}%!"

        await monster.save()

        new_attack = monster.attack
        new_health = monster.health

        ball = await Ball.get(id=monster.ball_id)

        emoji = self.bot.get_emoji(ball.emoji_id)
        emoji_str = f"<:_:{emoji.id}>" if emoji else ""

        message = f"{interaction.user.mention} your {emoji_str} **{ball.country}** battled against some monsters, causing its {stat_message}\n"

        if old_attack_bonus != monster.attack_bonus:
            message += f"ATK: {old_attack} → {new_attack}\n"
        if old_health_bonus != monster.health_bonus:
            message += f"HP: {old_health} → {new_health}\n"

        await interaction.followup.send(message.strip())

async def setup(bot):
    for attempt in range(3):
        monsters_group = bot.tree.get_command("monsters")
        if monsters_group and isinstance(monsters_group, app_commands.Group):
            monsters_group.add_command(Training(bot).train)
            break
        elif attempt < 2:  
            await asyncio.sleep(1)
    else:
        bot.tree.add_command(Training(bot).train)