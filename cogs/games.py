"""
Games cog — anime trivia with dynamic questions from AniList.
"""

import asyncio
import discord
from discord import app_commands
from discord.ext import commands
from services import AniListService, TriviaGenerator, TriviaQuestion, BackendClient
from utils.embeds import (
    base_embed, error_embed, Colors,
    trivia_question_embed, trivia_answered_embed,
    trivia_timeout_embed, trivia_results_embed,
)
import logging

logger = logging.getLogger(__name__)

QUESTION_TIMEOUT = 20
NEXT_DELAY = 3


# --- Trivia session state ---

class TriviaSession:
    """Holds the state of a running trivia session for one message."""

    def __init__(self, guild_id: int, questions: list[TriviaQuestion], backend: BackendClient):
        self.guild_id = guild_id
        self.questions = questions
        self.backend = backend
        self.current = 0
        self.scores: dict[int, dict] = {}  # local copy for the results embed
        self.message: discord.Message | None = None

    @property
    def current_question(self) -> TriviaQuestion:
        return self.questions[self.current]

    @property
    def total(self) -> int:
        return len(self.questions)

    async def record_answer(self, user_id: int, display_name: str, points: int, correct: bool):
        """Persist score to backend and update local session copy."""
        if user_id not in self.scores:
            self.scores[user_id] = {"name": display_name, "points": 0}
        self.scores[user_id]["points"] += points
        self.scores[user_id]["name"] = display_name

        await self.backend.add_score(
            user_discord_id=user_id,
            guild_id=self.guild_id,
            username=display_name,
            points=points,
            correct=correct,
        )

    async def show_current(self):
        q = self.current_question
        embed = trivia_question_embed(q, self.current + 1, self.total)
        view = TriviaQuestionView(self)
        await self.message.edit(embed=embed, view=view)
        view.message = self.message

    async def advance(self):
        self.current += 1
        if self.current >= self.total:
            embed = trivia_results_embed(self.scores, self.total)
            await self.message.edit(embed=embed, view=None)
            await self.backend.increment_trivia(self.guild_id)
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
            button = discord.ui.Button(
                label=f"{self.LABELS[idx]}. {option}"[:80],
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

            await self.session.record_answer(
                interaction.user.id, interaction.user.display_name, points, is_correct
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

    @property
    def backend(self) -> BackendClient:
        return self.bot.backend

    @commands.hybrid_command(name="trivia", description="Start an anime trivia session")
    @app_commands.describe(rounds="Number of questions (1-10, default 5)")
    async def trivia(self, ctx: commands.Context, rounds: int = 5):
        """Start a multi-round anime trivia session for the whole server."""
        rounds = max(1, min(rounds, 10))
        await ctx.defer()

        await self.backend.register_user(ctx.author.id, ctx.author.name)

        msg = await ctx.send(embed=base_embed(
            title="Preparing Trivia...",
            description=f"Fetching {rounds} questions from AniList. Please wait!",
            color=Colors.GAMES,
        ))

        questions = await self.generator.generate(count=rounds)

        if not questions:
            await msg.edit(embed=error_embed("Could not generate questions. AniList may be unavailable."))
            return

        session = TriviaSession(
            guild_id=ctx.guild.id,
            questions=questions,
            backend=self.backend,
        )
        session.message = msg
        await session.show_current()

    @commands.hybrid_command(name="ranking", description="Show the trivia leaderboard for this server")
    async def ranking(self, ctx: commands.Context):
        """Display the all-time trivia leaderboard for this server."""
        await ctx.defer()

        embed = base_embed(title=f"Trivia Leaderboard — {ctx.guild.name}", color=Colors.GAMES)

        entries = await self.backend.get_ranking(ctx.guild.id, limit=10)

        if not entries:
            embed.description = "No scores yet! Use `/trivia` to start playing."
            await ctx.send(embed=embed)
            return

        medals = ["🥇", "🥈", "🥉"]
        ranking_text = ""
        for entry in entries:
            pos = entry["position"] - 1
            prefix = medals[pos] if pos < 3 else f"**#{entry['position']}**"
            ranking_text += (
                f"{prefix} **{entry['username']}** — {entry['total_points']} pts "
                f"({entry['correct_answers']}/{entry['games_played']} correct)\n"
            )

        embed.description = ranking_text
        embed.set_footer(text="All-time scores in this server")
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Games(bot))
