from typing import TYPE_CHECKING

from ballsdex.packages.suggest_ability.cog import SuggestAbility

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot

async def setup(bot: "BallsDexBot"):
    await bot.add_cog(SuggestAbility(bot))