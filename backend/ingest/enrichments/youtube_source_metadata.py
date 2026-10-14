import os, orjson, time, logging, re, asyncio, requests
import unicodedata
from asgiref.sync import sync_to_async
from datetime import timedelta
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from enum import StrEnum
from py_yt import VideosSearch
from py_yt.exceptions import PyYTSearchError
from random import random
from recommend_api.models import Track, TrackSource
from rapidfuzz import fuzz
from typing import Any

log = logging.getLogger(__name__)


OUTPUT_FILENAME = os.path.join(
    settings.BASE_DIR, "ingest", "enrichments", "youtube_track_metadata.json"
)
TEMP_FILENAME = os.path.join(
    settings.BASE_DIR, "ingest", "enrichments", "youtube_track_metadata.temp.json"
)
MAX_CONSECUTIVE_ERRORS = 5
YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"


def normalize_text(title: str) -> str:
    if not title:
        return ""

    title = unicodedata.normalize("NFKC", title).lower()

    target_annotations = [
        "lyric video", "official video", "audio only", "remastered", "remaster",
        "official music video", "mono", "official audio", "audio", "acoustic / lyric video",
        "remix", "official hd video", "radio edit", "original official video", "official 4k video",
        "4k", "mono version", "album version", "video"
    ]
    phrases_regex = "|".join(re.escape(phrase) for phrase in target_annotations)
    pattern = rf"\s*(?:\([^()]*?(?:{phrases_regex})[^()]*?\)|\[[^\[\]]*?(?:{phrases_regex})[^\[\]]*?\])"
    title = re.sub(pattern, "", title, flags=re.I).strip()

    return title.strip()


def titles_are_for_same_track(
    original_title: str, comparison_title: str, is_isrc: bool = False, artists: list[str] | None = None
) -> tuple[bool, float]:
    """
    Checks if two titles are for the same track. Useful for checking if a YT search result matches
    a song in the DB. Artist names are taken into account.

    Args:
        original_title: the canonical title of the track
        comparison_title: candidate title for comparison
        artists: optional list of artists used in non-ISRC searches
        is_isrc: optional flag indicating that comparison_title was retrieved from a search by ISRC code
    """
    # Sanitization - strip extra terms
    original_title = normalize_text(original_title)
    comparison_title = normalize_text(comparison_title)

    if not original_title or not comparison_title:
        return False, 0.0

    # If the comparison_title was retrieved through an ISRC search it means that the record label
    # released the official video on YouTube and set the code in the video metadata.
    # We consider this a strong indicator of correctness and relax the search to a partial match.
    if (is_isrc):
        match_score = fuzz.partial_ratio(original_title, comparison_title)
        #print(f"ISRC match_score: {match_score}")
        return match_score > 80, match_score

    # Otherwise, the search was made for title + artist, not a strong indicator of correctness
    # - We don't have a strong indicator of correctness. If the artist is present, include it when matching strings.
    # - It's not clear what we should do for single word songs so if the original is a single word, we need to strictly match it against the result
    else:
        artists = list(map(normalize_text, artists)) if artists is not None else []
        all_artists = " ".join(artists).strip()
        artist_first_match_score = fuzz.partial_ratio(
            f"{all_artists} {original_title}", comparison_title
        )
        artist_last_match_score = fuzz.partial_ratio(
            f"{original_title} {all_artists}", comparison_title
        )
        #print(f"Search match_score: {artist_first_match_score}, {artist_last_match_score}")
        match_score = max(artist_first_match_score, artist_last_match_score)

        return match_score > 80, match_score


class SearchStatus(StrEnum):
    FOUND = "found"
    EMPTY = "empty"
    MISMATCH = "mismatch"
    ERROR = "error"


