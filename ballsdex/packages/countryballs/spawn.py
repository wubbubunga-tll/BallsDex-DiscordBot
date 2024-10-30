import asyncio
import logging
import random
from collections import deque, namedtuple
from dataclasses import dataclass, field
from datetime import datetime
from typing import cast
import random

import discord
from discord import app_commands 
from discord.ext import commands

from ballsdex.packages.countryballs.countryball import CountryBall

log = logging.getLogger("ballsdex.packages.countryballs")

SPAWN_CHANCE_RANGE = (15, 20)

CachedMessage = namedtuple("CachedMessage", ["content", "author_id"])


@dataclass
class SpawnCooldown:
    """
    Represents the spawn internal system per guild. Contains the counters that will determine
    if a countryball should be spawned next or not.

    Attributes
    ----------
    time: datetime
        Time when the object was initialized. Block spawning when it's been less than two minutes
    amount: float
        A number starting at 0, incrementing with the messages until reaching `chance`. At this
        point, a ball will be spawned next.
    chance: int
        The number `amount` has to reach for spawn. Determined randomly with `SPAWN_CHANCE_RANGE`
    lock: asyncio.Lock
        Used to ratelimit messages and ignore fast spam
    message_cache: ~collections.deque[CachedMessage]
        A list of recent messages used to reduce the spawn chance when too few different chatters
        are present. Limited to the 100 most recent messages in the guild.
    """

    time: datetime
    # initialize partially started, to reduce the dead time after starting the bot
    amount: float = field(default=SPAWN_CHANCE_RANGE[0] // 2)
    chance: int = field(default_factory=lambda: random.randint(*SPAWN_CHANCE_RANGE))
    lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False)
    message_cache: deque[CachedMessage] = field(default_factory=lambda: deque(maxlen=100))

    def reset(self, time: datetime):
        self.amount = 1.0
        self.chance = random.randint(*SPAWN_CHANCE_RANGE)
        try:
            self.lock.release()
        except RuntimeError:  # lock is not acquired
            pass
        self.time = time

    async def increase(self, message: discord.Message) -> bool:
        # this is a deque, not a list
        # its property is that, once the max length is reached (100 for us),
        # the oldest element is removed, thus we only have the last 100 messages in memory
        self.message_cache.append(
            CachedMessage(content=message.content, author_id=message.author.id)
        )

        if self.lock.locked():
            return False

        async with self.lock:
            amount = 1
            if message.guild.member_count < 5 or message.guild.member_count > 1000:  # type: ignore
                amount /= 2
            if message._state.intents.message_content and len(message.content) < 5:
                amount /= 2
            if len(set(x.author_id for x in self.message_cache)) < 4 or (
                len(list(filter(lambda x: x.author_id == message.author.id, self.message_cache)))
                / self.message_cache.maxlen  # type: ignore
                > 0.4
            ):
                amount /= 2
            self.amount += amount
            await asyncio.sleep(10)
        return True


@dataclass
class SpawnManager:
    """
    Manages the spawning of countryballs in guilds.
    
    cooldowns: dict[int, SpawnCooldown]
        A dictionary of guild IDs and their spawn cooldowns
    cache: dict[int, int]
        A dictionary of guild IDs and their spawn channel IDs
    swarm_sizes: dict[int, float]
        A dictionary of swarm sizes and their spawn probabilities
    swarm_chance: float
        The fixed probability of a swarm occurring (5%)
    """
    def __init__(self):
        self.cooldowns: dict[int, SpawnCooldown] = {}
        self.cache: dict[int, int] = {}
        self.swarm_sizes = {
            2: 0.25, 
            3: 0.40, 
            4: 0.20, 
            5: 0.10, 
            6: 0.05,  
        }
        self.swarm_chance: float = 0.05  # Set fixed 5% chance for swarm

    async def spawn_countryball(self, guild: discord.Guild) -> bool:
        """
        Spawn a single countryball in a guild.

        Parameters
        ----------
        guild: discord.Guild
            The guild to spawn the countryball in.

        Returns
        -------
        bool
            Whether the spawn was successful
        """
        channel = guild.get_channel(self.cache[guild.id])
        if not channel:
            log.warning(f"Lost channel {self.cache[guild.id]} for guild {guild.name}.")
            del self.cache[guild.id]
            return False
        ball = await CountryBall.get_random()
        success = await ball.spawn(cast(discord.TextChannel, channel))
        
        return success

    async def spawn_swarm(self, channel: discord.TextChannel) -> bool:
        """
        Spawn a swarm of countryballs in the given channel.
        
        Parameters
        ----------
        channel: discord.TextChannel
            The channel to spawn the swarm in
            
        Returns
        -------
        bool
            Whether the spawn was successful
        """
        swarm_size = random.choices(
            list(self.swarm_sizes.keys()),
            weights=list(self.swarm_sizes.values()),
            k=1
        )[0]
        
        try:
            permissions = channel.permissions_for(channel.guild.me)
            if not (permissions.send_messages and permissions.embed_links):
                log.warning(f"Missing permissions to spawn swarm in channel {channel}.")
                return False
                
            await channel.send(
                f"# 🪺 *A swarm of * ***{swarm_size}*** *monsters is approaching!* 🪺"
            )
            
            await asyncio.sleep(1)
            
            regular_spawns = swarm_size - 1 if swarm_size >= 4 else swarm_size
            
            for i in range(regular_spawns):
                ball = await CountryBall.get_random()
                success = await ball.spawn(channel)
                if not success:
                    return False
                await asyncio.sleep(0.5)  
            
            if swarm_size >= 4:
                ball = await CountryBall.get_random_norarity()
                success = await ball.spawn(channel)
                if not success:
                    return False
            
            return True
            
        except discord.Forbidden:
            log.error(f"Missing permission to spawn swarm in channel {channel}.")
            return False
        except discord.HTTPException:
            log.error("Failed to spawn swarm", exc_info=True)
            return False

    async def handle_message(self, message: discord.Message):
        """
        Handle a message and possibly trigger a spawn.

        This checks the guild's cooldown and may trigger a spawn if conditions are met.
        Takes into account the server's member count and time since last spawn.

        Parameters
        ----------
        message: discord.Message
            The message that triggered this check
        """
        guild = message.guild
        if not guild:
            return

        cooldown = self.cooldowns.get(guild.id, None)
        if not cooldown:
            cooldown = SpawnCooldown(message.created_at)
            self.cooldowns[guild.id] = cooldown

        delta = (message.created_at - cooldown.time).total_seconds()
        if not guild.member_count:
            return
        elif guild.member_count < 5:
            multiplier = 0.8
        elif guild.member_count < 100:
            multiplier = 0.8
        elif guild.member_count < 1000:
            multiplier = 0.8
        else:
            multiplier = 0.8
        chance = cooldown.chance - multiplier * (delta // 60)

        if not await cooldown.increase(message):
            return

        if cooldown.amount <= chance:
            return

        if delta < 400:
            return

        cooldown.reset(message.created_at)
        channel = guild.get_channel(self.cache[guild.id])
        if not channel:
            log.warning(f"Lost channel {self.cache[guild.id]} for guild {guild.name}.")
            del self.cache[guild.id]
            return
        
        if random.random() < self.swarm_chance:
            await self.spawn_swarm(cast(discord.TextChannel, channel))
        else:
            await self.spawn_countryball(guild)
