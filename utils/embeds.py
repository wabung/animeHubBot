import discord
from datetime import datetime
from utils.i18n import t

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
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.now(datetime.now().astimezone().tzinfo)
    )
    embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)

    if author:
        embed.set_author(
            name=author.display_name,
            icon_url=author.display_avatar.url
        )
    return embed


def success_embed(description: str, lang: str = "en", title: str = None) -> discord.Embed:
    return base_embed(title=title or t("generic.success", lang), description=description, color=Colors.SUCCESS)


def error_embed(description: str, lang: str = "en", title: str = None) -> discord.Embed:
    return base_embed(title=title or t("generic.error", lang), description=description, color=Colors.ERROR)


def info_embed(description: str, lang: str = "en", title: str = None) -> discord.Embed:
    return base_embed(title=title or t("generic.info", lang), description=description, color=Colors.INFO)


def warning_embed(description: str, lang: str = "en", title: str = None) -> discord.Embed:
    return base_embed(title=title or t("generic.warning", lang), description=description, color=Colors.WARNING)


# --- Anime list embed builders ---

def search_embed(result: dict, query: str, lang: str = "en") -> tuple[discord.Embed, dict]:
    """Build embed for anime search results."""
    media_list = result["Page"]["media"]
    page_info = result["Page"]["pageInfo"]
    main_anime = media_list[0]

    embed = base_embed(title=t("search.title", lang, query=query), color=Colors.INFO)

    title_text = main_anime["title"]["romaji"]
    if main_anime["title"]["english"]:
        title_text += f" ({main_anime['title']['english']})"

    description = main_anime.get("description") or t("search.no_description", lang)
    description = description.replace("<br>", "\n")[:256] + "..."

    embed.add_field(name=f"1. {title_text}", value=description, inline=False)
    embed.add_field(
        name=t("search.field_details", lang),
        value=(
            f"**ID:** {main_anime['id']}\n"
            f"**{t('genre.episodes', lang)}:** {main_anime['episodes'] or 'Unknown'}\n"
            f"**{t('anime.field_status', lang)}:** {main_anime['status']}\n"
            f"**{t('genre.score', lang)}:** {main_anime['averageScore']}/100\n"
            f"**{t('anime.field_status', lang)}:** {', '.join(main_anime['genres'])}"
        ),
        inline=False
    )

    if len(media_list) > 1:
        other_results = ""
        for idx, anime in enumerate(media_list[1:], 2):
            other_results += (
                f"**{idx}. {anime['title']['romaji']}**\n"
                f"{t('genre.score', lang)}: {anime['averageScore']}/100 | "
                f"{t('genre.episodes', lang)}: {anime['episodes'] or 'TBA'}\n"
            )
        embed.add_field(name=t("search.field_other", lang), value=other_results, inline=False)

    embed.set_footer(
        text=t("search.footer", lang, page=page_info["currentPage"], last=page_info["lastPage"], total=page_info["total"])
    )
    if main_anime["coverImage"]["large"]:
        embed.set_image(url=main_anime["coverImage"]["large"])

    return embed, page_info


def genre_embed(result: dict, genre: str, lang: str = "en") -> tuple[discord.Embed, dict]:
    """Build embed for genre-filtered anime results."""
    media_list = result["Page"]["media"]
    page_info = result["Page"]["pageInfo"]

    embed = base_embed(title=t("genre.title", lang, genre=genre), color=Colors.GAMES)

    per_page = 5
    start_idx = (page_info["currentPage"] - 1) * per_page + 1
    anime_list = ""
    for idx, anime in enumerate(media_list, start_idx):
        anime_list += (
            f"**{idx}. {anime['title']['romaji']}**\n"
            f"{t('genre.score', lang)}: {anime['averageScore']}/100 | "
            f"{t('genre.episodes', lang)}: {anime['episodes'] or 'TBA'}\n"
            f"{', '.join(anime['genres'][:2])}\n\n"
        )

    embed.description = anime_list
    embed.set_footer(
        text=t("genre.footer", lang, page=page_info["currentPage"], last=page_info["lastPage"], total=page_info["total"])
    )
    return embed, page_info


