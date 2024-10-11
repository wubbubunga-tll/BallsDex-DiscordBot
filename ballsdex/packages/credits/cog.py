import discord
from discord.ext import commands
from discord import app_commands

class Credits(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command()
    @app_commands.checks.cooldown(1, 10) 
    async def credits(self, interaction: discord.Interaction):
        """Display the credits for FanmadeDex"""
        try:
            content = """**CREDITS  🏆**
This is to show credits towards people who helped the bot become what it is now!

**Venus (Owner, Main Scripter) <:Venus:1293959996945469510> 
GHOSTYMPA <:GHOSTYMPA:1266784573317058639>
DDOMSM <:DDOMSM:1267481517198807060>
Raw Zebra <:RawZebra:1269788571284410470>
JakeTheDrake <:JakeTheDrake:1269785238398308434>
Charlilee <:Charlilee:1273687213426737184>
Interdimensional Music <:InterdimensionalMusic:1269794316147228703>
Pyro<:PyroMSM:1269775583165022369>
Slimer <:SlimerMSM:1269774390833188905>
Nova / MSM <:NovaMSM:1267481416330121216>
PlushyPlushMSM <:PlushyPlushMSM:1269780280109957223>
Logan Peters <:LoganPetersMSM:1269778782076534864>
Uksus <:Uksus:1273689692793208904>
Astroshock25 <:Astroshock25:1275579109237587989>
Licoad666 <:Licoad666:1275802191109820550>
Wubtopia <:Wubtopia:1278832063616909394>
Gorm / Demochees <:Demochees:1278832427313270848>
Calpamos <:Calpamos:1293964105539129345>
**
And special thanks to **Charlilee **<:Charlilee:1273687213426737184> for creating the FanmadeDex logo art, and **Bylogic**<:Bylogic:1275813304220123247> for setting up the official server."""
        except (discord.NotFound, discord.Forbidden, AttributeError):
            content = """Credits failed to load, please contact support if this error continues"""

        embed = discord.Embed(
            title="",
            description=content,
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Credits(bot))