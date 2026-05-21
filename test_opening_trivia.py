"""
Diagnostic script for the opening trivia pipeline.
Simulates the actual bot flow: build pool (no CDN calls) -> extract one clip.
Run: python test_opening_trivia.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))


async def main():
    from services.animethemes_service import AnimeThemesService

    print("=" * 60)
    print("STEP 1 -- Fetch popular anime from AniList")
    print("=" * 60)
    import aiohttp
    query = """
    query { Page(page: 1, perPage: 50) {
        media(type: ANIME, sort: POPULARITY_DESC) {
            id title { romaji }
        }
    } }
    """
    async with aiohttp.ClientSession() as s:
        async with s.post(
            "https://graphql.anilist.co",
            json={"query": query},
            timeout=aiohttp.ClientTimeout(total=15),
        ) as r:
            data = await r.json()
    media = data["data"]["Page"]["media"]
    print(f"Fetched {len(media)} anime")

    print("\n" + "=" * 60)
    print("STEP 2 -- Build opening pool (no CDN calls)")
    print("=" * 60)
    svc = AnimeThemesService()
    pool = [
        {
            "anime_name": a["title"]["romaji"],
            "video_url": AnimeThemesService.build_video_url(a["title"]["romaji"]),
        }
        for a in media if a.get("title", {}).get("romaji")
    ]
    print(f"Pool built: {len(pool)} candidates (no network requests)")
    print("Sample:")
    for c in pool[:5]:
        print(f"  {c['anime_name']} -> {c['video_url'].split('/')[-1]}")

    print("\n" + "=" * 60)
    print("STEP 3 -- ffmpeg clip extraction (first candidate)")
    print("=" * 60)
    # In the bot, clips are extracted one per question, 20-35s apart.
    # Here we test just the first one with a clean CDN slate.
    url = pool[0]["video_url"]
    print(f"Clipping: {url}")
    clip = await svc.get_clip_bytes(url)
    if clip:
        print(f"Clip OK -- {len(clip) // 1024} KB")
    else:
        print("Clip FAILED (CDN may be rate-limited from a previous test run)")
        print("Wait 40s and retry if so.")

    print("\nDone.")


asyncio.run(main())
