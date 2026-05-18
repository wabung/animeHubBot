"""
Trivia question generator using live AniList data.
Builds questions dynamically from a pool of popular anime and characters.
"""

import random
import logging
from dataclasses import dataclass, field
from typing import Optional
from .anilist_service import AniListService
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
    image: Optional[str] = None         # Cover art or character image shown in embed
    character_name: Optional[str] = None  # Populated only for character questions


class TriviaGenerator:
    """Generates trivia questions dynamically from AniList data."""

    def __init__(self, anilist: AniListService):
        self.anilist = anilist
        self._anime_pool: list[dict] = []
        self._char_pool: list[dict] = []

    async def refresh_pools(self):
        """Fetch fresh anime and character pools from AniList."""
        anime_result = await self.anilist.get_anime_pool(size=50)
        if anime_result and anime_result.get("Page", {}).get("media"):
            self._anime_pool = anime_result["Page"]["media"]

        char_result = await self.anilist.get_characters_pool(size=25)
        if char_result and char_result.get("Page", {}).get("characters"):
            # Keep only characters that have at least one anime attached
            self._char_pool = [
                c for c in char_result["Page"]["characters"]
                if c.get("media", {}).get("nodes")
            ]

        logger.info(
            f"Trivia pools refreshed — anime: {len(self._anime_pool)}, "
            f"characters: {len(self._char_pool)}"
        )

    async def generate(self, count: int = 5, lang: str = "en") -> list[TriviaQuestion]:
        """
        Generate a list of unique trivia questions.
        Refreshes pools when they are too small to cover the requested count.
        """
        if len(self._anime_pool) < count * 3 or len(self._char_pool) < count:
            await self.refresh_pools()

        if not self._anime_pool:
            return []

        questions: list[TriviaQuestion] = []
        used_anime_ids: set[int] = set()
        used_char_ids: set[int] = set()

        question_builders = [
            self._episodes_question,
            self._episodes_question,
            self._studio_question,
            self._studio_question,
            self._genre_question,
            self._character_question,
            self._character_question,
            self._character_question,
        ]

        attempts = 0
        while len(questions) < count and attempts < count * 6:
            attempts += 1
            builder = random.choice(question_builders)

            if builder == self._character_question:
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

        # Build distractor anime titles from the anime pool
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
