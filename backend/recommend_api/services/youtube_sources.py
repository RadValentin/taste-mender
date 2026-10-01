import logging, requests
from datetime import timedelta
from requests import Response
from django.core.cache import cache
from django.db.models import F
from django.utils import timezone
from dotenv import dotenv_values
from music_recommendation.settings import (
    APP_AUTHOR_EMAIL,
    APP_NAME,
    APP_VERSION,
    BASE_DIR,
    YOUTUBE_SOURCE_CACHE_DAYS,
)
from recommend_api.models import Track, TrackSource
from typing import Dict

log = logging.getLogger(__name__)

# YT API URLs
YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
# Timeout for when a source for a track isn't found through YT /search/
SOURCE_LOOKUP_FAILURE_TTL = timedelta(hours=24)
# Short timeout for YT API outages
YOUTUBE_API_ERROR_CACHE_KEY = "youtube:api_error"
YOUTUBE_API_ERROR_TTL = 60
OUTBOUND_USER_AGENT = f"{APP_NAME}/{APP_VERSION} ({APP_AUTHOR_EMAIL})"


def get_youtube_source(track: Track) -> TrackSource | None:
    """
    Returns a playable YouTube source for a Track and manages DB caching for sources.

    - If source is in cache and not stale, return it directly without querying YT.
    - If the source is out of date (stale), refresh its metadata by querying YT `/videos/`.
    If video has been removed or is not embeddable, fall back to search.
    - If the video is missing, query YT `/search/` for a source.

    Searching YT massively drains API quota so a failed search for a source results in a 24h
    timeout on future requests. Sources that fail on the first attempt will be stored without their
    metadata.
    """
    cached_source = TrackSource.objects.filter(
        track=track,
        provider=TrackSource.Provider.YOUTUBE,
    ).first()

    is_cached = cached_source is not None
    is_invalid = (
        is_cached and
        cached_source.last_lookup_failed_at is not None
    )
    is_stale = (
        is_cached and
        timezone.now() - cached_source.refreshed_at > timedelta(days=YOUTUBE_SOURCE_CACHE_DAYS)
    )

    # If source is in DB cache and it's not stale, return it.
    if is_cached and not is_invalid and not is_stale:
        TrackSource.objects.filter(pk=cached_source.pk).update(
            source_request_count=F("source_request_count") + 1,
        )
        cached_source.refresh_from_db()
        return cached_source

    # Check that YT API key is present in config
    config: Dict[str, str | None] = dotenv_values(BASE_DIR / ".env")
    YOUTUBE_API_KEY = config.get("YOUTUBE_API_KEY")

    if not YOUTUBE_API_KEY:
        raise RuntimeError("Missing YOUTUBE_API_KEY")

    # In case a recent call to YT API failed, pause all requests to it for a while.
    if cache.get(YOUTUBE_API_ERROR_CACHE_KEY):
        if cached_source:
            TrackSource.objects.filter(pk=cached_source.pk).update(
                source_request_count=F("source_request_count") + 1,
            )
        log.warning("Skipping YouTube request while API outage circuit is open")
        return None

    # If source is out of date, ping YT to check that video is still up and update metadata.
    if is_cached and not is_invalid and is_stale:
        try:
            response: Response = requests.get(YOUTUBE_VIDEOS_URL, params={
                "part": "snippet,status,id",
                "id": cached_source.source_id,
                "key": YOUTUBE_API_KEY
            }, headers={"User-Agent": OUTBOUND_USER_AGENT}, timeout=8)
            response.raise_for_status()
        except requests.RequestException:
            # We couldn't verify it, but we also don't know that it's invalid.
            TrackSource.objects.filter(pk=cached_source.pk).update(
                source_request_count=F("source_request_count") + 1,
            )
            cache.set(YOUTUBE_API_ERROR_CACHE_KEY, True, timeout=YOUTUBE_API_ERROR_TTL)
            # A stale source should not be returned to stay compliant with YT API terms.
            log.warning(
                "YouTube source verification failed for stale track=%s; returning no source",
                track.pk,
                exc_info=True,
            )
            return None

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
                log.info("Refreshed YouTube source for track=%s", track.pk)
                return cached_source

    # If a source search failed recently, prevent duplicate requests for a while.
    if (
        is_cached and
        cached_source.last_lookup_failed_at and
        timezone.now() - cached_source.last_lookup_failed_at < SOURCE_LOOKUP_FAILURE_TTL
    ):
        TrackSource.objects.filter(pk=cached_source.pk).update(
            source_request_count=F("source_request_count") + 1,
        )
        log.debug("Skipping YouTube search during failure cooldown for track=%s", track.pk)
        return None

    # Source is either missing from the DB cache or unavailable on YT so search for a new video on YT.
    artist = track.artists.first()
    artist_name: str = getattr(artist, "name", "") or ""
    query: str = f"{track.title} {artist_name}".strip()

    try:
        response: Response = requests.get(YOUTUBE_SEARCH_URL, params={
            "part": "snippet",
            "q": query,
            "videoEmbeddable": "true",
            "type": "video",
            "maxResults": 10,
            "key": YOUTUBE_API_KEY
        }, headers={"User-Agent": OUTBOUND_USER_AGENT}, timeout=8)
        response.raise_for_status()
    except requests.RequestException:
        if cached_source:
            TrackSource.objects.filter(pk=cached_source.pk).update(
                source_request_count=F("source_request_count") + 1,
            )
        cache.set(YOUTUBE_API_ERROR_CACHE_KEY, True, timeout=YOUTUBE_API_ERROR_TTL)
        log.warning(
            "YouTube source search failed for track=%s",
            track.pk,
            exc_info=True,
        )
        return None

    results: list[dict] = response.json().get("items", [])

    if not results:
        # If the video wasn't found, create a empty cache entry or update existing one
        # and set a failure timestamp.
        cached_source, created = TrackSource.objects.update_or_create(
            track=track,
            provider=TrackSource.Provider.YOUTUBE,
            defaults={
                "source_id": None,
                "title": None,
                "channel": None,
                "thumbnail": None,
                "url": None,
                "last_lookup_failed_at": timezone.now(),
            },
        )
        if not created:
            TrackSource.objects.filter(pk=cached_source.pk).update(
                source_request_count=F("source_request_count") + 1,
            )
        log.info("No YouTube source found for track=%s", track.pk)
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
            "last_lookup_failed_at": None,
        },
    )

    # Increment request count when refreshing a stale source
    if (not created):
        TrackSource.objects.filter(pk=cached_source.pk).update(
            source_request_count=F("source_request_count") + 1,
            refreshed_at=timezone.now(),
            last_lookup_failed_at=None
        )
        cached_source.refresh_from_db()

    log.info("Cached YouTube source for track=%s", track.pk)
    return cached_source
