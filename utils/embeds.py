import discord
from datetime import datetime

# Color palette for embeds
class Colors:
    PRIMARY   = 0xE94560
    SUCCESS   = 0x57F287
    ERROR     = 0xFF4757
    WARNING   = 0xFEE75C
    INFO      = 0x5865F2
    COMMUNITY = 0xFF6B6B
    GAMES     = 0xF9CA24
    ADMIN     = 0x6C5CE7

FOOTER_TEXT = "AnimeHub Bot 🎌"
FOOTER_ICON = None  # I won't be using an icon for the moment as I don't have one ready.


def base_embed(
    title: str = None,
    description: str = None,
    color: int = Colors.PRIMARY,
    author: discord.Member = None,
) -> discord.Embed:
    """
    Create a base embed with standard footer and timestamp.
    
    Usage:
        embed = base_embed("Title", "Description", Colors.SUCCESS)
    """
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.now(datetime.now().astimezone().tzinfo)  # Local timezone
    )
    embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)

    if author:
        embed.set_author(
            name=author.display_name,
            icon_url=author.display_avatar.url
        )
    return embed


def success_embed(description: str, title: str = "✅ Success") -> discord.Embed:
    return base_embed(title=title, description=description, color=Colors.SUCCESS)


def error_embed(description: str, title: str = "❌ Error") -> discord.Embed:
    return base_embed(title=title, description=description, color=Colors.ERROR)


def info_embed(description: str, title: str = "ℹ️ Info") -> discord.Embed:
    return base_embed(title=title, description=description, color=Colors.INFO)


def warning_embed(description: str, title: str = "⚠️ Warning") -> discord.Embed:
    return base_embed(title=title, description=description, color=Colors.WARNING)


# --- Anime list embed builders ---

def search_embed(result: dict, query: str) -> tuple[discord.Embed, dict]:
    """Build embed for anime search results."""
    media_list = result["Page"]["media"]
    page_info = result["Page"]["pageInfo"]
    main_anime = media_list[0]

    embed = base_embed(title=f"Search Results for '{query}'", color=Colors.INFO)

    title_text = main_anime["title"]["romaji"]
    if main_anime["title"]["english"]:
        title_text += f" ({main_anime['title']['english']})"

    description = main_anime.get("description") or "No description available"
    description = description.replace("<br>", "\n")[:256] + "..."

    embed.add_field(name=f"1. {title_text}", value=description, inline=False)
    embed.add_field(
        name="Details",
        value=(
            f"**ID:** {main_anime['id']}\n"
            f"**Episodes:** {main_anime['episodes'] or 'Unknown'}\n"
            f"**Status:** {main_anime['status']}\n"
            f"**Score:** {main_anime['averageScore']}/100\n"
            f"**Genres:** {', '.join(main_anime['genres'])}"
        ),
        inline=False
    )

    if len(media_list) > 1:
        other_results = ""
        for idx, anime in enumerate(media_list[1:], 2):
            other_results += (
                f"**{idx}. {anime['title']['romaji']}**\n"
                f"Score: {anime['averageScore']}/100 | "
                f"Episodes: {anime['episodes'] or 'TBA'}\n"
            )
        embed.add_field(name="Other Results", value=other_results, inline=False)

    embed.set_footer(
        text=f"Page {page_info['currentPage']}/{page_info['lastPage']} ({page_info['total']} total)"
    )
    if main_anime["coverImage"]["large"]:
        embed.set_image(url=main_anime["coverImage"]["large"])

    return embed, page_info


def genre_embed(result: dict, genre: str) -> tuple[discord.Embed, dict]:
    """Build embed for genre-filtered anime results."""
    media_list = result["Page"]["media"]
    page_info = result["Page"]["pageInfo"]

    embed = base_embed(title=f"Best {genre} Anime", color=Colors.GAMES)

    per_page = 5
    start_idx = (page_info["currentPage"] - 1) * per_page + 1
    anime_list = ""
    for idx, anime in enumerate(media_list, start_idx):
        anime_list += (
            f"**{idx}. {anime['title']['romaji']}**\n"
            f"Score: {anime['averageScore']}/100 | "
            f"Episodes: {anime['episodes'] or 'TBA'}\n"
            f"Genres: {', '.join(anime['genres'][:2])}\n\n"
        )

    embed.description = anime_list
    embed.set_footer(
        text=f"Page {page_info['currentPage']}/{page_info['lastPage']} ({page_info['total']} total)"
    )
    return embed, page_info


