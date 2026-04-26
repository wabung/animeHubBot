"""
Information cog for anime queries using AniList GraphQL API.
Provides commands to search, discover, and get detailed information about anime.
"""

import discord
from discord import app_commands
from discord.ext import commands
from services import AniListService
from utils.embeds import base_embed, error_embed, Colors
import logging

logger = logging.getLogger(__name__)


class Info(commands.Cog):
    """Anime information commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.anilist = AniListService()

    @commands.hybrid_command(name="anime", description="Search for anime information")
    @app_commands.describe(
        query="Anime title to search for",
        page="Page number for results (default 1)"
    )
    async def search_anime(
        self,
        ctx: commands.Context,
        *,
        query: str,
        page: int = 1
    ):
        """Search for anime by title."""
        await ctx.defer()

        result = await self.anilist.search_anime(query, page=page, per_page=5)

        if not result or not result["Page"]["media"]:
            await ctx.send(
                embed=error_embed(f"No anime found for '{query}'")
            )
            return

        media_list = result["Page"]["media"]
        page_info = result["Page"]["pageInfo"]

        # Create embed with first result prominently
        main_anime = media_list[0]
        embed = base_embed(
            title=f"Search Results for '{query}'",
            color=Colors.INFO
        )

        # Main result
        title_text = main_anime["title"]["romaji"]
        if main_anime["title"]["english"]:
            title_text += f" ({main_anime['title']['english']})"

        description = main_anime.get("description", "No description available")
        if description:
            description = description.replace("<br>", "\n")[:256] + "..."
        else:
            description = "No description available"

        embed.add_field(
            name=f"1️⃣ {title_text}",
            value=description,
            inline=False
        )
        embed.add_field(
            name="Details",
            value=(
                f"**ID:** {main_anime['id']}\n"
                f"**Episodes:** {main_anime['episodes'] or 'Unknown'}\n"
                f"**Status:** {main_anime['status']}\n"
                f"**Score:** ⭐ {main_anime['averageScore']}/100\n"
                f"**Genres:** {', '.join(main_anime['genres'])}"
            ),
            inline=False
        )

        # Other results
        if len(media_list) > 1:
            other_results = ""
            for idx, anime in enumerate(media_list[1:], 2):
                other_results += (
                    f"**{idx}. {anime['title']['romaji']}**\n"
                    f"Score: ⭐ {anime['averageScore']}/100 | "
                    f"Episodes: {anime['episodes'] or 'TBA'}\n"
                )
            embed.add_field(name="Other Results", value=other_results, inline=False)

        # Pagination info
        embed.set_footer(
            text=f"Page {page_info['currentPage']}/{page_info['lastPage']} "
                 f"({page_info['total']} total anime)"
        )

        if main_anime["coverImage"]["large"]:
            embed.set_image(url=main_anime["coverImage"]["large"])

        await ctx.send(embed=embed)

    @commands.hybrid_command(name="anime_details", description="Get detailed information about an anime")
    @app_commands.describe(anime_id="AniList anime ID")
    async def anime_details(
        self,
        ctx: commands.Context,
        anime_id: int
    ):
        """Get comprehensive details about a specific anime."""
        await ctx.defer()

        details = await self.anilist.get_anime_details(anime_id)

        if not details or not details.get("Media"):
            await ctx.send(
                embed=error_embed(f"Anime with ID {anime_id} not found")
            )
            return

        media = details["Media"]
        embed = base_embed(
            title=media["title"]["romaji"],
            color=Colors.PRIMARY
        )

        # Basic info
        description = media.get("description", "")
        if description:
            description = description.replace("<br>", "\n")[:512] + "..."
        embed.description = description or "No description available"

        # Air dates
        start_date = media.get("startDate", {})
        end_date = media.get("endDate", {})
        date_str = ""
        if start_date and start_date.get("year"):
            date_str = f"{start_date['day']}/{start_date['month']}/{start_date['year']}"
            if end_date and end_date.get("year"):
                date_str += f" to {end_date['day']}/{end_date['month']}/{end_date['year']}"
            else:
                date_str += " - Ongoing"

        # Main details
        studios = ", ".join([s["name"] for s in media.get("studios", {}).get("nodes", [])])

        embed.add_field(
            name="📺 Production Info",
            value=(
                f"**Studio:** {studios or 'Unknown'}\n"
                f"**Source:** {media.get('source', 'Unknown')}\n"
                f"**Season:** {media.get('season', 'Unknown')} {media.get('seasonYear', '')}\n"
                f"**Aired:** {date_str or 'Unknown'}"
            ),
            inline=False
        )

        embed.add_field(
            name="🎬 Statistics",
            value=(
                f"**Episodes:** {media.get('episodes') or '?'}\n"
                f"**Duration:** {media.get('duration', '?')} min/ep\n"
                f"**Score:** ⭐ {media.get('averageScore', '?')}/100\n"
                f"**Popularity:** #{media.get('popularity', '?')}"
            ),
            inline=True
        )

        embed.add_field(
            name="📊 Status",
            value=(
                f"**Current:** {media.get('status', 'Unknown')}\n"
                f"**Genres:** {', '.join(media.get('genres', []))}"
            ),
            inline=True
        )

        # Next airing episode
        next_ep = media.get("nextAiringEpisode")
        if next_ep:
            embed.add_field(
                name="⏰ Next Episode",
                value=f"Episode {next_ep['episode']} airing in {next_ep['timeUntilAiring']} seconds",
                inline=False
            )

        # Relations
        relations = media.get("relations", {}).get("edges", [])
        if relations:
            related_text = ""
            for edge in relations[:5]:
                rel_type = edge.get("relationType", "Related")
                node = edge.get("node", {})
                related_text += f"**{rel_type}:** {node.get('title', {}).get('romaji', 'Unknown')}\n"
            if len(relations) > 5:
                related_text += f"...and {len(relations) - 5} more"
            embed.add_field(name="🔗 Related Anime", value=related_text, inline=False)

        # Recommendations
        recommendations = media.get("recommendations", {}).get("edges", [])
        if recommendations:
            rec_text = ""
            for edge in recommendations[:3]:
                rec_node = edge.get("node", {}).get("mediaRecommendation", {})
                rating = edge.get("rating", 0)
                rec_text += f"**{rec_node.get('title', {}).get('romaji', 'Unknown')}** ({rating}% match)\n"
            embed.add_field(name="💡 Recommendations", value=rec_text, inline=False)

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
    async def anime_characters(
        self,
        ctx: commands.Context,
        anime_id: int,
        limit: int = 5
    ):
        """Get main characters and voice actors from an anime."""
        await ctx.defer()

        characters = await self.anilist.get_anime_characters(anime_id, per_page=limit)

        if not characters or not characters.get("Media"):
            await ctx.send(
                embed=error_embed(f"Could not fetch characters for anime ID {anime_id}")
            )
            return

        media = characters["Media"]
        char_edges = media.get("characters", {}).get("edges", [])

        if not char_edges:
            await ctx.send(
                embed=error_embed(f"No characters found for {media['title']['romaji']}")
            )
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

    @commands.hybrid_command(name="genre", description="Get anime recommendations by genre")
    @app_commands.describe(
        genre="Anime genre (e.g., Action, Romance, Comedy)",
        min_score="Minimum score filter (0-100, default 0)"
    )
    async def anime_by_genre(
        self,
        ctx: commands.Context,
        genre: str,
        min_score: int = 0
    ):
        """Get anime recommendations filtered by genre."""
        await ctx.defer()

        result = await self.anilist.get_anime_by_genre(
            genres=[genre],
            per_page=5,
            min_score=min_score
        )

        if not result or not result["Page"]["media"]:
            await ctx.send(
                embed=error_embed(
                    f"No anime found in genre '{genre}' with score ≥ {min_score}"
                )
            )
            return

        media_list = result["Page"]["media"]
        page_info = result["Page"]["pageInfo"]

        embed = base_embed(
            title=f"Best {genre} Anime",
            color=Colors.GAMES
        )

        anime_list = ""
        for idx, anime in enumerate(media_list[:5], 1):
            anime_list += (
                f"**{idx}. {anime['title']['romaji']}**\n"
                f"Score: ⭐ {anime['averageScore']}/100 | "
                f"Episodes: {anime['episodes'] or 'TBA'}\n"
                f"Genres: {', '.join(anime['genres'][:2])}\n\n"
            )

        embed.description = anime_list
        embed.set_footer(
            text=f"Showing {len(media_list)} of {page_info['total']} results"
        )

        await ctx.send(embed=embed)

    @commands.hybrid_command(name="trending", description="See currently trending anime")
    async def trending_anime(self, ctx: commands.Context):
        """Get the most popular anime right now."""
        await ctx.defer()

        trending = await self.anilist.get_trending_anime(per_page=10)

        if not trending or not trending["Page"]["media"]:
            await ctx.send(
                embed=error_embed("Could not fetch trending anime")
            )
            return

        media_list = trending["Page"]["media"]
        embed = base_embed(
            title="🔥 Trending Anime",
            color=Colors.WARNING
        )

        trending_text = ""
        for idx, anime in enumerate(media_list[:10], 1):
            trending_text += (
                f"**#{idx}** {anime['title']['romaji']}\n"
                f"Trending: {anime['trending']} | "
                f"Score: ⭐ {anime['averageScore']}/100\n\n"
            )

        embed.description = trending_text

        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    """Load the Info cog."""
    await bot.add_cog(Info(bot))
