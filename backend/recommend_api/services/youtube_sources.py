import requests
from datetime import timedelta
from requests import Response
from django.db.models import F
from django.utils import timezone
from dotenv import dotenv_values
from music_recommendation.settings import BASE_DIR, YOUTUBE_SOURCE_CACHE_DAYS
from recommend_api.models import Track, TrackSource
from typing import Dict

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"


def get_youtube_source(track: Track) -> TrackSource | None:
    """
    Returns a playable YouTube source for a Track.
    Tries to locate the source in DB cache. If it's missing, does a YT search.
    If it's stale, re-pings YT to check that the video is still up and refreshes metadata.
    """
    cached_source = TrackSource.objects.filter(
        track=track,
        provider=TrackSource.Provider.YOUTUBE,
    ).first()

    is_cached = cached_source is not None
    is_stale = (
        is_cached and
        timezone.now() - cached_source.refreshed_at > timedelta(days=YOUTUBE_SOURCE_CACHE_DAYS)
    )

    # If source is in DB cache and it's not stale, return it.
    if is_cached and not is_stale:
        TrackSource.objects.filter(pk=cached_source.pk).update(
            source_request_count=F("source_request_count") + 1,
        )
        cached_source.refresh_from_db()
        return cached_source

    config: Dict[str, str | None] = dotenv_values(BASE_DIR / ".env")
    YOUTUBE_API_KEY = config.get("YOUTUBE_API_KEY")

    if not YOUTUBE_API_KEY:
        raise RuntimeError("Missing YOUTUBE_API_KEY")

    # If source is out of date, ping YT to check that video is still up and update metadata.
    if is_cached and is_stale:
        response: Response = requests.get(YOUTUBE_VIDEOS_URL, params={
            "part": "snippet,status,id",
            "id": cached_source.source_id,
            "key": YOUTUBE_API_KEY
        }, timeout=8)
        response.raise_for_status()

        items = response.json().get("items", [])

        # If the source is still up and still embeddable, refresh its metadata.
        # Otherwise we'll assume the source as missing.
        if items:
            source = items[0]
            video_id = source["id"]

            if source and (source.get("status", {}).get("embeddable", False) is True):
                TrackSource.objects.filter(pk=cached_source.pk).update(
                    track=track,
                    provider=TrackSource.Provider.YOUTUBE,
                    source_id=video_id,
                    title=source["snippet"]["title"],
                    channel=source["snippet"]["channelTitle"],
                    thumbnail=source["snippet"]["thumbnails"]["medium"]["url"],
                    url=f"https://www.youtube.com/watch?v={video_id}",
                    source_request_count=F("source_request_count") + 1,
                    refreshed_at=timezone.now(),
                )

                cached_source.refresh_from_db()
                return cached_source

    # Source is either missing from the DB cache or unavailable on YT so search for a new video on YT.
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

    cached_source, created = TrackSource.objects.update_or_create(
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

    # Increment request count when refreshing a stale source
    if (not created):
        TrackSource.objects.filter(pk=cached_source.pk).update(
            source_request_count=F("source_request_count") + 1,
            refreshed_at=timezone.now()
        )
        cached_source.refresh_from_db()

    return cached_source
