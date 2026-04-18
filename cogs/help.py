import discord
from discord import app_commands
from discord.ext import commands
from utils.embeds import base_embed, error_embed, Colors


class Help(commands.Cog, name="❓ Help"):
    """Help command for the bot."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name='help', aliases=['ayuda', 'h'], description='Shows this help message.')
    @app_commands.describe(category='Optional category to filter commands (info, games, community, admin).')
    async def help(self, ctx: commands.Context, *, category: str = None):
        """
        Displays the available commands, optionally filtered by category.
        Usage: !help | !help info | !help games | !help community | !help admin
        """
        if category is None:
            # Main menu
            embed = base_embed(
                title="🎌 AnimeHub Bot — Commands",
                description="Use `!help <category>` to view commands for each section.",
                color=Colors.PRIMARY
            )
            for cog_name, cog in self.bot.cogs.items():
                cmds = [c for c in cog.get_commands() if not c.hidden]
                if cmds:
                    embed.add_field(
                        name=cog_name,
                        value=", ".join(f"`!{c.name}`" for c in cmds),
                        inline=False
                    )
            embed.set_footer(text="AnimeHub Bot 🎌 | !help <category> for more details")
            await ctx.send(embed=embed)
            return

        # Search for the specified category
        specified_cog = None
        for cog_name, cog in self.bot.cogs.items():
            if category.lower() in cog_name.lower():
                specified_cog = cog
                cog_title = cog_name
                break

        if not specified_cog:
            await ctx.send(embed=error_embed(
                f"Category `{category}` not found.\n"
                "Available categories: `info`, `games`, `community`, `admin`"
            ))
            return

        embed = base_embed(
            title=f"Commands — {cog_title}",
            description=specified_cog.__doc__ or "No description available.",
            color=Colors.INFO
        )
        for cmd in specified_cog.get_commands():
            if not cmd.hidden:
                embed.add_field(
                    name=f"`!{cmd.name}`",
                    value=cmd.help or "No description available.",
                    inline=False
                )
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Help(bot))