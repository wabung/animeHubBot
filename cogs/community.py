"""
Community cog — interactive polls for server members.
"""

import discord
from discord import app_commands
from discord.ext import commands
from services import BackendClient
from utils.embeds import error_embed, success_embed, poll_embed
from utils.i18n import t
import logging

logger = logging.getLogger(__name__)

_OPTION_LABELS = ["🇦", "🇧", "🇨", "🇩"]


class PollView(discord.ui.View):
    """Interactive vote buttons + close button for a poll."""

    def __init__(
        self,
        author: discord.Member,
        question: str,
        options: list[str],
        lang: str = "en",
    ):
        super().__init__(timeout=None)
        self.author = author
        self.question = question
        self.options = options
        self.lang = lang
        self.votes: dict[int, int] = {}  # user_id → option_index
        self.closed = False

        for idx, option in enumerate(options):
            btn = discord.ui.Button(
                label=f"{_OPTION_LABELS[idx]} {option}"[:80],
                style=discord.ButtonStyle.primary,
                custom_id=f"poll_opt_{idx}",
                row=idx // 2,
            )
            btn.callback = self._make_vote_callback(idx, option)
            self.add_item(btn)

        close_btn = discord.ui.Button(
            label=t("poll.close_btn", lang),
            style=discord.ButtonStyle.danger,
            custom_id="poll_close",
            row=2,
        )
        close_btn.callback = self._close_callback
        self.add_item(close_btn)

    def _make_vote_callback(self, idx: int, option: str):
        async def callback(interaction: discord.Interaction):
            if self.closed:
                await interaction.response.send_message(
                    embed=error_embed(t("poll.closed", self.lang), self.lang),
                    ephemeral=True,
                )
                return

            prev = self.votes.get(interaction.user.id)
            if prev == idx:
                await interaction.response.send_message(
                    embed=error_embed(t("poll.already_voted", self.lang, option=option), self.lang),
                    ephemeral=True,
                )
                return

            self.votes[interaction.user.id] = idx
            msg_key = "poll.vote_changed" if prev is not None else "poll.vote_registered"

            await interaction.response.send_message(
                embed=success_embed(t(msg_key, self.lang, option=option), self.lang),
                ephemeral=True,
            )
            embed = poll_embed(self.question, self.options, self.votes, self.lang, self.author)
            await interaction.message.edit(embed=embed)

        return callback

    async def _close_callback(self, interaction: discord.Interaction):
        is_author = interaction.user.id == self.author.id
        is_mod = interaction.user.guild_permissions.manage_messages
        if not is_author and not is_mod:
            await interaction.response.send_message(
                embed=error_embed(t("poll.close_no_permission", self.lang), self.lang),
                ephemeral=True,
            )
            return

        self.closed = True
        for child in self.children:
            child.disabled = True
        self.stop()

        embed = poll_embed(self.question, self.options, self.votes, self.lang, self.author, closed=True)
        await interaction.response.edit_message(embed=embed, view=self)


class Community(commands.Cog, name="🗳️ Community"):
    """Community engagement commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @property
    def backend(self) -> BackendClient:
        return self.bot.backend

    @commands.hybrid_command(name="poll", description="Create an interactive poll with up to 4 options.")
    @app_commands.describe(
        question="The poll question",
        option1="First option",
        option2="Second option",
        option3="Third option (optional)",
        option4="Fourth option (optional)",
    )
    async def poll(
        self,
        ctx: commands.Context,
        question: str,
        option1: str,
        option2: str,
        option3: str = None,
        option4: str = None,
    ):
        """Create a poll that server members can vote on with buttons."""
        await ctx.defer(ephemeral=True)
        lang = await self.bot.get_lang(ctx.guild.id)

        options = [o for o in [option1, option2, option3, option4] if o]

        guild_config = await self.backend.get_guild_config(ctx.guild.id)
        polls_channel_id = (guild_config or {}).get("polls_channel_id")

        target_channel = ctx.channel
        if polls_channel_id and polls_channel_id != ctx.channel.id:
            fetched = ctx.guild.get_channel(polls_channel_id)
            if fetched:
                target_channel = fetched

        embed = poll_embed(question, options, {}, lang, ctx.author)
        view = PollView(author=ctx.author, question=question, options=options, lang=lang)

        await target_channel.send(embed=embed, view=view)

        if target_channel != ctx.channel:
            await ctx.send(
                embed=success_embed(t("poll.sent_to", lang, channel=target_channel.mention), lang),
                ephemeral=True,
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(Community(bot))
