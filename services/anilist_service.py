"""
AniList GraphQL API service for anime data retrieval.
Handles all interactions with the AniList API using GraphQL.
"""

import logging
from typing import Optional, List, Dict, Any
from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport

logger = logging.getLogger(__name__)

ANILIST_API_URL = "https://graphql.anilist.co"


class AniListService:
    """Service for interacting with AniList GraphQL API."""

    def __init__(self):
        """Initialize the AniList service with GraphQL client."""
        self.transport = AIOHTTPTransport(url=ANILIST_API_URL)
        self.client = Client(transport=self.transport, fetch_schema_from_transport=False)

    async def search_anime(self, query: str, page: int = 1, per_page: int = 5) -> Optional[Dict[str, Any]]:
        """
        Search for anime by title.

        Args:
            query: Anime title to search for
            page: Page number for pagination (default 1)
            per_page: Number of results per page (default 5)

        Returns:
            Dictionary with search results or None if error
        """
        search_query = gql("""
            query SearchAnime($search: String, $page: Int, $perPage: Int) {
                Page(page: $page, perPage: $perPage) {
                    pageInfo {
                        total
                        currentPage
                        lastPage
                        hasNextPage
                    }
                    media(search: $search, type: ANIME, sort: SEARCH_MATCH) {
                        id
                        title {
                            romaji
                            english
                            native
                        }
                        coverImage {
                            large
                        }
                        description
                        status
                        episodes
                        averageScore
                        meanScore
                        startDate {
                            year
                            month
                            day
                        }
                        genres
                        studios(isMain: true) {
                            nodes {
                                name
                            }
                        }
                    }
                }
            }
        """)

        try:
            async with self.client as session:
                result = await session.execute(
                    search_query,
                    variable_values={
                        "search": query,
                        "page": page,
                        "perPage": per_page
                    }
                )
                return result
        except Exception as e:
            logger.error(f"Error searching anime '{query}': {e}")
            return None

    async def get_anime_details(self, anime_id: int) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific anime.

        Args:
            anime_id: AniList anime ID

        Returns:
            Dictionary with anime details or None if error
        """
        details_query = gql("""
            query GetAnimeDetails($id: Int!) {
                Media(id: $id, type: ANIME) {
                    id
                    title {
                        romaji
                        english
                        native
                    }
                    description
                    coverImage {
                        large
                        color
                    }
                    bannerImage
                    status
                    episodes
                    duration
                    averageScore
                    meanScore
                    popularity
                    startDate {
                        year
                        month
                        day
                    }
                    endDate {
                        year
                        month
                        day
                    }
                    season
                    seasonYear
                    genres
                    source
                    studios(isMain: true) {
                        nodes {
                            name
                        }
                    }
                    nextAiringEpisode {
                        airingAt
                        timeUntilAiring
                        episode
                    }
                    relations {
                        edges {
                            relationType
                            node {
                                id
                                title {
                                    romaji
                                }
                            }
                        }
                    }
                    recommendations(perPage: 3) {
                        edges {
                            node {
                                mediaRecommendation {
                                    id
                                    title {
                                        romaji
                                    }
                                }
                                rating
                            }
                        }
                    }
                }
            }
        """)

        try:
            async with self.client as session:
                result = await session.execute(
                    details_query,
                    variable_values={"id": anime_id}
                )
                return result
        except Exception as e:
            logger.error(f"Error fetching details for anime {anime_id}: {e}")
            return None

    async def get_anime_by_genre(
        self,
        genres: List[str],
        page: int = 1,
        per_page: int = 5,
        min_score: int = 0
    ) -> Optional[Dict[str, Any]]:
        """
        Get anime recommendations by genres.

        Args:
            genres: List of genre names to filter by
            page: Page number for pagination (default 1)
            per_page: Number of results per page (default 5)
            min_score: Minimum average score (0-100)

        Returns:
            Dictionary with anime results or None if error
        """
        genre_query = gql("""
            query GetAnimeByGenre($genres: [String!], $page: Int, $perPage: Int, $minScore: Int) {
                Page(page: $page, perPage: $perPage) {
                    pageInfo {
                        total
                        currentPage
                        lastPage
                        hasNextPage
                    }
                    media(genre_in: $genres, type: ANIME, averageScore_greater: $minScore, sort: SCORE_DESC) {
                        id
                        title {
                            romaji
                            english
                        }
                        coverImage {
                            large
                        }
                        averageScore
                        genres
                        episodes
                        status
                    }
                }
            }
        """)

        try:
            async with self.client as session:
                result = await session.execute(
                    genre_query,
                    variable_values={
                        "genres": genres,
                        "page": page,
                        "perPage": per_page,
                        "minScore": min_score
                    }
                )
                return result
        except Exception as e:
            logger.error(f"Error fetching anime by genres {genres}: {e}")
            return None

    async def get_anime_characters(self, anime_id: int, per_page: int = 10) -> Optional[Dict[str, Any]]:
        """
        Get main characters from an anime.

        Args:
            anime_id: AniList anime ID
            per_page: Number of characters to retrieve (default 10)

        Returns:
            Dictionary with character information or None if error
        """
        characters_query = gql("""
            query GetAnimeCharacters($id: Int!, $perPage: Int) {
                Media(id: $id, type: ANIME) {
                    id
                    title {
                        romaji
                    }
                    characters(perPage: $perPage) {
                        edges {
                            role
                            voiceActors(language: JAPANESE) {
                                name {
                                    full
                                }
                            }
                            node {
                                id
                                name {
                                    full
                                    native
                                }
                                image {
                                    large
                                }
                                description
                            }
                        }
                    }
                }
            }
        """)

        try:
            async with self.client as session:
                result = await session.execute(
                    characters_query,
                    variable_values={"id": anime_id, "perPage": per_page}
                )
                return result
        except Exception as e:
            logger.error(f"Error fetching characters for anime {anime_id}: {e}")
            return None

    async def get_user_profile(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Get AniList user profile information.

        Args:
            username: AniList username

        Returns:
            Dictionary with user profile or None if error
        """
        user_query = gql("""
            query GetUserProfile($name: String!) {
                User(name: $name) {
                    id
                    name
                    about
                    avatar {
                        large
                    }
                    bannerImage
                    statistics {
                        anime {
                            count
                            meanScore
                            standardDeviation
                            minutesWatched
                            episodesWatched
                        }
                    }
                    moderatorRoles
                    donatorTier
                }
            }
        """)

        try:
            async with self.client as session:
                result = await session.execute(
                    user_query,
                    variable_values={"name": username}
                )
                return result
        except Exception as e:
            logger.error(f"Error fetching user profile '{username}': {e}")
            return None

    async def get_trending_anime(self, page: int = 1, per_page: int = 10) -> Optional[Dict[str, Any]]:
        """
        Get currently trending anime.

        Args:
            page: Page number for pagination (default 1)
            per_page: Number of results per page (default 10)

        Returns:
            Dictionary with trending anime or None if error
        """
        trending_query = gql("""
            query GetTrendingAnime($page: Int, $perPage: Int) {
                Page(page: $page, perPage: $perPage) {
                    pageInfo {
                        total
                        currentPage
                        lastPage
                        hasNextPage
                    }
                    media(type: ANIME, sort: TRENDING_DESC) {
                        id
                        title {
                            romaji
                            english
                        }
                        coverImage {
                            large
                        }
                        averageScore
                        genres
                        episodes
                        status
                        trending
                    }
                }
            }
        """)

        try:
            async with self.client as session:
                result = await session.execute(
                    trending_query,
                    variable_values={"page": page, "perPage": per_page}
                )
                return result
        except Exception as e:
            logger.error(f"Error fetching trending anime: {e}")
            return None

    async def get_characters_pool(self, size: int = 25) -> Optional[Dict[str, Any]]:
        """
        Fetch a pool of popular characters with their anime for trivia generation.

        Args:
            size: Number of characters to fetch (default 25)

        Returns:
            Dictionary with character list or None if error
        """
        import random
        page = random.randint(1, 5)

        characters_pool_query = gql("""
            query GetCharactersPool($page: Int, $perPage: Int) {
                Page(page: $page, perPage: $perPage) {
                    characters(sort: FAVOURITES_DESC) {
                        id
                        name {
                            full
                        }
                        image {
                            large
                        }
                        media(type: ANIME, sort: POPULARITY_DESC) {
                            nodes {
                                id
                                title {
                                    romaji
                                    english
                                }
                            }
                        }
                    }
                }
            }
        """)

        try:
            async with self.client as session:
                result = await session.execute(
                    characters_pool_query,
                    variable_values={"page": page, "perPage": size}
                )
                return result
        except Exception as e:
            logger.error(f"Error fetching characters pool: {e}")
            return None

    async def get_anime_pool(self, size: int = 50) -> Optional[Dict[str, Any]]:
        """
        Fetch a pool of popular anime with full data needed for trivia generation.
        Uses a random page from the top 500 to ensure variety across sessions.

        Args:
            size: Number of anime to fetch (default 50)

        Returns:
            Dictionary with anime list or None if error
        """
        import random
        page = random.randint(1, 10)

        pool_query = gql("""
            query GetAnimePool($page: Int, $perPage: Int) {
                Page(page: $page, perPage: $perPage) {
                    media(type: ANIME, sort: SCORE_DESC, averageScore_greater: 60) {
                        id
                        title {
                            romaji
                            english
                        }
                        coverImage {
                            large
                        }
                        episodes
                        averageScore
                        genres
                        startDate {
                            year
                        }
                        studios(isMain: true) {
                            nodes {
                                name
                            }
                        }
                    }
                }
            }
        """)

        try:
            async with self.client as session:
                result = await session.execute(
                    pool_query,
                    variable_values={"page": page, "perPage": size}
                )
                return result
        except Exception as e:
            logger.error(f"Error fetching anime pool: {e}")
            return None