async def search_youtube(query: str, is_isrc: bool = False) -> dict[str, Any]:
    """Return a playable YouTube source for a `query`."""
    log.info(f"- Searching for {query}")
    try:
        search = VideosSearch(query, limit=1)
        search_response: dict[str, Any] = await search.next()
        items = search_response.get("result", [])
    except (PyYTSearchError, OSError, ValueError, TypeError) as ex:
        log.exception("YouTube search failed for %s", query)
        return {
            "query": query,
            "search_type": "isrc" if is_isrc else "title_artist",
            "search_status": SearchStatus.ERROR,
            "meta": None,
            "checked_at": timezone.now(),
            "error": {
                "type": type(ex).__name__,
                "message": str(ex),
            }
        }

    # Check for empty response
    if (
        not items
        or not isinstance(items, list)
        or not items[0]
        or not items[0].get("id")
    ):
        return {
            "query": query,
            "search_type": "isrc" if is_isrc else "title_artist",
            "search_status": SearchStatus.EMPTY,
            "meta": None,
            "checked_at": timezone.now(),
            "error": None
        }

    # Check if video is embeddable
    video_id = items[0].get("id")
    try:
        video_response = requests.get(YOUTUBE_VIDEOS_URL, params={
            "part": "status",
            "id": video_id,
            "key": settings.YOUTUBE_API_KEY,
        }, headers={"User-Agent": settings.OUTBOUND_USER_AGENT}, timeout=8)
        video_response.raise_for_status()
        video_items = video_response.json().get("items", [])
    except (requests.RequestException, ValueError, TypeError, AttributeError) as ex:
        log.exception("Could not check YouTube video %s for %s", video_id, query)
        return {
            "query": query,
            "search_type": "isrc" if is_isrc else "title_artist",
            "search_status": SearchStatus.ERROR,
            "meta": items[0],
            "checked_at": timezone.now(),
            "error": {
                "type": type(ex).__name__,
                "message": str(ex),
            }
        }

    if (
        not isinstance(video_items, list)
        or not video_items
        or not isinstance(video_items[0], dict)
        or video_items[0].get("status", {}).get("embeddable") is not True
    ):
        log.info("YouTube video %s is not embeddable", video_id)
        return {
            "query": query,
            "search_type": "isrc" if is_isrc else "title_artist",
            "search_status": SearchStatus.ERROR,
            "meta": items[0],
            "checked_at": timezone.now(),
            "error": {
                "type": "VideoNotEmbeddable",
                "message": f"YouTube video {video_id} is not embeddable",
            }
        }

    return {
        "query": query,
        "search_type": "isrc" if is_isrc else "title_artist",
        "search_status": SearchStatus.FOUND,
        "meta": items[0],
        "checked_at": timezone.now(),
        "error": None
    }


