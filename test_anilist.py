"""
Test script to verify AniList GraphQL service functionality.
Run with: python test_anilist.py
"""

import asyncio
from services.anilist_service import AniListService
import json


async def main():
    """Test various AniList service methods."""
    service = AniListService()

    print("=" * 60)
    print("ANILIST SERVICE TEST")
    print("=" * 60)

    # Test 1: Search anime
    print("\n[TEST 1] Searching for 'Demon Slayer'...")
    search_result = await service.search_anime("Demon Slayer", per_page=3)
    if search_result:
        print(f"Found {search_result['Page']['pageInfo']['total']} anime")
        for anime in search_result['Page']['media']:
            print(f"  - {anime['title']['romaji']} (Score: {anime['averageScore']})")
            anime_id = anime['id']  # Save first anime ID for next tests
    else:
        print("[FAILED] Search failed")

    # Test 2: Get anime details
    if search_result:
        print(f"\n[TEST 2] Getting details for anime ID {anime_id}...")
        details = await service.get_anime_details(anime_id)
        if details:
            media = details['Media']
            print(f"Title: {media['title']['romaji']}")
            print(f"Episodes: {media['episodes']}")
            print(f"Status: {media['status']}")
            print(f"Score: {media['averageScore']}/100")
            print(f"Genres: {', '.join(media['genres'])}")
            print(f"Studios: {', '.join([s['name'] for s in media['studios']['nodes']])}")
        else:
            print("[FAILED] Details fetch failed")

    # Test 3: Get characters
    if search_result:
        print(f"\n[TEST 3] Getting characters for anime ID {anime_id}...")
        characters = await service.get_anime_characters(anime_id, per_page=5)
        if characters:
            char_list = characters['Media']['characters']['edges']
            print(f"Found {len(char_list)} main characters:")
            for edge in char_list[:3]:
                char = edge['node']
                role = edge['role']
                print(f"  - {char['name']['full']} ({role})")
        else:
            print("[FAILED] Characters fetch failed")

    # Test 4: Search by genre
    print("\n[TEST 4] Searching anime by genre 'Action'...")
    genre_result = await service.get_anime_by_genre(["Action"], per_page=3, min_score=70)
    if genre_result:
        print(f"Found {genre_result['Page']['pageInfo']['total']} action anime")
        for anime in genre_result['Page']['media'][:3]:
            print(f"  - {anime['title']['romaji']} (Score: {anime['averageScore']})")
    else:
        print("[FAILED] Genre search failed")

    # Test 5: Get trending anime
    print("\n[TEST 5] Getting trending anime...")
    trending = await service.get_trending_anime(per_page=5)
    if trending:
        print("Top 5 trending anime:")
        for anime in trending['Page']['media'][:5]:
            print(f"  - {anime['title']['romaji']} (Trending: {anime['trending']})")
    else:
        print("[FAILED] Trending fetch failed")

    # Test 6: Get user profile
    print("\n[TEST 6] Fetching user profile 'Rem'...")
    user = await service.get_user_profile("Rem")
    if user:
        stats = user['User']['statistics']['anime']
        print(f"Username: {user['User']['name']}")
        print(f"Anime watched: {stats['count']}")
        print(f"Mean score: {stats['meanScore']}")
        print(f"Episodes watched: {stats['episodesWatched']}")
    else:
        print("[FAILED] User profile fetch failed")

    print("\n" + "=" * 60)
    print("TESTS COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
