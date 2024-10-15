from typing import TYPE_CHECKING

from ballsdex.packages.rarity.cog import Rarity 

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot


async def setup(bot: "BallsDexBot"):
    await bot.add_cog(Rarity(bot))
