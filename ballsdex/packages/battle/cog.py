import asyncio
import random
import discord
from discord import app_commands
from discord.ext import commands
from typing import Dict, Set
from ballsdex.core.models import BallInstance, Player, Ball
from ballsdex.settings import settings
from tortoise.exceptions import DoesNotExist

class BattleView(discord.ui.View):
    def __init__(self, starter: discord.Member, other_player: discord.Member, bot: commands.Bot):
        super().__init__(timeout=120)
        self.starter = starter
        self.other_player = other_player
        self.bot = bot
        self.decks: Dict[int, List[BallInstance]] = {starter.id: [], other_player.id: []}
        self.ready: Dict[int, bool] = {starter.id: False, other_player.id: False}
        self.message: discord.Message | None = None
        self.battle_started = False
        self.check_task: asyncio.Task | None = None
        self.cancelled = False

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
            self.ready_button.label = "Ready"
            self.ready_button.style = discord.ButtonStyle.green

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
        
        all_ready = all(self.ready.values())
        if all_ready:
            # Start the battle
            for player_id, deck in self.decks.items():
                player = await Player.get(discord_id=player_id)
                player_monsters = await BallInstance.filter(player=player)
                if not all(monster in player_monsters for monster in deck):
                    self.ready[player_id] = False
                    await self.update_message()
                    return await interaction.response.send_message(f"<@{player_id}> no longer owns all their monsters. Battle start cancelled.", ephemeral=False)
            
            self.battle_started = True
            if self.check_task:
                self.check_task.cancel()
            await self.start_battle(interaction)
        else:
            # Set player as ready
            self.ready[interaction.user.id] = True
            await self.update_message()
            await interaction.response.defer()

    async def start_battle(self, interaction: discord.Interaction):
        embed = discord.Embed(title="Battle in Progress", color=discord.Color.gold())
        await interaction.response.edit_message(embed=embed, view=None)

        player1_monsters = self.decks[self.starter.id].copy()
        player2_monsters = self.decks[self.other_player.id].copy()

        while player1_monsters and player2_monsters:
            attacker = random.choice(player1_monsters)
            defender = random.choice(player2_monsters)

            damage = attacker.attack
            defender.health -= damage

            attack_text = (
                f"{self.starter.display_name}'{'s' if not self.starter.display_name.endswith('s') else ''} "
                f"{self.get_emoji(attacker)} {attacker.countryball.country} (HP: {attacker.health} | ATK: {attacker.attack}) "
                f"attacked {self.other_player.display_name}'{'s' if not self.other_player.display_name.endswith('s') else ''} "
                f"{self.get_emoji(defender)} {defender.countryball.country} "
                f"(HP: {defender.health + damage} → {defender.health})!"
            )

            embed.description = attack_text
            await self.message.edit(embed=embed)
            await asyncio.sleep(2)

            if defender.health <= 0:
                player2_monsters.remove(defender)

            player1_monsters, player2_monsters = player2_monsters, player1_monsters
            self.starter, self.other_player = self.other_player, self.starter

        winner = self.starter if player2_monsters else self.other_player
        embed = discord.Embed(title="Battle Result", description=f"{winner.mention} wins the battle!", color=discord.Color.green())
        await self.message.edit(embed=embed, view=None)
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction and interaction.user and interaction.user.id not in self.decks:
            return await interaction.response.send_message("You're not part of this battle.", ephemeral=True)
        
        self.cancelled = True
        if self.check_task:
            self.check_task.cancel()
        
        embed = discord.Embed(title="Battle", description="This battle has been cancelled.", color=discord.Color.red())
        
        for _ in range(15):  # 3 seconds, 5 times per second
            if interaction and not interaction.response.is_done():
                await interaction.response.edit_message(embed=embed, view=None)
            elif self.message:
                await self.message.edit(embed=embed, view=None)
            await asyncio.sleep(0.2)
        
        # Remove the battle from the active battles list
        cog = interaction.client.get_cog("Battle")
        if isinstance(cog, Battle):
            cog.remove_battle(self)
        
        self.stop()

    async def on_timeout(self):
        if not self.battle_started and not self.cancelled:
            self.cancelled = True
            if self.check_task:
                self.check_task.cancel()
            embed = discord.Embed(title="Battle", description="This battle has timed out.", color=discord.Color.orange())
            if self.message:
                await self.message.edit(embed=embed, view=None)
            self.stop()

