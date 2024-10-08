from typing import TYPE_CHECKING

from ballsdex.packages.training.cog import Training

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot

async def setup(bot: "BallsDexBot"):
    await bot.add_cog(Training(bot))