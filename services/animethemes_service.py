"""
AnimeThemes service — fetches OP themes via the REST API and clips them for Discord upload.

Pool source: api.animethemes.moe  (real slugs, no 404s)
Clip source: v.animethemes.moe CDN (rate-limited to ~6 req/35 s)
"""

import asyncio
import logging
import re
import subprocess
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)

VIDEO_BASE = "https://v.animethemes.moe"
_API_BASE = "https://api.animethemes.moe"
_CLIP_DURATION = 12
_MAX_CLIP_BYTES = 9_000_000
_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
_REFERER = "https://animethemes.moe/"
_VERIFY_BATCH = 2
_VERIFY_BATCH_DELAY = 0.4


class AnimeThemesService:
    """Fetches AnimeThemes OP data via API and clips video segments for Discord."""

    # --- Pool fetching ---

    async def fetch_opening_pool(self, limit: int = 100) -> list[dict]:
        """
        Return up to `limit` OP1 entries from the AnimeThemes REST API.
        Each entry: {"anime_name": str, "video_url": str}
        Uses real CDN filenames from the API — no URL construction guesswork.
        """
        url = (
            f"{_API_BASE}/animetheme"
            "?filter[animethemetype]=OP&filter[sequence]=1"
            "&include=anime,animethemeentries.videos"
            f"&page[size]={limit}"
        )
        headers = {"User-Agent": _USER_AGENT}
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as r:
                    if r.status != 200:
                        logger.warning(f"AnimeThemes API returned {r.status}")
                        return []
                    data = await r.json()
        except Exception as e:
            logger.error(f"AnimeThemes API fetch failed: {e}")
            return []

        pool: list[dict] = []
        for theme in data.get("animethemes", []):
            anime = theme.get("anime") or {}
            # API may return anime as object or single-element list
            if isinstance(anime, list):
                anime = anime[0] if anime else {}
            anime_name = anime.get("name", "").strip()
            if not anime_name:
                continue

            video_url: Optional[str] = None
            for entry in theme.get("animethemeentries", []):
                for video in entry.get("videos", []):
                    link = video.get("link")
                    if not link:
                        filename = video.get("filename", "")
                        if filename:
                            link = f"{VIDEO_BASE}/{filename}"
                    if link:
                        video_url = link
                        break
                if video_url:
                    break

            if video_url:
                pool.append({"anime_name": anime_name, "video_url": video_url})

        logger.info(f"AnimeThemes API pool: {len(pool)}/{limit} entries fetched")
        return pool

    # --- Fallback URL construction (kept for offline/testing use) ---

    @staticmethod
    def build_video_url(romaji_title: str) -> str:
        """Best-effort URL construction — use fetch_opening_pool() for production."""
        cleaned = re.sub(r'[^a-zA-Z0-9\s]', '', romaji_title)
        camel = ''.join(word.capitalize() for word in cleaned.split() if word)
        return f"{VIDEO_BASE}/{camel}-OP1.webm"

    # --- CDN verification (used only for pre-game spot-checks) ---

    async def verify_urls(self, candidates: list[dict]) -> list[dict]:
        """
        Check which candidates have a reachable video URL using range GET.
        _VERIFY_BATCH at a time with _VERIFY_BATCH_DELAY between batches.
        """
        headers = {
            "Range": "bytes=0-0",
            "User-Agent": _USER_AGENT,
            "Referer": _REFERER,
        }

        async def _check(candidate: dict) -> Optional[dict]:
            try:
                async with aiohttp.ClientSession() as s:
                    async with s.get(
                        candidate["video_url"],
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=6),
                    ) as r:
                        return candidate if r.status in (200, 206) else None
            except Exception:
                return None

        verified: list[dict] = []
        for i in range(0, len(candidates), _VERIFY_BATCH):
            batch = candidates[i: i + _VERIFY_BATCH]
            results = await asyncio.gather(*[_check(c) for c in batch])
            verified.extend(r for r in results if r is not None)
            if i + _VERIFY_BATCH < len(candidates):
                await asyncio.sleep(_VERIFY_BATCH_DELAY)

        logger.info(f"AnimeThemes verification: {len(verified)}/{len(candidates)} reachable")
        return verified

    # --- Clip extraction ---

    async def get_clip_bytes(self, url: str, duration: int = _CLIP_DURATION) -> Optional[tuple[bytes, str]]:
        """
        Extract the first `duration` seconds from a CDN URL using ffmpeg.
        Returns (raw_bytes, extension) or None.

        Strategy:
        - Try stream-copy first (instant, no re-encode).
        - If copy exits non-zero (CDN error), return None immediately — no re-encode retry.
        - If copy succeeds but size > 9 MB, re-encode to mp4 at lower bitrate.
        """
        try:
            import imageio_ffmpeg  # type: ignore
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        except (ImportError, RuntimeError) as e:
            logger.warning(f"imageio-ffmpeg unavailable ({e})")
            return None

        def _run_cmd(cmd: list[str]) -> Optional[bytes]:
            try:
                result = subprocess.run(cmd, capture_output=True, timeout=60)
                if result.returncode == 0 and result.stdout:
                    return result.stdout
                logger.error(
                    f"ffmpeg exit {result.returncode}: "
                    f"{result.stderr.decode(errors='ignore')[-200:]}"
                )
                return None
            except subprocess.TimeoutExpired:
                logger.error("ffmpeg timed out")
                return None
            except Exception as e:
                logger.error(f"ffmpeg error: {e}")
                return None

        def _run() -> Optional[tuple[bytes, str]]:
            base_args = [
                ffmpeg_exe,
                "-user_agent", _USER_AGENT,
                "-headers", f"Referer: {_REFERER}",
                "-t", str(duration),
                "-i", url,
            ]

            data = _run_cmd(base_args + ["-c", "copy", "-f", "webm", "pipe:1"])
            if data is None:
                # CDN returned 404/5XX — don't waste a second request
                return None

            size_kb = len(data) // 1024
            if len(data) <= _MAX_CLIP_BYTES:
                logger.info(f"Clip ready (copy): {size_kb} KB — {url}")
                return data, "webm"

            # Copy succeeded but file is too large: re-encode to fit Discord limit
            logger.warning(f"Clip too large ({size_kb} KB), re-encoding…")
            data = _run_cmd(base_args + [
                "-vf", "scale=-2:720",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
                "-c:a", "aac", "-b:a", "96k",
                "-f", "mp4", "-movflags", "frag_keyframe+empty_moov",
                "pipe:1",
            ])
            if data and len(data) <= _MAX_CLIP_BYTES:
                logger.info(f"Clip ready (re-encoded): {len(data) // 1024} KB — {url}")
                return data, "mp4"

            logger.warning(f"Re-encoded clip still too large, skipping")
            return None

        loop = asyncio.get_event_loop()
        try:
            return await asyncio.wait_for(loop.run_in_executor(None, _run), timeout=90)
        except asyncio.TimeoutError:
            logger.error("Clip executor timed out")
            return None
