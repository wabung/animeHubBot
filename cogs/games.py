"""
Games cog — anime trivia with dynamic questions from AniList.
"""

import asyncio
import discord
from discord import app_commands
from discord.ext import commands
from services import AniListService, TriviaGenerator, TriviaQuestion
from utils.embeds import (
    base_embed, error_embed, Colors,
    trivia_question_embed, trivia_answered_embed,
    trivia_timeout_embed, trivia_results_embed,
)
import logging

logger = logging.getLogger(__name__)

QUESTION_TIMEOUT = 20   # seconds to answer each question
NEXT_DELAY = 3          # seconds before advancing to the next question

# In-memory leaderboard: guild_id -> {user_id -> {"name": str, "points": int}}
_leaderboard: dict[int, dict[int, dict]] = {}


def _add_score(guild_id: int, user_id: int, display_name: str, points: int):
    """Add points to the global leaderboard."""
    guild_scores = _leaderboard.setdefault(guild_id, {})
    if user_id not in guild_scores:
        guild_scores[user_id] = {"name": display_name, "points": 0}
    guild_scores[user_id]["points"] += points
    guild_scores[user_id]["name"] = display_name


# --- Trivia session state ---

class TriviaSession:
    """Holds the state of a running trivia session for one message."""

    def __init__(
        self,
        guild_id: int,
        questions: list[TriviaQuestion],
        generator: TriviaGenerator,
    ):
        self.guild_id = guild_id
        self.questions = questions
        self.generator = generator
        self.current = 0
        self.scores: dict[int, dict] = {}
        self.message: discord.Message | None = None

    @property
    def current_question(self) -> TriviaQuestion:
        return self.questions[self.current]

    @property
    def total(self) -> int:
        return len(self.questions)

    def record_answer(self, user_id: int, display_name: str, points: int):
        if user_id not in self.scores:
            self.scores[user_id] = {"name": display_name, "points": 0}
        self.scores[user_id]["points"] += points
        self.scores[user_id]["name"] = display_name
        if points > 0:
            _add_score(self.guild_id, user_id, display_name, points)

    async def show_current(self):
        """Render the current question into the session message."""
        q = self.current_question
        embed = trivia_question_embed(q, self.current + 1, self.total)
        view = TriviaQuestionView(self)
        await self.message.edit(embed=embed, view=view)
        view.message = self.message

    async def advance(self):
        """Move to the next question or show results."""
        self.current += 1
        if self.current >= self.total:
            embed = trivia_results_embed(self.scores, self.total)
            await self.message.edit(embed=embed, view=None)
        else:
            await self.show_current()


# --- Question view ---

class TriviaQuestionView(discord.ui.View):
    """Displays A/B/C/D buttons for a single trivia question."""

    LABELS = ["A", "B", "C", "D"]

    def __init__(self, session: TriviaSession):
        super().__init__(timeout=QUESTION_TIMEOUT)
        self.session = session
        self.answered = False
        self.message: discord.Message | None = None

        for idx, option in enumerate(session.current_question.options):
            label = f"{self.LABELS[idx]}. {option}"
            button = discord.ui.Button(
                label=label[:80],
                style=discord.ButtonStyle.primary,
                custom_id=f"trivia_opt_{idx}",
                row=idx // 2,
            )
            button.callback = self._make_callback(idx)
            self.add_item(button)

    def _make_callback(self, chosen_index: int):
        async def callback(interaction: discord.Interaction):
            if self.answered:
                await interaction.response.send_message(
                    embed=error_embed("This question has already been answered."),
                    ephemeral=True,
                )
                return

            self.answered = True
            self.stop()

            q = self.session.current_question
            is_correct = chosen_index == q.correct_index
            points = q.points if is_correct else 0

            self.session.record_answer(
                interaction.user.id, interaction.user.display_name, points
            )

            self._apply_button_styles(chosen_index)

            embed = trivia_answered_embed(
                q, self.session.current + 1, self.session.total,
                is_correct, interaction.user.display_name,
            )
            await interaction.response.edit_message(embed=embed, view=self)

            await asyncio.sleep(NEXT_DELAY)
            await self.session.advance()

        return callback

    def _apply_button_styles(self, chosen_index: int):
        """Color buttons: green = correct, red = wrong choice, grey = rest."""
        q = self.session.current_question
        for item in self.children:
            if not isinstance(item, discord.ui.Button):
                continue
            idx = int(item.custom_id.split("_")[-1])
            item.disabled = True
            if idx == q.correct_index:
                item.style = discord.ButtonStyle.success
            elif idx == chosen_index:
                item.style = discord.ButtonStyle.danger
            else:
                item.style = discord.ButtonStyle.secondary

    async def on_timeout(self):
        if self.answered:
            return
        self.answered = True

        q = self.session.current_question
        for item in self.children:
            if not isinstance(item, discord.ui.Button):
                continue
            idx = int(item.custom_id.split("_")[-1])
            item.disabled = True
            item.style = (
                discord.ButtonStyle.success
                if idx == q.correct_index
                else discord.ButtonStyle.secondary
            )

        embed = trivia_timeout_embed(q, self.session.current + 1, self.session.total)
        if self.message:
            await self.message.edit(embed=embed, view=self)
            await asyncio.sleep(NEXT_DELAY)
            await self.session.advance()


# --- Cog ---

class Games(commands.Cog):
    """Anime trivia and games."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.anilist = AniListService()
        self.generator = TriviaGenerator(self.anilist)

    @commands.hybrid_command(name="trivia", description="Start an anime trivia session")
    @app_commands.describe(rounds="Number of questions (1-10, default 5)")
    async def trivia(self, ctx: commands.Context, rounds: int = 5):
        """Start a multi-round anime trivia session for the whole server."""
        rounds = max(1, min(rounds, 10))
        await ctx.defer()

        loading_embed = base_embed(
            title="Preparing Trivia...",
            description=f"Fetching {rounds} questions from AniList. Please wait!",
            color=Colors.GAMES,
        )
        msg = await ctx.send(embed=loading_embed)

        questions = await self.generator.generate(count=rounds)

        if not questions:
            await msg.edit(
                embed=error_embed("Could not generate questions. AniList may be unavailable.")
            )
            return

        session = TriviaSession(
            guild_id=ctx.guild.id,
            questions=questions,
            generator=self.generator,
        )
        session.message = msg

        await session.show_current()

    @commands.hybrid_command(name="ranking", description="Show the anime trivia leaderboard for this server")
    async def ranking(self, ctx: commands.Context):
        """Display the all-time trivia leaderboard for this server."""
        await ctx.defer()

        guild_scores = _leaderboard.get(ctx.guild.id, {})

        embed = base_embed(title=f"Trivia Leaderboard — {ctx.guild.name}", color=Colors.GAMES)

        if not guild_scores:
            embed.description = "No scores yet! Use `/trivia` to start playing."
            await ctx.send(embed=embed)
            return

        sorted_scores = sorted(guild_scores.values(), key=lambda s: s["points"], reverse=True)
        medals = ["🥇", "🥈", "🥉"]
        ranking_text = ""
        for idx, entry in enumerate(sorted_scores[:10]):
            prefix = medals[idx] if idx < 3 else f"**#{idx + 1}**"
            ranking_text += f"{prefix} **{entry['name']}** — {entry['points']} pts\n"

        embed.description = ranking_text
        embed.set_footer(text="Top 10 all-time scores in this server")
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    """Load the Games cog."""
    await bot.add_cog(Games(bot))
