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

    def __init__(self, author_id: int, anilist, fetch_fn, fetch_kwargs: dict, build_embed_fn, page_info: dict):
        super().__init__(timeout=120)
        self.author_id = author_id
        self.anilist = anilist
        self.fetch_fn = fetch_fn
        self.fetch_kwargs = fetch_kwargs
        self.build_embed_fn = build_embed_fn
        self.current_page = page_info["currentPage"]
        self.last_page = page_info["lastPage"]
        self._sync_buttons()

    def _sync_buttons(self):
        self.prev_button.disabled = self.current_page <= 1
        self.next_button.disabled = self.current_page >= self.last_page

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                embed=error_embed("Only the user who ran this command can navigate pages."),
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

    def __init__(self, author_id: int, anilist):
        super().__init__(timeout=60)
        self.author_id = author_id
        self.anilist = anilist

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                embed=error_embed("Only the user who ran this command can use this menu."),
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
                embed=error_embed(f"No anime found for genre '{selected_genre}'"),
                view=None
            )
            return

        embed, page_info = genre_embed(result, selected_genre)

        paginated_view = AnimePaginatedView(
            author_id=self.author_id,
            anilist=self.anilist,
            fetch_fn=self.anilist.get_anime_by_genre,
            fetch_kwargs={"genres": [selected_genre], "per_page": 5},
            build_embed_fn=lambda r: genre_embed(r, selected_genre)[0],
            page_info=page_info
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

        result = await self.anilist.search_anime(query, page=1, per_page=5)

        if not result or not result["Page"]["media"]:
            await ctx.send(embed=error_embed(f"No anime found for '{query}'"))
            return

        embed, page_info = search_embed(result, query)

        view = AnimePaginatedView(
            author_id=ctx.author.id,
            anilist=self.anilist,
            fetch_fn=self.anilist.search_anime,
            fetch_kwargs={"query": query, "per_page": 5},
            build_embed_fn=lambda r: search_embed(r, query)[0],
            page_info=page_info
        )

        await ctx.send(embed=embed, view=view)

    @commands.hybrid_command(name="anime_details", description="Get detailed information about an anime")
    @app_commands.describe(anime_id="AniList anime ID")
    async def anime_details(self, ctx: commands.Context, anime_id: int):
        """Get comprehensive details about a specific anime."""
        await ctx.defer()

        details = await self.anilist.get_anime_details(anime_id)

        if not details or not details.get("Media"):
            await ctx.send(embed=error_embed(f"Anime with ID {anime_id} not found"))
            return

        media = details["Media"]
        embed = base_embed(title=media["title"]["romaji"], color=Colors.PRIMARY)

        description = media.get("description", "")
        if description:
            description = description.replace("<br>", "\n")[:512] + "..."
        embed.description = description or "No description available"

        start_date = media.get("startDate", {})
        end_date = media.get("endDate", {})
        date_str = ""
        if start_date and start_date.get("year"):
            date_str = f"{start_date['day']}/{start_date['month']}/{start_date['year']}"
            if end_date and end_date.get("year"):
                date_str += f" to {end_date['day']}/{end_date['month']}/{end_date['year']}"
            else:
                date_str += " - Ongoing"

        studios = ", ".join([s["name"] for s in media.get("studios", {}).get("nodes", [])])

        embed.add_field(
            name="Production Info",
            value=(
                f"**Studio:** {studios or 'Unknown'}\n"
                f"**Source:** {media.get('source', 'Unknown')}\n"
                f"**Season:** {media.get('season', 'Unknown')} {media.get('seasonYear', '')}\n"
                f"**Aired:** {date_str or 'Unknown'}"
            ),
            inline=False
        )
        embed.add_field(
            name="Statistics",
            value=(
                f"**Episodes:** {media.get('episodes') or '?'}\n"
                f"**Duration:** {media.get('duration', '?')} min/ep\n"
                f"**Score:** {media.get('averageScore', '?')}/100\n"
                f"**Popularity:** #{media.get('popularity', '?')}"
            ),
            inline=True
        )
        embed.add_field(
            name="Status",
            value=(
                f"**Current:** {media.get('status', 'Unknown')}\n"
                f"**Genres:** {', '.join(media.get('genres', []))}"
            ),
            inline=True
        )

        next_ep = media.get("nextAiringEpisode")
        if next_ep:
            embed.add_field(
                name="Next Episode",
                value=f"Episode {next_ep['episode']} airing in {next_ep['timeUntilAiring']} seconds",
                inline=False
            )

        relations = media.get("relations", {}).get("edges", [])
        if relations:
            related_text = ""
            for edge in relations[:5]:
                rel_type = edge.get("relationType", "Related")
                node = edge.get("node", {})
                related_text += f"**{rel_type}:** {node.get('title', {}).get('romaji', 'Unknown')}\n"
            if len(relations) > 5:
                related_text += f"...and {len(relations) - 5} more"
            embed.add_field(name="Related Anime", value=related_text, inline=False)

        recommendations = media.get("recommendations", {}).get("edges", [])
        if recommendations:
            rec_text = ""
            for edge in recommendations[:3]:
                rec_node = edge.get("node", {}).get("mediaRecommendation", {})
                rating = edge.get("rating", 0)
                rec_text += f"**{rec_node.get('title', {}).get('romaji', 'Unknown')}** ({rating}% match)\n"
            embed.add_field(name="Recommendations", value=rec_text, inline=False)

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

        characters = await self.anilist.get_anime_characters(anime_id, per_page=limit)

        if not characters or not characters.get("Media"):
            await ctx.send(embed=error_embed(f"Could not fetch characters for anime ID {anime_id}"))
            return

        media = characters["Media"]
        char_edges = media.get("characters", {}).get("edges", [])

        if not char_edges:
            await ctx.send(embed=error_embed(f"No characters found for {media['title']['romaji']}"))
            return

        embed = base_embed(
            title=f"Characters from {media['title']['romaji']}",
            color=Colors.COMMUNITY
        )

        for idx, edge in enumerate(char_edges[:limit], 1):
            char = edge.get("node", {})
            role = edge.get("role", "Unknown")
            voice_actors = edge.get("voiceActors", [])
            char_name = char.get("name", {}).get("full", "Unknown")
            char_info = f"**Role:** {role}"
            if voice_actors:
                va_names = ", ".join([va.get("name", {}).get("full", "Unknown") for va in voice_actors[:2]])
                char_info += f"\n**Voice Actor (JP):** {va_names}"
            embed.add_field(name=f"{idx}. {char_name}", value=char_info, inline=False)

        await ctx.send(embed=embed)

    @commands.hybrid_command(name="genre", description="Browse anime by genre")
    async def anime_by_genre(self, ctx: commands.Context):
        """Select a genre from the dropdown to get anime recommendations."""
        await ctx.defer()

        embed = base_embed(
            title="Browse by Genre",
            description="Select a genre from the dropdown below to see the best anime in that category.",
            color=Colors.GAMES
        )

        view = GenreSelectView(author_id=ctx.author.id, anilist=self.anilist)
        await ctx.send(embed=embed, view=view)

    @commands.hybrid_command(name="trending", description="See currently trending anime")
    async def trending_anime(self, ctx: commands.Context):
        """Get the most popular anime right now."""
        await ctx.defer()
        await self._track(ctx)

        result = await self.anilist.get_trending_anime(per_page=10)

        if not result or not result["Page"]["media"]:
            await ctx.send(embed=error_embed("Could not fetch trending anime"))
            return

        embed, page_info = trending_embed(result)

        view = AnimePaginatedView(
            author_id=ctx.author.id,
            anilist=self.anilist,
            fetch_fn=self.anilist.get_trending_anime,
            fetch_kwargs={"per_page": 10},
            build_embed_fn=lambda r: trending_embed(r)[0],
            page_info=page_info
        )

        await ctx.send(embed=embed, view=view)


async def setup(bot: commands.Bot):
    """Load the Info cog."""
    await bot.add_cog(Info(bot))