async def agather_youtube_metadata(data, target_tracks: list[Track]):
    """Async wrapper required in order to use `py-yt-search`"""

    class Counters:
        """Utility class"""
        # Count errors so we can abort after a certain number of them.
        repeated_errors: int = 0
        # How many times was a source retrieved from isrc dict instead of search.
        cache_hits: int = 0
        isrc_searches: int = 0
        title_artist_searches: int = 0
        current_run_checked: int = 0
        all_runs_checked: int = 0

    # MBIDs of tracks which were enriched through title + artist search
    enriched_mbids: dict = data.get("sources", {})
    Counters.all_runs_checked = len(enriched_mbids)
    # ISRCs of tracks which were enriched though direct ISRC search
    enriched_isrcs: dict = data.get("isrcs", {})
    # Select the most popular tracks that either don't have a source or have a stale one

    for track in target_tracks:
        # Give up after encountering a certain number of repeated errors
        if (Counters.repeated_errors >= MAX_CONSECUTIVE_ERRORS):
            return False

        Counters.current_run_checked += 1
        stop_requested = False
        artists = await sync_to_async(
            lambda: [normalize_text(artist.name) for artist in track.artists.all()]
        )()
        all_artists_str = " ".join(artists).strip() if artists else ""
        log.info(
            "Checking track: %s by %s (%s)",
            track.title,
            all_artists_str if all_artists_str else "Unknown Artist",
            track.musicbrainz_recordingid,
        )

        # If one of the track's ISRC codes was previously searched, save the source.
        valid_enriched_isrcs = {
            k
            for k, v in enriched_isrcs.items()
            if isinstance(v, dict) and v.get("search_status") == SearchStatus.FOUND.value
        }
        overlap_isrcs: set[str] = set(track.isrc) & valid_enriched_isrcs
        if len(overlap_isrcs) > 0:
            isrc = overlap_isrcs.pop()
            enriched_mbids[track.musicbrainz_recordingid] = enriched_isrcs.get(isrc, {})
            Counters.cache_hits += 1
            continue

        # Attempt to search for the track by its ISRC codes
        for isrc in track.isrc:
            # If previous ISRC search returned invalid or no results, don't check again
            cached_result = enriched_isrcs.get(isrc)
            if cached_result and cached_result.get("search_status") in (
                SearchStatus.EMPTY,
                SearchStatus.MISMATCH,
            ):
                continue

            result = await search_youtube(query=isrc, is_isrc=True)
            Counters.isrc_searches += 1

            if result.get("search_status") is SearchStatus.ERROR:
                Counters.repeated_errors += 1
                continue
            else:
                Counters.repeated_errors = 0

            if result.get("search_status") is SearchStatus.FOUND:
                result_title = result.get("meta", {}).get("title", "")
                if titles_are_for_same_track(
                    track.title, result_title, is_isrc=True
                ):
                    enriched_mbids[track.musicbrainz_recordingid] = result
                    enriched_isrcs[isrc] = result
                    stop_requested = True
                    break
                else:
                    # Ensure that invalid responses are indexed to prevent duplicate requests
                    enriched_isrcs[isrc] = {
                        **result,
                        "search_status": SearchStatus.MISMATCH
                    }
                    log.warning(
                        'Title mismatch when searching by ISRC. Was searching for "%s" but found "%s".',
                        track.title,
                        result_title
                    )
            else:
                # Ensure that empty responses are indexed to prevent duplicate requests
                enriched_isrcs[isrc] = result

        # If we still haven't found the source, try searching by title + artist
        if not stop_requested:
            title_artist_query = f"{track.title} {all_artists_str}".strip()
            result = await search_youtube(title_artist_query, is_isrc=False)
            Counters.title_artist_searches += 1

            if result.get("search_status") is SearchStatus.ERROR:
                Counters.repeated_errors += 1
                continue
            else:
                Counters.repeated_errors = 0

            if result.get("search_status") is SearchStatus.FOUND:
                result_title = result.get("meta", {}).get("title", "")
                if titles_are_for_same_track(
                    track.title, result_title, is_isrc=False, artists=artists
                ):
                    enriched_mbids[track.musicbrainz_recordingid] = result
                else:
                    enriched_mbids[track.musicbrainz_recordingid] = {
                        **result,
                        "search_status": SearchStatus.MISMATCH
                    }
                    log.warning(
                        'Title mismatch when searching by title+artist. Was searching for "%s" but found "%s".',
                        track.title,
                        result_title
                    )
            else:
                # Ensure that empty responses are indexed to prevent duplicate requests
                enriched_mbids[track.musicbrainz_recordingid] = result


        # Write to file
        data["sources"] = enriched_mbids
        data["isrcs"] = enriched_isrcs

        try:
            with open(TEMP_FILENAME, "wb+") as f:
                f.write(orjson.dumps(data, option=orjson.OPT_INDENT_2))
        except Exception as ex:
            log.exception(
                "Could not write metadata to temp file for track %s.",
                track.musicbrainz_recordingid
            )

        # Wait a bit before making the next request
        time.sleep(1 + (random() * 4))

    # Replace the old output file with the temp file generated by this run.
    try:
        if os.path.exists(TEMP_FILENAME):
            with open(TEMP_FILENAME, "wb") as f:
                data["last_run_finished_at"] = timezone.now()
                f.write(orjson.dumps(data, option=orjson.OPT_INDENT_2))
            os.replace(TEMP_FILENAME, OUTPUT_FILENAME)
    except Exception as ex:
        log.exception("Could not write metadata to disk.")

    # Display stats before exiting
    log.info("The current run checked %s tracks", Counters.current_run_checked)
    log.info("- %s sources were already in the JSON file", Counters.cache_hits)
    log.info("- ran %s YT searches for ISRC codes ", Counters.isrc_searches)
    log.info("- ran %s YT searches for title + artist queries ", Counters.title_artist_searches)
    log.info("Previous runs had checked %s tracks", Counters.all_runs_checked)

    return True


