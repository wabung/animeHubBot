"""
Games cog — anime trivia with dynamic questions from AniList.
"""

import asyncio
import io
import random
import discord
from discord import app_commands
from discord.ext import commands
from services import AniListService, AnimeThemesService, TriviaGenerator, TriviaQuestion, BackendClient
from utils.embeds import (
    base_embed, error_embed, Colors,
    trivia_question_embed, trivia_answered_embed,
    trivia_timeout_embed, trivia_results_embed,
)
from utils.i18n import t
import logging

logger = logging.getLogger(__name__)

QUESTION_TIMEOUT = 20
OPENING_QUESTION_TIMEOUT = 35
NEXT_DELAY = 3


# --- Trivia session state ---

class TriviaSession:
    """Holds the state of a running trivia session for one message."""

    def __init__(
        self,
        guild_id: int,
        questions: list[TriviaQuestion],
        backend: BackendClient,
        lang: str = "en",
        animethemes: AnimeThemesService | None = None,
        generator: TriviaGenerator | None = None,
    ):
        self.guild_id = guild_id
        self.questions = questions
        self.backend = backend
        self.lang = lang
        self.animethemes = animethemes
        self.generator = generator
        self.current = 0
        self.scores: dict[int, dict] = {}
        self.message: discord.Message | None = None
        self._video_message: discord.Message | None = None

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

        if self._video_message:
            try:
                await self._video_message.delete()
            except Exception:
                pass
            self._video_message = None

        if q.video_url:
            result = None
            if self.animethemes:
                result = await self.animethemes.get_clip_bytes(q.video_url)

            # If the URL 404d or clip failed, try fallback openings from the pool
            if result is None and self.animethemes and self.generator:
                already_used = {oq.video_url for oq in self.questions if oq.video_url}
                pool = [
                    th for th in self.generator._opening_pool
                    if th["video_url"] not in already_used
                ]
                random.shuffle(pool)
                for candidate in pool[:3]:
                    await asyncio.sleep(1)
                    result = await self.animethemes.get_clip_bytes(candidate["video_url"])
                    if result:
                        new_q = self.generator._opening_question(candidate, self.lang)
                        if new_q:
                            self.questions[self.current] = new_q
                            q = new_q
                        break

            if result is None:
                embed = error_embed(
                    t("trivia.opening_unavailable_desc", self.lang),
                    self.lang,
                    title=t("trivia.opening_unavailable_title", self.lang),
                )
                await self.message.channel.send(embed=embed)
                await asyncio.sleep(NEXT_DELAY)
                await self.advance()
                return

            if result:
                clip, ext = result
                hint = t("trivia.opening_hint", self.lang)
                self._video_message = await self.message.channel.send(
                    hint, file=discord.File(io.BytesIO(clip), f"opening.{ext}")
                )

        embed = trivia_question_embed(q, self.current + 1, self.total, self.lang)
        view = TriviaQuestionView(self)
        self.message = await self.message.channel.send(embed=embed, view=view)
        view.message = self.message

    async def advance(self):
        self.current += 1
        if self.current >= self.total:
            # Clean up the last video message when the session ends
            if self._video_message:
                try:
                    await self._video_message.delete()
                except Exception:
                    pass
            embed = trivia_results_embed(self.scores, self.total, self.lang)
            await self.message.channel.send(embed=embed)
            await self.backend.increment_trivia(self.guild_id)
        else:
            await self.show_current()


# --- Question view ---

class TriviaQuestionView(discord.ui.View):
    """Displays A/B/C/D buttons for a single trivia question."""

    LABELS = ["A", "B", "C", "D"]

    def __init__(self, session: TriviaSession):
        timeout = OPENING_QUESTION_TIMEOUT if session.current_question.video_url else QUESTION_TIMEOUT
        super().__init__(timeout=timeout)
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
                    embed=error_embed(
                        t("trivia.already_answered", self.session.lang),
                        self.session.lang,
                    ),
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
                self.session.lang,
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

        embed = trivia_timeout_embed(q, self.session.current + 1, self.session.total, self.session.lang)
        if self.message:
            await self.message.edit(embed=embed, view=self)
            await asyncio.sleep(NEXT_DELAY)
            await self.session.advance()


