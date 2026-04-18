import discord
from discord.ext import commands
from discord import app_commands
from utils.embeds import base_embed, success_embed, error_embed, Colors


class Admin(commands.Cog, name="⚙️ Admin"):
    """Commands for admin functionality. Requires administrator permissions."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_check(self, ctx: commands.Context) -> bool:
        """All commands in this cog require administrator permissions."""
        if not ctx.author.guild_permissions.administrator:
            await ctx.send(embed=error_embed("You need **administrator** permissions to use this command."))
            return False
        return True

    @commands.hybrid_command(name='config', help='Displays the current bot configuration for this server.')
    async def config(self, ctx):
        """
        Displays the current bot configuration for this server.
        Usage: !config
        """
        embed = base_embed(
            title=f"⚙️ Configuration — {ctx.guild.name}",
            color=Colors.ADMIN
        )
        embed.add_field(name="Prefix", value="`!`", inline=True)
        embed.add_field(name="Language", value="Spanish", inline=True)
        embed.add_field(name="Polls Channel", value="Not configured", inline=True)
        embed.add_field(name="Games Channel", value="Not configured", inline=True)
        embed.add_field(
            name="ℹ️ Note",
            value="Persistent configuration in the database will be available soon.",
            inline=False
        )
        embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='setchannel', help='Sets the channel for polls or games.')
    async def setchannel(self, ctx, tipo: str, channel: discord.TextChannel):
        """
        Sets a channel for a specific bot function.
        Usage: !setchannel polls #polls-channel
               !setchannel games #games-channel

        (this will be saved in the database soon, for now it's just a confirmation message)
        """
        tipos_validos = ["polls", "games"]
        if tipo.lower() not in tipos_validos:
            await ctx.send(embed=error_embed(
                f"Invalid type. Use: `{', '.join(tipos_validos)}`"
            ))
            return

        embed = success_embed(
            f"Channel for **{tipo}** set to {channel.mention}.\n"
            "⚙️ This will be saved in the database soon."
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='stats', help='Displays usage statistics of the bot in the server.')
    async def stats(self, ctx):
        """
        Displays usage statistics of the bot in the server.
        Usage: !stats
        
        (When there is a database, real usage statistics of the bot will be displayed, for now only server data)
        """
        embed = base_embed(
            title=f"📊 Statistics — {ctx.guild.name}",
            color=Colors.ADMIN
        )
        embed.add_field(name="Members", value=ctx.guild.member_count, inline=True)
        embed.add_field(name="Channels", value=len(ctx.guild.channels), inline=True)
        embed.add_field(name="Anime Queries", value="⚙️ DB Pending", inline=True)
        embed.add_field(name="Trivia Games", value="⚙️ DB Pending", inline=True)
        embed.add_field(name="Polls Created", value="⚙️ DB Pending", inline=True)
        await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))