class Battle(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_battles: Dict[int, BattleView] = {}
        self.players_in_battle: Set[int] = set()

    async def add_commands_to_group(self):
        monsters_group = self.bot.tree.get_command("monsters")
        if not isinstance(monsters_group, app_commands.Group):
            raise ValueError("monsters command is not a group")

        battle_group = app_commands.Group(name="battle", description="Battle commands")
        
        @battle_group.command(name="start")
        async def battle_start(interaction: discord.Interaction, opponent: discord.Member):
            await self.battle(interaction, opponent)

        @battle_group.command(name="add")
        async def battle_add(interaction: discord.Interaction, monster_id: str):
            await self.add(interaction, monster_id)

        @battle_group.command(name="remove")
        async def battle_remove(interaction: discord.Interaction, monster_id: str):
            await self.remove(interaction, monster_id)

        for _ in range(3):
            try:
                monsters_group.add_command(battle_group)
                break
            except Exception as e:
                print(f"Failed to add battle commands to monsters group: {e}")
                await asyncio.sleep(1)
        else:
            print("Failed to add battle commands after 3 attempts")

    async def cog_load(self):
        await self.add_commands_to_group()

    def cancel_existing_battle(self, user_id: int):
        if user_id in self.active_battles:
            battle_view = self.active_battles[user_id]
            asyncio.create_task(battle_view.cancel_button(None, battle_view.cancel_button))
            self.remove_battle(battle_view)

    def remove_battle(self, battle_view: BattleView):
        for player_id in [battle_view.starter.id, battle_view.other_player.id]:
            if player_id in self.active_battles:
                del self.active_battles[player_id]
            if player_id in self.players_in_battle:
                self.players_in_battle.remove(player_id)

    async def battle(self, interaction: discord.Interaction, opponent: discord.Member):
        if opponent.bot or opponent == interaction.user:
            return await interaction.response.send_message("You can't battle with that user.", ephemeral=True)

        if interaction.user.id in self.players_in_battle:
            self.cancel_existing_battle(interaction.user.id)
            await interaction.response.send_message("Your previous battle has been cancelled.", ephemeral=True)
        
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

    async def add(self, interaction: discord.Interaction, monster_id: str):
        if interaction.user.id not in self.active_battles:
            return await interaction.response.send_message("You're not in an active battle.", ephemeral=True)

        battle_view = self.active_battles[interaction.user.id]
        
        try:
            monster_instance = await BallInstance.get(pk=int(monster_id, 16)).prefetch_related('ball', 'player')
        except ValueError:
            return await interaction.response.send_message("Invalid monster ID.", ephemeral=True)
        except DoesNotExist:
            return await interaction.response.send_message("Monster not found.", ephemeral=True)

        player = await Player.get(discord_id=interaction.user.id)
        if monster_instance.player.id != player.id:
            return await interaction.response.send_message("You don't own this monster.", ephemeral=True)

        if len(battle_view.decks[interaction.user.id]) >= 3:
            return await interaction.response.send_message("You can't add more than 3 monsters to your deck.", ephemeral=True)

        if monster_instance in battle_view.decks[interaction.user.id]:
            return await interaction.response.send_message("You've already added this monster to your deck.", ephemeral=True)

        battle_view.decks[interaction.user.id].append(monster_instance)
        battle_view.ready[interaction.user.id] = False
        await battle_view.update_message()
        emoji = battle_view.get_emoji(monster_instance)
        await interaction.response.send_message(f"Added {emoji} {monster_instance.ball.country} (ATK: {monster_instance.attack} | HP: {monster_instance.health}) to your deck.", ephemeral=True)

    async def remove(self, interaction: discord.Interaction, monster_id: str):
        if interaction.user.id not in self.active_battles:
            return await interaction.response.send_message("You're not in an active battle.", ephemeral=True)

        battle_view = self.active_battles[interaction.user.id]
        
        try:
            monster_instance = await BallInstance.get(pk=int(monster_id, 16)).prefetch_related('ball')
        except ValueError:
            return await interaction.response.send_message("Invalid monster ID.", ephemeral=True)
        except DoesNotExist:
            return await interaction.response.send_message("Monster not found.", ephemeral=True)

        if monster_instance not in battle_view.decks[interaction.user.id]:
            return await interaction.response.send_message("That monster is not in your battle deck.", ephemeral=True)

        battle_view.decks[interaction.user.id].remove(monster_instance)
        battle_view.ready[interaction.user.id] = False
        await battle_view.update_message()
        emoji = battle_view.get_emoji(monster_instance)
        await interaction.response.send_message(f"Removed {emoji} {monster_instance.ball.country} (ATK: {monster_instance.attack} | HP: {monster_instance.health}) from your deck.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Battle(bot))