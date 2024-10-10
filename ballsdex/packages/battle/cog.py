
import asyncio
import random
import discord
from discord import app_commands
from discord.ext import commands
from typing import Dict, Set, List
from ballsdex.core.models import BallInstance, Player, Ball
from ballsdex.settings import settings
from tortoise.exceptions import DoesNotExist
from ballsdex.core.utils.transformers import BallInstanceTransform
import copy
import io
from discord.ui import Button, View
from datetime import datetime, timedelta
import re


class BattleView(discord.ui.View):
    def __init__(self, starter: discord.Member, other_player: discord.Member, bot: commands.Bot):
        super().__init__(timeout=86400)
        self.starter = starter
        self.other_player = other_player
        self.bot = bot
        self.decks: Dict[int, List[BallInstance]] = {starter.id: [], other_player.id: []}
        self.battle_stats: Dict[int, List[Dict[str, int]]] = {starter.id: [], other_player.id: []}
        self.ready: Dict[int, bool] = {starter.id: False, other_player.id: False}
        self.message: discord.Message | None = None
        self.battle_started = False
        self.check_task: asyncio.Task | None = None
        self.cancelled = False
        self.battle_in_progress = False
        self.battle_log = []
        self.winner = None
        self.battle_exists = True
        self.current_attacker = starter
        self.default_emoji = discord.PartialEmoji(name="None", id=1293882244271964220)


    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not self.battle_exists:
            await interaction.response.send_message("This battle no longer exists.", ephemeral=True)
            return False
        if self.battle_in_progress:
            await interaction.response.send_message("A battle is in progress. Please wait for it to finish.", ephemeral=True)
            return False
        return True

    def create_embed(self):
        embed = discord.Embed(title="Battle", color=discord.Color.blurple())
        embed.description = (
            f"Add or remove {settings.plural_collectible_name} you want to propose to the other player "
            f"using the '/monsters battle add' and '/monsters battle remove' commands. "
            "Once you're finished, click the Ready button to start the battle."
        )

        for player in [self.starter, self.other_player]:
            deck = self.decks[player.id]
            ready_status = "✅" if self.ready[player.id] else ""
            deck_str = "\n".join([f"{self.get_emoji(ball)} #{ball.pk:0X} {ball.countryball.country} (ATK: {ball.attack} | HP: {ball.health})" for ball in deck]) if deck else "Empty"
            embed.add_field(
                name=f"{player.display_name}'s deck: {ready_status}",
                value=deck_str,
                inline=False
            )

        return embed
    
    def get_emoji(self, ball: BallInstance) -> str:
        emoji = self.bot.get_emoji(ball.countryball.emoji_id)
        return str(emoji) if emoji else "🔵"

    async def update_message(self):
        if self.message:
            try:
                self.update_button_state()
                await self.message.edit(embed=self.create_embed(), view=self)
            except discord.NotFound:
                pass

    def update_button_state(self):
        all_ready = all(self.ready.values())
        if all_ready:
            self.ready_button.label = "Start"
            self.ready_button.style = discord.ButtonStyle.blurple
        else:
            self.ready_button.style = discord.ButtonStyle.green
            self.ready_button.label = "Ready"

    async def check_ownership(self):
        while not self.battle_started and not self.cancelled:
            for player_id, deck in self.decks.items():
                player = await Player.get(discord_id=player_id)
                player_monsters = await BallInstance.filter(player=player)
                removed_monsters = [monster for monster in deck if monster not in player_monsters]
                if removed_monsters:
                    for monster in removed_monsters:
                        self.decks[player_id].remove(monster)
                    self.ready[player_id] = False
                    await self.update_message()
            await asyncio.sleep(1)

    @discord.ui.button(label="Ready", style=discord.ButtonStyle.green)
    async def ready_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in self.decks:
            return await interaction.response.send_message("You're not part of this battle.", ephemeral=True)
        
        deck = self.decks[interaction.user.id]
        all_ready = all(self.ready.values())
        
        if all_ready:
            self.battle_started = True
            if self.check_task:
                self.check_task.cancel()
            await interaction.response.defer()
            await self.start_battle(interaction)
            return
        
        if self.ready[interaction.user.id]:
            if not all_ready:
                self.ready[interaction.user.id] = False
            else:
                self.ready[interaction.user.id] = True
        else:
            if len(deck) < 1:
                return await interaction.response.send_message("You need at least 1 monster in your deck to ready up.", ephemeral=True)
            
            if len(deck) > 3:
                return await interaction.response.send_message("You can have at most 3 monsters in your deck.", ephemeral=True)
            
            self.ready[interaction.user.id] = True
        
        await self.update_message()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    async def start_battle(self, interaction: discord.Interaction):
        self.battle_in_progress = True
        battle_start_time = datetime.now()

        embed = self.message.embeds[0]  
        embed.title = "Battle in Progress"
        embed.color = discord.Color.gold()

        for player_id, monsters in self.decks.items():
            self.battle_stats[player_id] = [
                {"id": monster.pk, "health": monster.health, "attack": monster.attack}
                for monster in monsters
            ]

        while self.battle_stats[self.starter.id] and self.battle_stats[self.other_player.id]:
            attacker = self.current_attacker
            defender = self.other_player if attacker == self.starter else self.starter
            attacker_deck = self.battle_stats[attacker.id]
            defender_deck = self.battle_stats[defender.id]

            embed.clear_fields()
            embed.add_field(name=f"{attacker.display_name}'s monsters:", value=self.format_deck(attacker_deck), inline=False)
            embed.description = f"{attacker.display_name}, choose one of your monsters to attack with:"

            attacker_buttons = self.create_monster_buttons(attacker_deck, "attacker")
            attacker_view = discord.ui.View(timeout=300)  
            for button in attacker_buttons:
                attacker_view.add_item(button)

            await self.message.edit(embed=embed, view=attacker_view)

            attacker_interaction = await self.wait_for_interaction(attacker, 300)
            if isinstance(attacker_interaction, str):
                embed.description = attacker_interaction
                await self.message.edit(embed=embed, view=None)
                break

            attacker_id = int(attacker_interaction.data["custom_id"].split("_")[1])
            attacker_monster = next(monster for monster in attacker_deck if monster["id"] == attacker_id)

            embed.clear_fields()
            embed.add_field(name=f"{defender.display_name}'s monsters:", value=self.format_deck(defender_deck), inline=False)
            embed.description = f"{attacker.display_name}, choose one of {defender.display_name}'s monsters to attack:"

            defender_buttons = self.create_monster_buttons(defender_deck, "defender")
            defender_view = discord.ui.View(timeout=300) 
            for button in defender_buttons:
                defender_view.add_item(button)

            await attacker_interaction.response.edit_message(embed=embed, view=defender_view)

            defender_interaction = await self.wait_for_interaction(attacker, 300)
            if isinstance(defender_interaction, str):  
                embed.description = defender_interaction
                await self.message.edit(embed=embed, view=None)
                break

            defender_id = int(defender_interaction.data["custom_id"].split("_")[1])
            defender_monster = next(monster for monster in defender_deck if monster["id"] == defender_id)

            base_damage = attacker_monster["attack"]
            actual_damage = self.calculate_damage(base_damage)
            defender_monster["health"] = max(0, defender_monster["health"] - actual_damage)

            attack_text = (
                f"{attacker.display_name}'s "
                f"{self.get_emoji_by_id(attacker_monster['id'])} #{attacker_monster['id']:0X} {self.get_monster_name(attacker_monster['id'])} "
                f"(HP: {attacker_monster['health']} | ATK: {attacker_monster['attack']}) "
                f"attacked {defender.display_name}'s "
                f"{self.get_emoji_by_id(defender_monster['id'])} #{defender_monster['id']:0X} {self.get_monster_name(defender_monster['id'])} "
                f"for {actual_damage} damage! "
                f"(HP: {defender_monster['health'] + actual_damage} → {defender_monster['health']} | ATK: {defender_monster['attack']})!"
            )

            self.battle_log.append(attack_text)
            embed.description = attack_text
            await defender_interaction.response.edit_message(embed=embed, view=None)
            await asyncio.sleep(1.5)

            if defender_monster["health"] == 0:
                self.battle_stats[defender.id] = [monster for monster in self.battle_stats[defender.id] if monster["id"] != defender_monster["id"]]
                if not self.battle_stats[defender.id]:
                    self.winner = attacker
                    break

            self.current_attacker = defender

            if (datetime.now() - battle_start_time).total_seconds() > 600:
                timeout_message = "The battle has exceeded the 10-minute time limit. It's a draw!"
                self.battle_log.append(timeout_message)
                embed.description = timeout_message
                await self.message.edit(embed=embed, view=None)
                break

        if not self.winner:
            if len(self.battle_stats[self.starter.id]) == len(self.battle_stats[self.other_player.id]):
                winner_text = "The battle ended in a draw!"
            else:
                self.winner = self.starter if self.battle_stats[self.starter.id] else self.other_player
                winner_text = f"**{self.winner.mention} wins the battle!**"
        else:
            winner_text = f"**{self.winner.mention} wins the battle!**"

        embed.title = "Battle Result"
        embed.description = winner_text
        embed.color = discord.Color.green()
        embed.clear_fields() 


        await self.message.edit(embed=embed, view=None)

        log_button = discord.ui.Button(label="Get Battle Log", style=discord.ButtonStyle.blurple, custom_id="battle_log")

        view = discord.ui.View()
        view.add_item(log_button)

        await self.message.edit(embed=embed, view=view)

        async def interaction_handler(interaction: discord.Interaction):
            if interaction.data["custom_id"] == "battle_log":
                await self.send_battle_log(interaction.user) 
                await interaction.response.send_message("Battle Log sent to your DMs.", ephemeral=True)
                

        log_button.callback = interaction_handler
        

        
        self.battle_in_progress = False
        self.cancelled = True
        self.battle_exists = False
        self.stop()
    async def wait_for_interaction(self, user, timeout):
        def check(interaction: discord.Interaction):
            if interaction.user != user:
                asyncio.create_task(interaction.response.send_message("It's not your turn.", ephemeral=True))
                return False
            if not interaction.data:
                return False
            custom_id = interaction.data.get('custom_id', '')
            return custom_id.startswith("attacker_") or custom_id.startswith("defender_")

        try:
            return await self.bot.wait_for("interaction", check=check, timeout=timeout)
        except asyncio.TimeoutError:
            return f"{user.display_name} took too long to make a move. The other player wins by timeout!"

    def calculate_damage(self, base_damage):
        damage_range = range(base_damage - 2, base_damage + 3)
        weights = [5, 10, 70, 10, 5]  
        return random.choices(damage_range, weights=weights)[0]

    def create_monster_buttons(self, deck, prefix):
        buttons = []
        for monster in deck:
            buttons.append(
                discord.ui.Button(
                    emoji=self.get_emoji_by_id(monster["id"]),
                    style=discord.ButtonStyle.primary,
                    custom_id=f"{prefix}_{monster['id']}",
                )
            )
        
        for _ in range(3 - len(buttons)):
            buttons.append(
                discord.ui.Button(
                    emoji=self.bot.get_emoji(1293882244271964220),
                    style=discord.ButtonStyle.secondary,
                    disabled=True,
                )
            )
        
        return buttons

    def format_deck(self, deck):
        formatted_deck = [f"{self.get_emoji_by_id(monster['id'])} #{monster['id']:0X} {self.get_monster_name(monster['id'])} (HP: {monster['health']} | ATK: {monster['attack']})" for monster in deck]

        
        return "\n".join(formatted_deck)
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in [self.starter.id, self.other_player.id]:
            return await interaction.response.send_message("You're not part of this battle.", ephemeral=True)
        
        self.cancelled = True
        if self.check_task:
            self.check_task.cancel()
        
        embed = discord.Embed(title="Battle", description="This battle has been cancelled.", color=discord.Color.red())
        
        await self.message.edit(embed=embed, view=None)
        
        self.battle_exists = False
        self.stop()

    async def on_timeout(self):
        if not self.battle_started and not self.cancelled:
            self.cancelled = True
            if self.check_task:
                self.check_task.cancel()
            
            embed = discord.Embed(
                title="Battle",
                description="Battle timed out due to inactivity.",
                color=discord.Color.orange()  
            )
            

            if self.message:
                await self.message.edit(embed=embed, view=None)
            

            self.battle_exists = False
            self.stop()


    def get_emoji_by_id(self, monster_id: int) -> str:
        for deck in self.decks.values():
            for monster in deck:
                if monster.pk == monster_id:
                    return self.get_emoji(monster)
        
        default_emoji = self.bot.get_emoji(1293882244271964220)
        if default_emoji:
            return str(default_emoji)
        else:
            return "🔵" 

    def get_monster_name(self, monster_id: int) -> str:
        for deck in self.decks.values():
            for monster in deck:
                if monster.pk == monster_id:
                    return monster.countryball.country
        return "Unknown Monster"  

    async def send_battle_log(self, user: discord.User):
        if not self.battle_log:
            return

        battle_log_text = "\n".join(self.strip_emojis(log) for log in self.battle_log)
        log_file = discord.File(io.StringIO(battle_log_text), filename="battle_log.txt")
        await user.send(file=log_file)

    def strip_emojis(self, text: str) -> str:

        return re.sub(r'<:[a-zA-Z0-9_]+:[0-9]+>', '', text)


