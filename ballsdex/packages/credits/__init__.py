from .cog import Credits

async def setup(bot):
    await bot.add_cog(Credits(bot))