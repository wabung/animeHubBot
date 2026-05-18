"""
Information cog for anime queries using AniList GraphQL API.
Provides commands to search, discover, and get detailed information about anime.
"""

import discord
from discord import app_commands
from discord.ext import commands
from services import AniListService, BackendClient
from utils.embeds import base_embed, error_embed, Colors
from utils.embeds import search_embed, genre_embed, trending_embed
from utils.i18n import t
import logging

logger = logging.getLogger(__name__)

GENRES = [
    "Action", "Adventure", "Comedy", "Drama", "Fantasy", "Horror",
    "Mahou Shoujo", "Mecha", "Music", "Mystery", "Psychological",
    "Romance", "Sci-Fi", "Slice of Life", "Sports", "Supernatural", "Thriller"
]


# --- Views ---

class AnimePaginatedView(discord.ui.View):
    """Generic paginated view with previous/next buttons."""

    def __init__(self, author_id: int, anilist, fetch_fn, fetch_kwargs: dict, build_embed_fn, page_info: dict, lang: str = "en"):
        super().__init__(timeout=120)
        self.author_id = author_id
        self.anilist = anilist
        self.fetch_fn = fetch_fn
        self.fetch_kwargs = fetch_kwargs
        self.build_embed_fn = build_embed_fn
        self.lang = lang
        self.current_page = page_info["currentPage"]
        self.last_page = page_info["lastPage"]
        self._sync_buttons()

    def _sync_buttons(self):
        self.prev_button.disabled = self.current_page <= 1
        self.next_button.disabled = self.current_page >= self.last_page

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                embed=error_embed(t("error.navigate_only_author", self.lang), self.lang),
                ephemeral=True
            )
            return False
        return True

    async def _change_page(self, interaction: discord.Interaction, page: int):
        await interaction.response.defer()
        result = await self.fetch_fn(**self.fetch_kwargs, page=page)

        if not result or not result["Page"]["media"]:
            return

        page_info = result["Page"]["pageInfo"]
        self.current_page = page_info["currentPage"]
        self.last_page = page_info["lastPage"]
        self._sync_buttons()

        embed = self.build_embed_fn(result)
        await interaction.edit_original_response(embed=embed, view=self)

    @discord.ui.button(label="<", style=discord.ButtonStyle.secondary)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._change_page(interaction, self.current_page - 1)

    @discord.ui.button(label=">", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._change_page(interaction, self.current_page + 1)

    async def on_timeout(self):
        self.prev_button.disabled = True
        self.next_button.disabled = True


class GenreSelectView(discord.ui.View):
    """View with a genre dropdown that loads results and switches to paginated view."""

    def __init__(self, author_id: int, anilist, lang: str = "en"):
        super().__init__(timeout=60)
        self.author_id = author_id
        self.anilist = anilist
        self.lang = lang
        self.genre_select.placeholder = t("genre.placeholder", lang)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                embed=error_embed(t("error.menu_only_author", self.lang), self.lang),
                ephemeral=True
            )
            return False
        return True

    @discord.ui.select(
        placeholder="Select a genre...",
        options=[discord.SelectOption(label=g, value=g) for g in GENRES]
    )
    async def genre_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        selected_genre = select.values[0]
        await interaction.response.defer()

        result = await self.anilist.get_anime_by_genre([selected_genre], per_page=5)

        if not result or not result["Page"]["media"]:
            await interaction.edit_original_response(
                embed=error_embed(t("genre.no_results", self.lang, genre=selected_genre), self.lang),
                view=None
            )
            return

        embed, page_info = genre_embed(result, selected_genre, self.lang)

        paginated_view = AnimePaginatedView(
            author_id=self.author_id,
            anilist=self.anilist,
            fetch_fn=self.anilist.get_anime_by_genre,
            fetch_kwargs={"genres": [selected_genre], "per_page": 5},
            build_embed_fn=lambda r: genre_embed(r, selected_genre, self.lang)[0],
            page_info=page_info,
            lang=self.lang,
        )

        await interaction.edit_original_response(embed=embed, view=paginated_view)

    async def on_timeout(self):
        self.genre_select.disabled = True


# --- Cog ---