# --- Cog ---

class Games(commands.Cog, name="🎮 Games"):
    """Anime trivia and games."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.anilist = AniListService()
        self.animethemes = AnimeThemesService()
        self.generator = TriviaGenerator(self.anilist, self.animethemes)

    @property
    def backend(self) -> BackendClient:
        return self.bot.backend

    async def _check_games_channel(self, ctx: commands.Context, lang: str) -> bool:
        """Return True if the command can proceed; False (+ send error) if wrong channel."""
        guild_config = await self.backend.get_guild_config(ctx.guild.id)
        games_channel_id = (guild_config or {}).get("games_channel_id")
        if games_channel_id and ctx.channel.id != games_channel_id:
            channel = ctx.guild.get_channel(games_channel_id)
            mention = channel.mention if channel else f"<#{games_channel_id}>"
            await ctx.send(
                embed=error_embed(t("games.wrong_channel", lang, channel=mention), lang),
                ephemeral=True,
            )
            return False
        return True

    @commands.hybrid_command(name="trivia", description="Start an anime trivia session")
    @app_commands.describe(
        rounds="Number of questions (1-10, default 5)",
        mode="Question type: basic, openings, or both (default: both)",
    )
    @app_commands.choices(mode=[
        app_commands.Choice(name="Both (basic + openings)", value="both"),
        app_commands.Choice(name="Basic (episodes, studio, genre, characters)", value="basic"),
        app_commands.Choice(name="Openings only", value="openings"),
    ])
    async def trivia(self, ctx: commands.Context, rounds: int = 5, mode: str = "both"):
        """Start a multi-round anime trivia session for the whole server."""
        rounds = max(1, min(rounds, 10))
        lang = await self.bot.get_lang(ctx.guild.id)
        if not await self._check_games_channel(ctx, lang):
            return
        await ctx.defer()

        await self.backend.register_user(ctx.author.id, ctx.author.name)

        msg = await ctx.send(embed=base_embed(
            title=t("trivia.preparing_title", lang),
            description=t("trivia.preparing_desc", lang, rounds=rounds),
            color=Colors.GAMES,
        ))

        questions = await self.generator.generate(count=rounds, lang=lang, mode=mode)

        if not questions:
            await msg.edit(embed=error_embed(t("trivia.error_no_questions", lang), lang))
            return

        session = TriviaSession(
            guild_id=ctx.guild.id,
            questions=questions,
            backend=self.backend,
            lang=lang,
            animethemes=self.animethemes,
            generator=self.generator,
        )
        session.message = msg
        await session.show_current()

    @commands.hybrid_command(name="ranking", description="Show the trivia leaderboard for this server")
    async def ranking(self, ctx: commands.Context):
        """Display the all-time trivia leaderboard for this server."""
        lang = await self.bot.get_lang(ctx.guild.id)
        if not await self._check_games_channel(ctx, lang):
            return
        await ctx.defer()

        embed = base_embed(title=t("ranking.title", lang, guild=ctx.guild.name), color=Colors.GAMES)

        entries = await self.backend.get_ranking(ctx.guild.id, limit=10)

        if not entries:
            embed.description = t("ranking.no_scores", lang)
            await ctx.send(embed=embed)
            return

        medals = ["🥇", "🥈", "🥉"]
        ranking_text = ""
        for entry in entries:
            pos = entry["position"] - 1
            prefix = medals[pos] if pos < 3 else f"**#{entry['position']}**"
            ranking_text += (
                f"{prefix} **{entry['username']}** — {entry['total_points']} pts "
                f"({entry['correct_answers']}/{entry['games_played']} {t('ranking.correct_label', lang)})\n"
            )

        embed.description = ranking_text
        embed.set_footer(text=t("ranking.footer", lang))
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Games(bot))