def trivia_question_embed(question, num: int, total: int, lang: str = "en") -> discord.Embed:
    """Build embed for an active trivia question."""
    labels = ["A", "B", "C", "D"]
    options_text = "\n".join(
        f"**{labels[i]}.** {opt}" for i, opt in enumerate(question.options)
    )

    title = t("trivia.question_title", lang, num=num, total=total)
    if question.character_name:
        title += f" — {t('trivia.question_who_suffix', lang, name=question.character_name)}"

    embed = base_embed(
        title=title,
        description=f"{question.question}\n\n{options_text}",
        color=Colors.GAMES
    )
    embed.set_footer(text=t("trivia.footer_points", lang, points=question.points))

    if question.image:
        embed.set_image(url=question.image)

    return embed


def trivia_answered_embed(question, num: int, total: int, is_correct: bool, responder: str, lang: str = "en") -> discord.Embed:
    """Build embed shown immediately after a question is answered."""
    labels = ["A", "B", "C", "D"]
    options_text = ""
    for i, opt in enumerate(question.options):
        if i == question.correct_index:
            options_text += f"**{labels[i]}.** ✅ {opt}\n"
        else:
            options_text += f"**{labels[i]}.** {opt}\n"

    result_line = (
        t("trivia.correct", lang, responder=responder, points=question.points)
        if is_correct
        else t("trivia.wrong", lang, responder=responder)
    )

    embed = base_embed(
        title=t("trivia.answered_title", lang, num=num, total=total),
        description=f"{question.question}\n\n{options_text}\n{result_line}",
        color=Colors.SUCCESS if is_correct else Colors.ERROR,
    )

    if question.image:
        embed.set_image(url=question.image)

    return embed


def trivia_timeout_embed(question, num: int, total: int, lang: str = "en") -> discord.Embed:
    """Build embed shown when nobody answers in time."""
    labels = ["A", "B", "C", "D"]
    options_text = ""
    for i, opt in enumerate(question.options):
        if i == question.correct_index:
            options_text += f"**{labels[i]}.** ✅ {opt}\n"
        else:
            options_text += f"**{labels[i]}.** {opt}\n"

    embed = base_embed(
        title=t("trivia.timeout_title", lang, num=num, total=total),
        description=f"{question.question}\n\n{options_text}\n{t('trivia.timeout_nobody', lang)}",
        color=Colors.WARNING,
    )

    if question.image:
        embed.set_image(url=question.image)

    return embed


def trivia_results_embed(scores: dict, total_questions: int, lang: str = "en") -> discord.Embed:
    """Build the final results embed at the end of a trivia session."""
    embed = base_embed(title=t("trivia.results_title", lang), color=Colors.PRIMARY)

    if not scores:
        embed.description = t("trivia.no_scores", lang)
        return embed

    sorted_scores = sorted(scores.values(), key=lambda s: s["points"], reverse=True)

    medals = ["🥇", "🥈", "🥉"]
    ranking_text = ""
    for idx, entry in enumerate(sorted_scores):
        prefix = medals[idx] if idx < 3 else f"**#{idx + 1}**"
        ranking_text += f"{prefix} **{entry['name']}** — {entry['points']} pts\n"

    embed.description = ranking_text
    embed.set_footer(text=t("trivia.footer_questions", lang, total=total_questions))
    return embed


def trending_embed(result: dict, lang: str = "en") -> tuple[discord.Embed, dict]:
    """Build embed for trending anime results."""
    media_list = result["Page"]["media"]
    page_info = result["Page"]["pageInfo"]

    embed = base_embed(title=t("trending.title", lang), color=Colors.WARNING)

    offset = (page_info["currentPage"] - 1) * 10
    trending_text = ""
    for idx, anime in enumerate(media_list, 1):
        trending_text += (
            f"**#{offset + idx}** {anime['title']['romaji']}\n"
            f"{t('trending.trending', lang)}: {anime['trending']} | "
            f"{t('trending.score', lang)}: {anime['averageScore']}/100\n\n"
        )

    embed.description = trending_text
    embed.set_footer(
        text=t("trending.footer", lang, page=page_info["currentPage"], last=page_info["lastPage"])
    )
    return embed, page_info