class Info(commands.Cog):
    """Anime information commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.anilist = AniListService()

    @property
    def backend(self) -> BackendClient:
        return self.bot.backend

    async def _track(self, ctx: commands.Context):
        """Register user if new and increment query counters. Fire-and-forget."""
        await self.backend.register_user(ctx.author.id, ctx.author.name)
        await self.backend.increment_user_queries(ctx.author.id)
        await self.backend.increment_queries(ctx.guild.id)

    @commands.hybrid_command(name="anime", description="Search for anime information")
    @app_commands.describe(query="Anime title to search for")
    async def search_anime(self, ctx: commands.Context, *, query: str):
        """Search for anime by title."""
        await ctx.defer()
        await self._track(ctx)
        lang = await self.bot.get_lang(ctx.guild.id)

        result = await self.anilist.search_anime(query, page=1, per_page=5)

        if not result or not result["Page"]["media"]:
            await ctx.send(embed=error_embed(t("anime.no_results", lang, query=query), lang))
            return

        embed, page_info = search_embed(result, query, lang)

        view = AnimePaginatedView(
            author_id=ctx.author.id,
            anilist=self.anilist,
            fetch_fn=self.anilist.search_anime,
            fetch_kwargs={"query": query, "per_page": 5},
            build_embed_fn=lambda r: search_embed(r, query, lang)[0],
            page_info=page_info,
            lang=lang,
        )

        await ctx.send(embed=embed, view=view)

    @commands.hybrid_command(name="anime_details", description="Get detailed information about an anime")
    @app_commands.describe(anime_id="AniList anime ID")
    async def anime_details(self, ctx: commands.Context, anime_id: int):
        """Get comprehensive details about a specific anime."""
        await ctx.defer()
        lang = await self.bot.get_lang(ctx.guild.id)

        details = await self.anilist.get_anime_details(anime_id)

        if not details or not details.get("Media"):
            await ctx.send(embed=error_embed(t("anime.not_found", lang, anime_id=anime_id), lang))
            return

        media = details["Media"]
        embed = base_embed(title=media["title"]["romaji"], color=Colors.PRIMARY)

        description = media.get("description", "")
        if description:
            description = description.replace("<br>", "\n")[:512] + "..."
        embed.description = description or t("anime.no_description", lang)

        start_date = media.get("startDate", {})
        end_date = media.get("endDate", {})
        unk = t("generic.unknown", lang)
        date_str = ""
        if start_date and start_date.get("year"):
            date_str = f"{start_date['day']}/{start_date['month']}/{start_date['year']}"
            if end_date and end_date.get("year"):
                date_str += f" {t('anime.date_to', lang)} {end_date['day']}/{end_date['month']}/{end_date['year']}"
            else:
                date_str += f" - {t('generic.ongoing', lang)}"

        studios = ", ".join([s["name"] for s in media.get("studios", {}).get("nodes", [])])

        embed.add_field(
            name=t("anime.field_production", lang),
            value=(
                f"**{t('anime.label_studio', lang)}:** {studios or unk}\n"
                f"**{t('anime.label_source', lang)}:** {media.get('source') or unk}\n"
                f"**{t('anime.label_season', lang)}:** {media.get('season') or unk} {media.get('seasonYear', '')}\n"
                f"**{t('anime.label_aired', lang)}:** {date_str or unk}"
            ),
            inline=False
        )
        embed.add_field(
            name=t("anime.field_stats", lang),
            value=(
                f"**{t('genre.episodes', lang)}:** {media.get('episodes') or '?'}\n"
                f"**{t('anime.label_duration', lang)}:** {media.get('duration', '?')} {t('anime.min_ep', lang)}\n"
                f"**{t('genre.score', lang)}:** {media.get('averageScore', '?')}/100\n"
                f"**{t('anime.label_popularity', lang)}:** #{media.get('popularity', '?')}"
            ),
            inline=True
        )
        embed.add_field(
            name=t("anime.field_status", lang),
            value=(
                f"**{t('anime.label_current', lang)}:** {media.get('status') or unk}\n"
                f"**{t('anime.label_genres', lang)}:** {', '.join(media.get('genres', []))}"
            ),
            inline=True
        )

        next_ep = media.get("nextAiringEpisode")
        if next_ep:
            embed.add_field(
                name=t("anime.field_next_ep", lang),
                value=t("anime.ep_airing", lang, ep=next_ep["episode"], time=next_ep["timeUntilAiring"]),
                inline=False
            )

        relations = media.get("relations", {}).get("edges", [])
        if relations:
            related_text = ""
            for edge in relations[:5]:
                rel_type = edge.get("relationType", unk)
                node = edge.get("node", {})
                related_text += f"**{rel_type}:** {node.get('title', {}).get('romaji', unk)}\n"
            if len(relations) > 5:
                related_text += t("anime.and_more", lang, n=len(relations) - 5)
            embed.add_field(name=t("anime.field_related", lang), value=related_text, inline=False)

        recommendations = media.get("recommendations", {}).get("edges", [])
        if recommendations:
            rec_text = ""
            for edge in recommendations[:3]:
                rec_node = edge.get("node", {}).get("mediaRecommendation", {})
                rating = edge.get("rating", 0)
                rec_text += f"**{rec_node.get('title', {}).get('romaji', unk)}** ({t('anime.match', lang, pct=rating)})\n"
            embed.add_field(name=t("anime.field_recs", lang), value=rec_text, inline=False)

        if media.get("coverImage", {}).get("large"):
            embed.set_image(url=media["coverImage"]["large"])
        if media.get("bannerImage"):
            embed.set_thumbnail(url=media["bannerImage"])

        await ctx.send(embed=embed)

    @commands.hybrid_command(name="characters", description="Get main characters from an anime")
    @app_commands.describe(
        anime_id="AniList anime ID",
        limit="Number of characters to show (default 5)"
    )
    async def anime_characters(self, ctx: commands.Context, anime_id: int, limit: int = 5):
        """Get main characters and voice actors from an anime."""
        await ctx.defer()
        lang = await self.bot.get_lang(ctx.guild.id)

        characters = await self.anilist.get_anime_characters(anime_id, per_page=limit)

        if not characters or not characters.get("Media"):
            await ctx.send(embed=error_embed(t("characters.no_media", lang, anime_id=anime_id), lang))
            return

        media = characters["Media"]
        char_edges = media.get("characters", {}).get("edges", [])

        if not char_edges:
            await ctx.send(embed=error_embed(t("characters.none", lang, title=media["title"]["romaji"]), lang))
            return

        embed = base_embed(
            title=t("characters.title", lang, title=media["title"]["romaji"]),
            color=Colors.COMMUNITY
        )

        for idx, edge in enumerate(char_edges[:limit], 1):
            char = edge.get("node", {})
            role = edge.get("role", "Unknown")
            voice_actors = edge.get("voiceActors", [])
            char_name = char.get("name", {}).get("full", "Unknown")
            char_info = f"**{t('characters.field_role', lang)}:** {role}"
            if voice_actors:
                va_names = ", ".join([va.get("name", {}).get("full", "Unknown") for va in voice_actors[:2]])
                char_info += f"\n**{t('characters.field_va', lang)}:** {va_names}"
            embed.add_field(name=f"{idx}. {char_name}", value=char_info, inline=False)

        await ctx.send(embed=embed)

    @commands.hybrid_command(name="genre", description="Browse anime by genre")
    async def anime_by_genre(self, ctx: commands.Context):
        """Select a genre from the dropdown to get anime recommendations."""
        await ctx.defer()
        lang = await self.bot.get_lang(ctx.guild.id)

        embed = base_embed(
            title=t("genre.browse_title", lang),
            description=t("genre.browse_desc", lang),
            color=Colors.GAMES
        )

        view = GenreSelectView(author_id=ctx.author.id, anilist=self.anilist, lang=lang)
        await ctx.send(embed=embed, view=view)

    @commands.hybrid_command(name="trending", description="See currently trending anime")
    async def trending_anime(self, ctx: commands.Context):
        """Get the most popular anime right now."""
        await ctx.defer()
        await self._track(ctx)
        lang = await self.bot.get_lang(ctx.guild.id)

        result = await self.anilist.get_trending_anime(per_page=10)

        if not result or not result["Page"]["media"]:
            await ctx.send(embed=error_embed(t("error.trending_failed", lang), lang))
            return

        embed, page_info = trending_embed(result, lang)

        view = AnimePaginatedView(
            author_id=ctx.author.id,
            anilist=self.anilist,
            fetch_fn=self.anilist.get_trending_anime,
            fetch_kwargs={"per_page": 10},
            build_embed_fn=lambda r: trending_embed(r, lang)[0],
            page_info=page_info,
            lang=lang,
        )

        await ctx.send(embed=embed, view=view)


async def setup(bot: commands.Bot):
    """Load the Info cog."""
    await bot.add_cog(Info(bot))
