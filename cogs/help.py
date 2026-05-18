import discord
from discord import app_commands
from discord.ext import commands
from utils.embeds import base_embed, error_embed, Colors
from utils.i18n import t


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
        lang = await self.bot.get_lang(ctx.guild.id)

        if category is None:
            embed = base_embed(
                title=t("help.title", lang),
                description=t("help.description", lang),
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
            embed.set_footer(text=t("help.footer", lang))
            await ctx.send(embed=embed)
            return

        specified_cog = None
        for cog_name, cog in self.bot.cogs.items():
            if category.lower() in cog_name.lower():
                specified_cog = cog
                cog_title = cog_name
                break

        if not specified_cog:
            await ctx.send(embed=error_embed(
                t("help.category_not_found", lang, category=category),
                lang
            ))
            return

        embed = base_embed(
            title=t("help.cog_title", lang, cog_title=cog_title),
            description=specified_cog.__doc__ or t("help.no_description", lang),
            color=Colors.INFO
        )
        for cmd in specified_cog.get_commands():
            if not cmd.hidden:
                embed.add_field(
                    name=f"`!{cmd.name}`",
                    value=cmd.help or t("help.no_description", lang),
                    inline=False
                )
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Help(bot))
