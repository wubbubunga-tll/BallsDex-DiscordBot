from typing import TYPE_CHECKING

from ballsdex.packages.leaderboard.cog import Leaderboard

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot

async def setup(bot: "BallsDexBot"):
    await bot.add_cog(Leaderboard(bot))