def trivia_question_embed(question, num: int, total: int) -> discord.Embed:
    """Build embed for an active trivia question."""
    labels = ["A", "B", "C", "D"]
    options_text = "\n".join(
        f"**{labels[i]}.** {opt}" for i, opt in enumerate(question.options)
    )

    title = f"Question {num}/{total}"
    if question.character_name:
        title += f" — Who is **{question.character_name}**?"

    embed = base_embed(
        title=title,
        description=f"{question.question}\n\n{options_text}",
        color=Colors.GAMES
    )
    embed.set_footer(text=f"Points: {question.points} | Select an answer below")

    if question.image:
        embed.set_image(url=question.image)

    return embed


def trivia_answered_embed(question, num: int, total: int, is_correct: bool, responder: str) -> discord.Embed:
    """Build embed shown immediately after a question is answered."""
    labels = ["A", "B", "C", "D"]
    options_text = ""
    for i, opt in enumerate(question.options):
        if i == question.correct_index:
            options_text += f"**{labels[i]}.** ✅ {opt}\n"
        else:
            options_text += f"**{labels[i]}.** {opt}\n"

    result_line = (
        f"✅ **{responder}** got it right! **+{question.points} pts**"
        if is_correct
        else f"❌ **{responder}** answered wrong. No points awarded."
    )

    embed = base_embed(
        title=f"Question {num}/{total} — Answered",
        description=f"{question.question}\n\n{options_text}\n{result_line}",
        color=Colors.SUCCESS if is_correct else Colors.ERROR,
    )

    if question.image:
        embed.set_image(url=question.image)

    return embed


def trivia_timeout_embed(question, num: int, total: int) -> discord.Embed:
    """Build embed shown when nobody answers in time."""
    labels = ["A", "B", "C", "D"]
    options_text = ""
    for i, opt in enumerate(question.options):
        if i == question.correct_index:
            options_text += f"**{labels[i]}.** ✅ {opt}\n"
        else:
            options_text += f"**{labels[i]}.** {opt}\n"

    embed = base_embed(
        title=f"Question {num}/{total} — Time's up!",
        description=f"{question.question}\n\n{options_text}\n⏰ Nobody answered in time.",
        color=Colors.WARNING,
    )

    if question.image:
        embed.set_image(url=question.image)

    return embed


def trivia_results_embed(scores: dict, total_questions: int) -> discord.Embed:
    """Build the final results embed at the end of a trivia session."""
    embed = base_embed(title="Trivia Results", color=Colors.PRIMARY)

    if not scores:
        embed.description = "Nobody scored any points this session!"
        return embed

    sorted_scores = sorted(scores.values(), key=lambda s: s["points"], reverse=True)

    medals = ["🥇", "🥈", "🥉"]
    ranking_text = ""
    for idx, entry in enumerate(sorted_scores):
        prefix = medals[idx] if idx < 3 else f"**#{idx + 1}**"
        ranking_text += f"{prefix} **{entry['name']}** — {entry['points']} pts\n"

    embed.description = ranking_text
    embed.set_footer(text=f"Based on {total_questions} questions")
    return embed


def trending_embed(result: dict) -> tuple[discord.Embed, dict]:
    """Build embed for trending anime results."""
    media_list = result["Page"]["media"]
    page_info = result["Page"]["pageInfo"]

    embed = base_embed(title="Trending Anime", color=Colors.WARNING)

    offset = (page_info["currentPage"] - 1) * 10
    trending_text = ""
    for idx, anime in enumerate(media_list, 1):
        trending_text += (
            f"**#{offset + idx}** {anime['title']['romaji']}\n"
            f"Trending: {anime['trending']} | Score: {anime['averageScore']}/100\n\n"
        )

    embed.description = trending_text
    embed.set_footer(
        text=f"Page {page_info['currentPage']}/{page_info['lastPage']}"
    )
    return embed, page_info