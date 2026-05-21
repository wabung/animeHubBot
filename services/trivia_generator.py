"""
Trivia question generator using live AniList and AnimeThemes data.
Builds questions dynamically from pools of popular anime, characters and openings.
"""

import random
import logging
from dataclasses import dataclass, field
from typing import Optional
from .anilist_service import AniListService
from .animethemes_service import AnimeThemesService
from utils.i18n import t

logger = logging.getLogger(__name__)

ALL_GENRES = [
    "Action", "Adventure", "Comedy", "Drama", "Fantasy", "Horror",
    "Mahou Shoujo", "Mecha", "Music", "Mystery", "Psychological",
    "Romance", "Sci-Fi", "Slice of Life", "Sports", "Supernatural", "Thriller"
]

DIFFICULTY_POINTS = {
    "easy":   100,
    "medium": 150,
    "hard":   200,
}


@dataclass
class TriviaQuestion:
    question: str
    options: list[str]
    correct_index: int
    points: int
    image: Optional[str] = None           # Cover art or character image shown in embed
    character_name: Optional[str] = None  # Populated only for character questions
    video_url: Optional[str] = None       # Populated only for opening questions


class TriviaGenerator:
    """Generates trivia questions dynamically from AniList and AnimeThemes data."""

    def __init__(self, anilist: AniListService, animethemes: AnimeThemesService):
        self.anilist = anilist
        self.animethemes = animethemes
        self._anime_pool: list[dict] = []
        self._char_pool: list[dict] = []
        self._opening_pool: list[dict] = []

    async def refresh_pools(self):
        """Fetch fresh anime and character pools from AniList."""
        anime_result = await self.anilist.get_anime_pool(size=50)
        if anime_result and anime_result.get("Page", {}).get("media"):
            self._anime_pool = anime_result["Page"]["media"]

        char_result = await self.anilist.get_characters_pool(size=25)
        if char_result and char_result.get("Page", {}).get("characters"):
            self._char_pool = [
                c for c in char_result["Page"]["characters"]
                if c.get("media", {}).get("nodes")
            ]

        logger.info(
            f"AniList pools refreshed — anime: {len(self._anime_pool)}, "
            f"characters: {len(self._char_pool)}"
        )

    async def refresh_opening_pool(self):
        """
        Fetch the opening pool from the AnimeThemes REST API (real slugs, no 404s).
        Falls back to URL construction from AniList titles if the API is unreachable.
        """
        try:
            pool = await self.animethemes.fetch_opening_pool(limit=50)
            if pool:
                self._opening_pool = pool
                logger.info(f"Opening pool ready (API) — {len(self._opening_pool)} entries")
                return
        except Exception as e:
            logger.warning(f"AnimeThemes API pool fetch failed, using URL construction: {e}")

        # Fallback: construct URLs from AniList romaji titles
        self._opening_pool = [
            {
                "anime_name": a["title"]["romaji"],
                "video_url": AnimeThemesService.build_video_url(a["title"]["romaji"]),
            }
            for a in self._anime_pool
            if a.get("title", {}).get("romaji")
        ]
        logger.info(f"Opening pool ready (constructed) — {len(self._opening_pool)} candidates")

    async def generate(self, count: int = 5, lang: str = "en", mode: str = "both") -> list[TriviaQuestion]:
        """
        Generate a list of unique trivia questions.
        mode: 'basic' | 'openings' | 'both'
        """
        need_basic = mode in ("basic", "both")
        need_openings = mode in ("openings", "both")

        # Anime pool is the source for both basic questions and opening URL construction
        if len(self._anime_pool) < count * 3 or (need_basic and len(self._char_pool) < count):
            await self.refresh_pools()

        if need_openings and not self._opening_pool:
            await self.refresh_opening_pool()

        if need_basic and not self._anime_pool:
            return []
        if mode == "openings" and not self._opening_pool:
            return []

        # Build weighted builder list according to mode
        basic_builders = [
            self._episodes_question, self._episodes_question,
            self._studio_question, self._studio_question,
            self._genre_question,
            self._character_question, self._character_question, self._character_question,
        ]
        opening_builders = [self._opening_question] * 4

        if mode == "basic":
            weighted_builders = basic_builders
        elif mode == "openings":
            weighted_builders = opening_builders
        else:
            weighted_builders = basic_builders + opening_builders

        questions: list[TriviaQuestion] = []
        used_anime_ids: set[int] = set()
        used_char_ids: set[int] = set()
        used_theme_keys: set[str] = set()

        attempts = 0
        while len(questions) < count and attempts < count * 8:
            attempts += 1
            builder = random.choice(weighted_builders)

            if builder == self._opening_question:
                candidates = [
                    th for th in self._opening_pool
                    if th["anime_name"] not in used_theme_keys
                ]
                if not candidates:
                    continue
                theme = random.choice(candidates)
                question = self._opening_question(theme, lang)
                if question:
                    questions.append(question)
                    used_theme_keys.add(theme["anime_name"])

            elif builder == self._character_question:
                candidates = [c for c in self._char_pool if c["id"] not in used_char_ids]
                if not candidates:
                    continue
                char = random.choice(candidates)
                question = self._character_question(char, lang)
                if question:
                    questions.append(question)
                    used_char_ids.add(char["id"])

            else:
                candidates = [a for a in self._anime_pool if a["id"] not in used_anime_ids]
                if not candidates:
                    continue
                anime = random.choice(candidates)
                question = builder(anime, lang)
                if question:
                    questions.append(question)
                    used_anime_ids.add(anime["id"])

        return questions

    # --- Question builders ---

    def _episodes_question(self, anime: dict, lang: str = "en") -> Optional[TriviaQuestion]:
        episodes = anime.get("episodes")
        if not episodes or episodes < 1:
            return None

        offsets = [-24, -12, -8, -4, 4, 8, 12, 24, 36, 50]
        random.shuffle(offsets)
        distractors: set[int] = set()
        for offset in offsets:
            value = episodes + offset
            if value > 0 and value != episodes:
                distractors.add(value)
            if len(distractors) == 3:
                break

        if len(distractors) < 3:
            return None

        options = [str(episodes)] + [str(d) for d in distractors]
        random.shuffle(options)

        return TriviaQuestion(
            question=t("trivia.q_episodes", lang, title=anime["title"]["romaji"]),
            options=options,
            correct_index=options.index(str(episodes)),
            points=DIFFICULTY_POINTS["easy"],
            image=anime.get("coverImage", {}).get("large"),
        )

    def _studio_question(self, anime: dict, lang: str = "en") -> Optional[TriviaQuestion]:
        studios = (anime.get("studios") or {}).get("nodes", [])
        if not studios:
            return None

        correct_studio = studios[0]["name"]

        other_studios: set[str] = set()
        for other in self._anime_pool:
            if other["id"] == anime["id"]:
                continue
            for s in (other.get("studios") or {}).get("nodes", []):
                name = s.get("name", "")
                if name and name != correct_studio:
                    other_studios.add(name)

        if len(other_studios) < 3:
            return None

        distractors = random.sample(sorted(other_studios), 3)
        options = [correct_studio] + distractors
        random.shuffle(options)

        return TriviaQuestion(
            question=t("trivia.q_studio", lang, title=anime["title"]["romaji"]),
            options=options,
            correct_index=options.index(correct_studio),
            points=DIFFICULTY_POINTS["hard"],
            image=anime.get("coverImage", {}).get("large"),
        )

    def _genre_question(self, anime: dict, lang: str = "en") -> Optional[TriviaQuestion]:
        genres = anime.get("genres", [])
        if not genres:
            return None

        correct_genre = genres[0]
        distractors_pool = [g for g in ALL_GENRES if g not in genres]
        if len(distractors_pool) < 3:
            return None

        options = [correct_genre] + random.sample(distractors_pool, 3)
        random.shuffle(options)

        return TriviaQuestion(
            question=t("trivia.q_genre", lang, title=anime["title"]["romaji"]),
            options=options,
            correct_index=options.index(correct_genre),
            points=DIFFICULTY_POINTS["easy"],
            image=anime.get("coverImage", {}).get("large"),
        )

    def _character_question(self, char: dict, lang: str = "en") -> Optional[TriviaQuestion]:
        anime_nodes = (char.get("media") or {}).get("nodes", [])
        if not anime_nodes:
            return None

        correct_anime = anime_nodes[0]["title"]["romaji"]
        char_image = (char.get("image") or {}).get("large")
        char_name = (char.get("name") or {}).get("full", "???")

        distractor_titles: set[str] = set()
        candidates = random.sample(self._anime_pool, min(20, len(self._anime_pool)))
        for a in candidates:
            title = a["title"]["romaji"]
            if title != correct_anime:
                distractor_titles.add(title)
            if len(distractor_titles) == 3:
                break

        if len(distractor_titles) < 3:
            return None

        options = [correct_anime] + list(distractor_titles)
        random.shuffle(options)

        return TriviaQuestion(
            question=t("trivia.q_character", lang),
            options=options,
            correct_index=options.index(correct_anime),
            points=DIFFICULTY_POINTS["medium"],
            image=char_image,
            character_name=char_name,
        )

    def _opening_question(self, theme: dict, lang: str = "en") -> Optional[TriviaQuestion]:
        correct_anime = theme["anime_name"]

        distractor_names = {
            th["anime_name"] for th in self._opening_pool
            if th["anime_name"] != correct_anime
        }
        if len(distractor_names) < 3:
            return None

        distractors = random.sample(sorted(distractor_names), 3)
        options = [correct_anime] + distractors
        random.shuffle(options)

        song_title = theme.get("song_title")
        artist = theme.get("artist")
        if song_title and artist:
            question = t("trivia.q_opening", lang, title=song_title, artist=artist)
        else:
            question = t("trivia.q_opening_notitle", lang)

        return TriviaQuestion(
            question=question,
            options=options,
            correct_index=options.index(correct_anime),
            points=DIFFICULTY_POINTS["medium"],
            video_url=theme.get("video_url"),
        )
