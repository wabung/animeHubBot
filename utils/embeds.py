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