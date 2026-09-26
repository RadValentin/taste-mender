import requests
from datetime import timedelta
from requests import Response
from django.utils import timezone
from dotenv import dotenv_values
from music_recommendation.settings import BASE_DIR
from recommend_api.models import Track, TrackSource
from typing import Dict

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"


def get_youtube_source(track: Track) -> TrackSource | None:
    cached_source = TrackSource.objects.filter(
        track=track,
        provider=TrackSource.Provider.YOUTUBE,
    ).first()

    is_stale = (
        cached_source is None
        or timezone.now() - cached_source.refreshed_at > timedelta(days=30)
    )

    if is_stale:
        # Source not found in DB or is stale
        config: Dict[str, str | None] = dotenv_values(BASE_DIR / ".env")
        YOUTUBE_API_KEY = config.get("YOUTUBE_API_KEY")

        if not YOUTUBE_API_KEY:
            raise RuntimeError("Missing YOUTUBE_API_KEY")

        artist = track.artists.first()
        artist_name: str = getattr(artist, "name", "") or ""
        query: str = f"{track.title} {artist_name}".strip()

        response: Response = requests.get(YOUTUBE_SEARCH_URL, params={
            "part": "snippet",
            "q": query,
            "videoEmbeddable": "true",
            "type": "video",
            "maxResults": 10,
            "key": YOUTUBE_API_KEY
        }, timeout=8)
        response.raise_for_status()

        results: list[dict] = response.json().get("items", [])

        if not results:
            return None

        source: dict = results[0]
        video_id = source["id"]["videoId"]

        cached_source, _ = TrackSource.objects.update_or_create(
            track=track,
            provider=TrackSource.Provider.YOUTUBE,
            defaults={
                "source_id": video_id,
                "title": source["snippet"]["title"],
                "channel": source["snippet"]["channelTitle"],
                "thumbnail": source["snippet"]["thumbnails"]["medium"]["url"],
                "url": f"https://www.youtube.com/watch?v={video_id}",
            },
        )

    return cached_source