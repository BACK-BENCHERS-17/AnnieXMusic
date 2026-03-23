"""
YouTube Data API v3 — fast async helpers.
Used for search and video metadata when YOUTUBE_API_KEY is set.
Falls back gracefully to youtubesearchpython / yt-dlp when key is missing.
"""

import asyncio
import time
from typing import Dict, List, Optional

import aiohttp

_YT_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
_YT_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"

_search_cache: Dict[str, tuple] = {}
_search_lock = asyncio.Lock()
_SEARCH_TTL = 300


def _get_api_key() -> str:
    try:
        from config import YOUTUBE_API_KEY
        return YOUTUBE_API_KEY or ""
    except Exception:
        return ""


def _iso8601_to_seconds(duration: str) -> int:
    """Convert ISO 8601 duration (PT4M13S) to seconds."""
    import re
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration or "")
    if not match:
        return 0
    h = int(match.group(1) or 0)
    m = int(match.group(2) or 0)
    s = int(match.group(3) or 0)
    return h * 3600 + m * 60 + s


def _seconds_to_min(secs: int) -> str:
    if not secs:
        return "0:00"
    return f"{secs // 60}:{secs % 60:02d}"


async def yt_api_search(query: str, max_results: int = 10) -> List[Dict]:
    """
    Search YouTube using Data API v3.
    Returns list of dicts: {id, title, channel, duration, thumb}
    Very fast (~200ms) compared to yt-dlp search (~2-5s).
    """
    api_key = _get_api_key()
    if not api_key:
        return []

    cache_key = f"{query}:{max_results}"
    now = time.time()

    async with _search_lock:
        cached = _search_cache.get(cache_key)
        if cached and now - cached[0] < _SEARCH_TTL:
            return cached[1]

    try:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=8)
        ) as session:
            search_params = {
                "key": api_key,
                "q": query,
                "part": "snippet",
                "type": "video",
                "maxResults": min(max_results, 50),
                "videoCategoryId": "10",
            }
            async with session.get(_YT_SEARCH_URL, params=search_params) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()

            items = data.get("items", [])
            if not items:
                return []

            video_ids = [item["id"]["videoId"] for item in items if item.get("id", {}).get("videoId")]
            if not video_ids:
                return []

            detail_params = {
                "key": api_key,
                "id": ",".join(video_ids),
                "part": "contentDetails,snippet",
            }
            async with session.get(_YT_VIDEOS_URL, params=detail_params) as resp:
                if resp.status != 200:
                    detail_data = {"items": []}
                else:
                    detail_data = await resp.json()

            detail_map: Dict[str, Dict] = {}
            for v in detail_data.get("items", []):
                vid = v["id"]
                duration_iso = v.get("contentDetails", {}).get("duration", "")
                secs = _iso8601_to_seconds(duration_iso)
                detail_map[vid] = {
                    "duration_sec": secs,
                    "duration": _seconds_to_min(secs),
                }

            results = []
            for item in items:
                vid = item.get("id", {}).get("videoId", "")
                if not vid:
                    continue
                snippet = item.get("snippet", {})
                title = snippet.get("title", "Unknown")
                channel = snippet.get("channelTitle", "")
                thumb = (
                    snippet.get("thumbnails", {}).get("medium", {}).get("url")
                    or snippet.get("thumbnails", {}).get("default", {}).get("url")
                    or f"https://img.youtube.com/vi/{vid}/mqdefault.jpg"
                )
                d = detail_map.get(vid, {})
                results.append({
                    "id": vid,
                    "title": title,
                    "channel": channel,
                    "duration": d.get("duration", "0:00"),
                    "duration_sec": d.get("duration_sec", 0),
                    "thumb": thumb,
                    "url": f"https://www.youtube.com/watch?v={vid}",
                })

        async with _search_lock:
            if len(_search_cache) > 200:
                _search_cache.clear()
            _search_cache[cache_key] = (time.time(), results)

        return results

    except Exception:
        return []


async def yt_api_video_details(video_id: str) -> Optional[Dict]:
    """
    Get video metadata via YouTube Data API v3.
    Returns dict with title, channel, duration, duration_sec, thumb, url.
    """
    api_key = _get_api_key()
    if not api_key or not video_id:
        return None

    try:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=8)
        ) as session:
            params = {
                "key": api_key,
                "id": video_id,
                "part": "snippet,contentDetails",
            }
            async with session.get(_YT_VIDEOS_URL, params=params) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()

        items = data.get("items", [])
        if not items:
            return None

        v = items[0]
        snippet = v.get("snippet", {})
        duration_iso = v.get("contentDetails", {}).get("duration", "")
        secs = _iso8601_to_seconds(duration_iso)
        thumb = (
            snippet.get("thumbnails", {}).get("medium", {}).get("url")
            or f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"
        )
        return {
            "id": video_id,
            "title": snippet.get("title", "Unknown"),
            "channel": snippet.get("channelTitle", ""),
            "duration": _seconds_to_min(secs),
            "duration_sec": secs,
            "thumb": thumb,
            "url": f"https://www.youtube.com/watch?v={video_id}",
        }
    except Exception:
        return None


def is_api_available() -> bool:
    """Return True if YOUTUBE_API_KEY is configured."""
    return bool(_get_api_key())