def gather_youtube_metadata(batch_size, override_file=False):
    """
    Builds a JSON file with video data from YouTube for the Tracks with most submissions.
    It can be used to prefill the TrackSource model. The file contains two main dictionaries:
    - `sources` - maps a MBID to a YT video (these are the actual sources)
    - `isrcs` - maps an ISRC to a YT video (useful for preventing duplicate requests when searching by ISRC)

    Notes:
    - Repeated calls will append more sources to the existing file, unless `override_file` is used.
    - Video data is only saved if its title matches the title in Track model.
    - Not all ISRCs have matching YouTube videos.
    - Official videos that are found by ISRC have "Provided to YouTube by" in description.

    Args:
        batch_size: how many tracks to check
        override_file: If true, build the output file from scratch on every run
    """

    # Check that YT API key is present in config
    if not settings.YOUTUBE_API_KEY:
        raise RuntimeError("Missing YOUTUBE_API_KEY")

    # Create the output file if it doesn't exist
    if not os.path.exists(OUTPUT_FILENAME) or override_file:
        log.info("%s not found, will create it from scratch.", OUTPUT_FILENAME)
        try:
            with open(OUTPUT_FILENAME, "wb+") as f:
                output_json = {
                    "schema_version": 1,
                    "first_ran_at": timezone.now(),
                    "last_run_finished_at": None,
                    "sources": {},
                    "isrcs": {}
                }
                count = f.write(orjson.dumps(output_json))
                log.info("Created %s (%s bytes).", OUTPUT_FILENAME, count)

        except Exception as ex:
            os.remove(OUTPUT_FILENAME)
            log.exception("Could not create file, aborting.")
            return

    # Load enrichment data from disk
    log.info("Loading enrichment data from disk.")
    try:
        with open(OUTPUT_FILENAME, "rb") as f:
            bytes = f.read()
            data: dict[str, Any] = orjson.loads(bytes)
    except Exception as ex:
        log.exception("Could not load enrichment data from disk.")
        return False

    log.info("Will begin searching for playable sources on YouTube.")
    # MBIDs of tracks which were enriched through title + artist search
    enriched_mbids: dict = data.get("sources", {})
    # Select the most popular tracks that either don't have a source or have a stale one
    stale_timedelta = timezone.now() - timedelta(days=settings.YOUTUBE_SOURCE_CACHE_DAYS)
    target_tracks: list[Track] = list(
        Track.objects.exclude(
            Q(sources__refreshed_at__gte=stale_timedelta) |
            Q(musicbrainz_recordingid__in=enriched_mbids.keys())
        ).prefetch_related("artists").order_by("-submissions")[:batch_size]
    )

    return asyncio.run(
        agather_youtube_metadata(data=data, target_tracks=target_tracks)
    )


def load_youtube_metadata():
    if not os.path.exists(OUTPUT_FILENAME):
        log.error("%s not found, cannot continue.", OUTPUT_FILENAME)
        return False

    with open(OUTPUT_FILENAME, "rb") as f:
        bytes = f.read()
        try:
            data: dict[str, Any] = orjson.loads(bytes)
        except orjson.JSONDecodeError as ex:
            log.exception("Error parsing JSON, cannot continue.")
            return False

    json_sources: dict[str, dict] = data.get("sources", {})
    # filter to only the sources for which we have a valid result
    found_sources = {
        k: v
        for k, v in json_sources.items()
        if isinstance(v, dict) and v.get("search_status") == SearchStatus.FOUND.value
    }

    with transaction.atomic():
        for mbid, source in found_sources.items():
            if not isinstance(source, dict):
                log.warning("Invalid source data for track %s", mbid)
                continue

            track = Track.objects.filter(musicbrainz_recordingid=mbid).prefetch_related("artists").first()

            if track is None:
                log.warning("Track with MBID %s not found in database.", mbid)
                continue

            artist = track.artists.first()
            log.info(
                "Updating source for track: %s by %s (%s)",
                track.title,
                artist.name if artist else "Unknown Artist",
                track.musicbrainz_recordingid,
            )

            meta = source.get("meta")
            if not isinstance(meta, dict):
                log.warning("Missing metadata for track %s", mbid)
                continue
            source_id = meta.get("id", None)
            title = meta.get("title", None)
            channel_data = meta.get("channel")
            channel = (
                channel_data.get("name")
                if isinstance(channel_data, dict)
                else None
            )
            thumbnails = meta.get("thumbnails")
            thumbnail = (
                thumbnails[0].get("url")
                if isinstance(thumbnails, list)
                and thumbnails
                and isinstance(thumbnails[0], dict)
                else None
            )
            url = meta.get("link", None)

            TrackSource.objects.update_or_create(
                track=track,
                provider=TrackSource.Provider.YOUTUBE,
                defaults={
                    "source_id": source_id,
                    "title": title,
                    "channel": channel,
                    "thumbnail": thumbnail,
                    "url": url or f"https://www.youtube.com/watch?v={source_id}",
                    "refreshed_at": timezone.now(),
                    "last_lookup_failed_at": None
                }
            )

    return True