class Battle(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_battles: Dict[int, BattleView] = {}
        self.players_in_battle: Set[int] = set()

    async def cog_load(self):
        await self.add_commands_to_group()

    async def add_commands_to_group(self):
        for attempt in range(3):
            try:
                monsters_group = self.bot.tree.get_command("monsters")
                if not isinstance(monsters_group, app_commands.Group):
                    raise ValueError("monsters command is not a group")

                battle_group = app_commands.Group(name="battle", description="Battle commands")

                @battle_group.command(name="start")
                async def battle_start(interaction: discord.Interaction, opponent: discord.Member):
                    """Start a battle with another player."""
                    await self.battle(interaction, opponent)

                @battle_group.command(name="add")
                async def battle_add(interaction: discord.Interaction, monster: BallInstanceTransform):
                    """Add a monster to your battle deck."""
                    await self.add(interaction, monster)

                @battle_group.command(name="remove")
                async def battle_remove(interaction: discord.Interaction, monster: BallInstanceTransform):
                    """Remove a monster from your battle deck."""
                    await self.remove(interaction, monster)

                monsters_group.add_command(battle_group)
                print("Successfully added battle commands to monsters group")
                break 
            except Exception as e:
                if attempt < 2: 
                    print(f"Attempt {attempt + 1} failed. Retrying in 1 second...")
                    await asyncio.sleep(1)
                else:
                    print(f"Failed to add battle commands after 3 attempts: {e}")
                    raise 

    def cancel_existing_battle(self, user_id: int):
        if user_id in self.active_battles:
            battle_view = self.active_battles[user_id]
            asyncio.create_task(battle_view.on_timeout())
            del self.active_battles[user_id]
            self.players_in_battle.remove(user_id)
            if battle_view.starter.id in self.active_battles:
                del self.active_battles[battle_view.starter.id]
                self.players_in_battle.remove(battle_view.starter.id)
            if battle_view.other_player.id in self.active_battles:
                del self.active_battles[battle_view.other_player.id]
                self.players_in_battle.remove(battle_view.other_player.id)

    async def battle(self, interaction: discord.Interaction, opponent: discord.Member):
        if opponent.bot or opponent == interaction.user:
            return await interaction.response.send_message("You can't battle with that user.", ephemeral=True)

        if interaction.user.id in self.players_in_battle:
            self.cancel_existing_battle(interaction.user.id)
            pass
        
        if opponent.id in self.players_in_battle:
            return await interaction.response.send_message("That player is already in a battle.", ephemeral=True)

        battle_view = BattleView(interaction.user, opponent, self.bot)
        self.active_battles[interaction.user.id] = battle_view
        self.active_battles[opponent.id] = battle_view
        self.players_in_battle.add(interaction.user.id)
        self.players_in_battle.add(opponent.id)

        embed = battle_view.create_embed()
        
        if interaction.response.is_done():
            message = await interaction.channel.send(f"{opponent.mention}, you've been challenged to a battle!", embed=embed, view=battle_view)
        else:
            await interaction.response.send_message(f"{opponent.mention}, you've been challenged to a battle!", embed=embed, view=battle_view)
            message = await interaction.original_response()
        
        battle_view.message = message
        battle_view.check_task = asyncio.create_task(battle_view.check_ownership())

    async def add(self, interaction: discord.Interaction, monster: BallInstance):

        if interaction.user.id not in self.active_battles:
            return await interaction.response.send_message("You're not in an active battle.", ephemeral=True)
        
        battle_view = self.active_battles[interaction.user.id]
        
        if battle_view.cancelled:  
            return await interaction.response.send_message("You can't add monsters after the battle has been canceled.", ephemeral=True)

        if battle_view.battle_in_progress:
            return await interaction.response.send_message("A battle is in progress. You can't add monsters now.", ephemeral=True)

        if len(battle_view.decks[interaction.user.id]) >= 3:
            return await interaction.response.send_message("You can't add more than 3 monsters to your deck.", ephemeral=True)

        if any(m.pk == monster.pk for m in battle_view.decks[interaction.user.id]):
            return await interaction.response.send_message("You've already added this monster to your deck.", ephemeral=True)

        battle_view.decks[interaction.user.id].append(monster)
        battle_view.ready[interaction.user.id] = False 
        await battle_view.update_message()
        emoji = battle_view.get_emoji(monster)
        await interaction.response.send_message(f"Added {emoji} {monster.countryball.country} (ATK: {monster.attack} | HP: {monster.health}) to your deck.", ephemeral=True)

    async def remove(self, interaction: discord.Interaction, monster: BallInstance):

        if interaction.user.id not in self.active_battles:
            return await interaction.response.send_message("You're not in an active battle.", ephemeral=True)
        
        battle_view = self.active_battles[interaction.user.id]
        
        if battle_view.cancelled: 
            return await interaction.response.send_message("You can't remove monsters after the battle has been canceled.", ephemeral=True)

        if battle_view.battle_in_progress:
            return await interaction.response.send_message("A battle is in progress. You can't remove monsters now.", ephemeral=True)

        user_deck = battle_view.decks[interaction.user.id]
        
        for ball in user_deck:
            if ball.pk == monster.pk:
                user_deck.remove(ball)
                battle_view.ready[interaction.user.id] = False 
                await battle_view.update_message()
                emoji = battle_view.get_emoji(ball)
                return await interaction.response.send_message(f"Removed {emoji} {ball.countryball.country} (ATK: {ball.attack} | HP: {ball.health}) from your deck.", ephemeral=True)

        await interaction.response.send_message("That monster is not in your battle deck.", ephemeral=True)




    def remove_battle(self, battle_view: BattleView):
        for player_id in [battle_view.starter.id, battle_view.other_player.id]:
            if player_id in self.active_battles:
                del self.active_battles[player_id]
            if player_id in self.players_in_battle:
                self.players_in_battle.remove(player_id)

async def setup(bot):
    await bot.add_cog(Battle(bot))