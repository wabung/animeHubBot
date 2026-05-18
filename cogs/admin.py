import discord
from discord.ext import commands
from discord import app_commands
from services import BackendClient
from utils.embeds import base_embed, success_embed, error_embed, Colors
from utils.i18n import t

_SUPPORTED_LANGS = {"en": "English", "es": "Español"}


class Admin(commands.Cog, name="⚙️ Admin"):
    """Commands for admin functionality. Requires administrator permissions."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @property
    def backend(self) -> BackendClient:
        return self.bot.backend

    async def cog_check(self, ctx: commands.Context) -> bool:
        if not ctx.author.guild_permissions.administrator:
            lang = await self.bot.get_lang(ctx.guild.id)
            await ctx.send(embed=error_embed(t("error.admin_only", lang), lang))
            return False
        return True

    @commands.hybrid_command(name="config", description="Display the bot configuration for this server.")
    async def config(self, ctx: commands.Context):
        """Show the current server configuration stored in the database."""
        await ctx.defer()
        lang = await self.bot.get_lang(ctx.guild.id)

        guild_config = await self.backend.get_guild_config(ctx.guild.id)

        embed = base_embed(title=t("config.title", lang, guild=ctx.guild.name), color=Colors.ADMIN)

        if guild_config:
            not_set = t("config.not_set", lang)
            games_ch = f"<#{guild_config['games_channel_id']}>" if guild_config.get("games_channel_id") else not_set
            polls_ch = f"<#{guild_config['polls_channel_id']}>" if guild_config.get("polls_channel_id") else not_set
            embed.add_field(name=t("config.field_prefix",        lang), value=f"`{guild_config['prefix']}`", inline=True)
            embed.add_field(name=t("config.field_language",      lang), value=guild_config["language"],      inline=True)
            embed.add_field(name=t("config.field_games_channel", lang), value=games_ch,                      inline=True)
            embed.add_field(name=t("config.field_polls_channel", lang), value=polls_ch,                      inline=True)
        else:
            embed.description = t("config.no_config", lang)

        embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="setchannel", description="Set the channel for polls or games.")
    @app_commands.describe(tipo="Channel type: polls or games", channel="The channel to assign")
    async def setchannel(self, ctx: commands.Context, tipo: str, channel: discord.TextChannel):
        """Persist a channel assignment for a bot function to the database."""
        lang = await self.bot.get_lang(ctx.guild.id)

        if tipo.lower() not in ("polls", "games"):
            await ctx.send(embed=error_embed(t("error.invalid_channel_type", lang), lang))
            return

        await ctx.defer()

        field = "games_channel_id" if tipo == "games" else "polls_channel_id"
        result = await self.backend.update_guild_config(ctx.guild.id, **{field: channel.id})

        if result:
            await ctx.send(embed=success_embed(t("setchannel.success", lang, tipo=tipo, channel=channel.mention), lang))
        else:
            await ctx.send(embed=error_embed(t("error.config_save_failed", lang), lang))

    @commands.hybrid_command(name="setlang", description="Set the server language (en / es).")
    @app_commands.describe(language="Language: English or Español")
    @app_commands.choices(language=[
        app_commands.Choice(name="English", value="en"),
        app_commands.Choice(name="Español", value="es"),
    ])
    async def setlang(self, ctx: commands.Context, language: str):
        """Switch the bot language for this server."""
        await ctx.defer()
        lang = await self.bot.get_lang(ctx.guild.id)

        if language not in _SUPPORTED_LANGS:
            await ctx.send(embed=error_embed(t("setlang.invalid", lang), lang))
            return

        result = await self.backend.update_guild_config(ctx.guild.id, language=language)

        if result:
            self.bot.set_lang(ctx.guild.id, language)
            await ctx.send(embed=success_embed(t("setlang.success", language, name=_SUPPORTED_LANGS[language]), language))
        else:
            await ctx.send(embed=error_embed(t("error.config_save_failed", lang), lang))

    @commands.hybrid_command(name="stats", description="Display community usage statistics for this server.")
    async def stats(self, ctx: commands.Context):
        """Show aggregated bot usage stats from the database."""
        await ctx.defer()
        lang = await self.bot.get_lang(ctx.guild.id)

        community_stats = await self.backend.get_stats(ctx.guild.id)

        embed = base_embed(title=t("stats.title", lang, guild=ctx.guild.name), color=Colors.ADMIN)
        embed.add_field(name=t("stats.field_members",  lang), value=ctx.guild.member_count,  inline=True)
        embed.add_field(name=t("stats.field_channels", lang), value=len(ctx.guild.channels), inline=True)

        if community_stats:
            embed.add_field(name=t("stats.field_anime_queries",  lang), value=community_stats["anime_queries"],      inline=True)
            embed.add_field(name=t("stats.field_trivia_games",   lang), value=community_stats["trivia_games_played"], inline=True)
            embed.add_field(name=t("stats.field_active_users",   lang), value=community_stats["active_users"],        inline=True)
        else:
            embed.add_field(name=t("stats.field_anime_queries",  lang), value="0", inline=True)
            embed.add_field(name=t("stats.field_trivia_games",   lang), value="0", inline=True)
            embed.add_field(name=t("stats.field_active_users",   lang), value="0", inline=True)

        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))
