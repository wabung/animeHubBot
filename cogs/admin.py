import discord
from discord.ext import commands
from discord import app_commands
from services import BackendClient
from utils.embeds import base_embed, success_embed, error_embed, Colors


class Admin(commands.Cog, name="⚙️ Admin"):
    """Commands for admin functionality. Requires administrator permissions."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @property
    def backend(self) -> BackendClient:
        return self.bot.backend

    async def cog_check(self, ctx: commands.Context) -> bool:
        if not ctx.author.guild_permissions.administrator:
            await ctx.send(embed=error_embed("You need **administrator** permissions to use this command."))
            return False
        return True

    @commands.hybrid_command(name="config", description="Display the bot configuration for this server.")
    async def config(self, ctx: commands.Context):
        """Show the current server configuration stored in the database."""
        await ctx.defer()

        guild_config = await self.backend.get_guild_config(ctx.guild.id)

        embed = base_embed(title=f"⚙️ Configuration — {ctx.guild.name}", color=Colors.ADMIN)

        if guild_config:
            games_ch = f"<#{guild_config['games_channel_id']}>" if guild_config.get("games_channel_id") else "Not set"
            polls_ch = f"<#{guild_config['polls_channel_id']}>" if guild_config.get("polls_channel_id") else "Not set"
            embed.add_field(name="Prefix",         value=f"`{guild_config['prefix']}`", inline=True)
            embed.add_field(name="Language",       value=guild_config["language"],      inline=True)
            embed.add_field(name="Games Channel",  value=games_ch,                     inline=True)
            embed.add_field(name="Polls Channel",  value=polls_ch,                     inline=True)
        else:
            embed.description = "No configuration found for this server."

        embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="setchannel", description="Set the channel for polls or games.")
    @app_commands.describe(tipo="Channel type: polls or games", channel="The channel to assign")
    async def setchannel(self, ctx: commands.Context, tipo: str, channel: discord.TextChannel):
        """Persist a channel assignment for a bot function to the database."""
        if tipo.lower() not in ("polls", "games"):
            await ctx.send(embed=error_embed("Invalid type. Use: `polls` or `games`"))
            return

        await ctx.defer()

        field = "games_channel_id" if tipo == "games" else "polls_channel_id"
        result = await self.backend.update_guild_config(ctx.guild.id, **{field: channel.id})

        if result:
            await ctx.send(embed=success_embed(f"Channel for **{tipo}** set to {channel.mention}."))
        else:
            await ctx.send(embed=error_embed("Could not save the configuration. Is the backend running?"))

    @commands.hybrid_command(name="stats", description="Display community usage statistics for this server.")
    async def stats(self, ctx: commands.Context):
        """Show aggregated bot usage stats from the database."""
        await ctx.defer()

        community_stats = await self.backend.get_stats(ctx.guild.id)

        embed = base_embed(title=f"📊 Statistics — {ctx.guild.name}", color=Colors.ADMIN)
        embed.add_field(name="Members",  value=ctx.guild.member_count,  inline=True)
        embed.add_field(name="Channels", value=len(ctx.guild.channels), inline=True)

        if community_stats:
            embed.add_field(name="Anime Queries",  value=community_stats["anime_queries"],       inline=True)
            embed.add_field(name="Trivia Games",   value=community_stats["trivia_games_played"],  inline=True)
            embed.add_field(name="Active Users",   value=community_stats["active_users"],         inline=True)
        else:
            embed.add_field(name="Anime Queries",  value="0", inline=True)
            embed.add_field(name="Trivia Games",   value="0", inline=True)
            embed.add_field(name="Active Users",   value="0", inline=True)

        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))
