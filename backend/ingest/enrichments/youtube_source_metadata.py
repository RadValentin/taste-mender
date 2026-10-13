import os, orjson, time, logging, re, asyncio
import unicodedata
from asgiref.sync import sync_to_async
from datetime import datetime, timedelta
from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from py_yt import VideosSearch
from py_yt.exceptions import PyYTSearchError
from random import random
from recommend_api.models import Track
from rapidfuzz import fuzz
from typing import Any

log = logging.getLogger(__name__)


OUTPUT_FILENAME = os.path.join(
    settings.BASE_DIR, "ingest", "enrichments", "youtube_track_metadata.json"
)
TEMP_FILENAME = os.path.join(
    settings.BASE_DIR, "ingest", "enrichments", "youtube_track_metadata.temp.json"
)
YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
MAX_CONSECUTIVE_ERRORS = 5


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


class Counters:
    """Utility class"""
    # Count errors so we can abort after a certain number of them.
    repeaded_errors: int = 0
    current_run_checked: int = 0
    all_runs_checked: int = 0

async def search_youtube(query: str) -> dict[str, Any] | None:
    """Return the first YouTube search result title for ``query``."""
    log.info(f"- Searching for {query}")
    try:
        search = VideosSearch(query, limit=1)
        response: dict[str, Any] = await search.next()
        items = response.get("result", [])
    except (PyYTSearchError, OSError, ValueError, TypeError) as ex:
        Counters.repeaded_errors += 1
        log.exception(f"YouTube search failed for {query!r}: {ex}")
        return None

    Counters.repeaded_errors = 0
    if not items or not isinstance(items, list):
        return None

    source = items[0]
    description_snippet = source.get("descriptionSnippet", [])
    description = (
        description_snippet[0].get("text")
        if (
            isinstance(description_snippet, list)
            and description_snippet
            and isinstance(description_snippet[0], dict)
        )
        else None
    )

    return {
        **source,
        "description": description,
    }


async def agather_youtube_metadata(data, target_tracks: list[Track]):
    """Async wrapper required in order to use `py-yt-search`"""

    # MBIDs of tracks which were enriched through title + artist search
    enriched_mbids: dict = data.get("sources", {})
    Counters.all_runs_checked = len(enriched_mbids)
    # ISRCs of tracks which were enriched though direct ISRC search
    enriched_isrcs: dict = data.get("isrcs", {})
    # Select the most popular tracks that either don't have a source or have a stale one

    for track in target_tracks:
        # Give up after encountering a certain number of errors
        # TODO: ensure there are "REPEATED" errors not transient ones
        if (Counters.repeaded_errors > MAX_CONSECUTIVE_ERRORS):
            return False

        Counters.current_run_checked += 1
        stop_requested = False
        artists = await sync_to_async(track.artists.all)()
        artists = [artist.name for artist in artists]
        artist_name = artists[0].name if artists[0] else ""
        log.info(
            "Checking track: %s by %s (%s)",
            track.title,
            artist_name if artist_name else "Unknown Artist",
            track.musicbrainz_recordingid,
        )

        # If one of the track's ISRC codes was previously searched, save the source.
        overlap_isrcs: set[dict] = set(track.isrc) & set(enriched_isrcs.keys())
        if len(overlap_isrcs) > 0:
            isrc = overlap_isrcs.pop()
            enriched_mbids[track.musicbrainz_recordingid] = {
                "search_type": "isrc",
                **enriched_isrcs.get(isrc, {})
            }
            continue

        # Attempt to search for the track by its ISRC codes
        # TODO: Ensure that not-found ISRCs are also indexed to prevent duplicate requests
        for isrc in track.isrc:
            result = await search_youtube(query=isrc)
            if result is None:
                continue
            if titles_are_for_same_track(
                track.title, result.get("title", ""), is_isrc=True
            ):
                enriched_mbids[track.musicbrainz_recordingid] = {
                    "search_type": "isrc",
                    **result
                }
                enriched_isrcs[isrc] = result
                stop_requested = True
                break
            else:
                log.warning(
                    'Title mismatch when searching by ISRC. Was searching for "%s" but found "%s".',
                    track.title,
                    result.get("title", "")
                )

        # If we still haven't found the source, try searching by title + artist
        if not stop_requested:
            title_artist_query = f"{track.title} {artist_name}".strip()
            result = await search_youtube(title_artist_query)
            if result is None:
                continue
            if titles_are_for_same_track(
                track.title, result.get("title", ""), is_isrc=False, artists=artists
            ):
                enriched_mbids[track.musicbrainz_recordingid] = {
                    "search_type": "title_artist",
                    **result
                }
            else:
                log.warning(
                    'Title mismatch when searching by title+artist. Was searching for "%s" but found "%s".',
                    track.title,
                    result.get("title", "")
                )

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

    # Update the enrichment file
    try:
        if os.path.exists(TEMP_FILENAME):
            with open(TEMP_FILENAME, "wb") as f:
                data["last_run_finished_at"] = datetime.now()
                f.write(orjson.dumps(data, option=orjson.OPT_INDENT_2))
            os.replace(TEMP_FILENAME, OUTPUT_FILENAME)
    except Exception as ex:
        log.exception("Could not write metadata to disk.")

    # Display stats before exiting
    log.info("The current run checked %s tracks", Counters.current_run_checked)
    log.info("Previous runs had checked %s tracks", Counters.all_runs_checked)

    return True


def gather_youtube_metadata(batch_size=1, override_file=False):
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

    # Create the output file if it doesn't exist
    if not os.path.exists(OUTPUT_FILENAME) or override_file:
        log.info("%s not found, will create it from scratch.", OUTPUT_FILENAME)
        try:
            with open(OUTPUT_FILENAME, "wb+") as f:
                output_json = {
                    "schema_version": 1,
                    "first_ran_at": datetime.now(),
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
            Q(sources__refreshed_at__lt=stale_timedelta) |
            Q(musicbrainz_recordingid__in=enriched_mbids.keys())
        ).prefetch_related("artists").order_by("-submissions")[:batch_size]
    )

    return asyncio.run(
        agather_youtube_metadata(data=data, target_tracks=target_tracks)
    )
