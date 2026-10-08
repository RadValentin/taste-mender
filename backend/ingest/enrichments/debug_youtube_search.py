import asyncio
import os, sys, django
from pathlib import Path
from typing import Any
from asgiref.sync import sync_to_async

import orjson
from py_yt import VideosSearch
from py_yt.exceptions import PyYTSearchError

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "music_recommendation.settings")
django.setup()

from django.conf import settings
from recommend_api.models import Track


METADATA_FILENAME = Path(settings.BASE_DIR) / "ingest" / "enrichments" / (
    "musicbrainz_track_metadata.json"
)
RESULTS_FILENAME = Path(settings.BASE_DIR) / "ingest" / "enrichments" / (
    "debug_youtube_search_results.json"
)
SEARCH_DELAY_SECONDS = 1
MAX_CONSECUTIVE_ERRORS = 5


def load_existing_results(
    results_filename: os.PathLike[str] | str,
) -> dict[str, dict[str, Any]]:
    """Load previous results, migrating the original list-shaped artifact."""
    if not os.path.exists(results_filename):
        return {}

    with open(results_filename, "rb") as results_file:
        output: dict[str, Any] = orjson.loads(results_file.read())

    tracks = output.get("tracks", {})
    if isinstance(tracks, list):
        return {
            result["mbid"]: result
            for result in tracks
            if isinstance(result, dict) and isinstance(result.get("mbid"), str)
        }
    if not isinstance(tracks, dict):
        raise ValueError("The results artifact 'tracks' must be an object or list.")

    return tracks


def skipped_search_result() -> dict[str, Any]:
    return {
        "title": None,
        "description": None,
        "error": "search skipped after consecutive errors",
    }


def save_results(
    results_filename: os.PathLike[str] | str,
    metadata_filename: os.PathLike[str] | str,
    results: dict[str, dict[str, Any]],
) -> None:
    output = {
        "schema_version": 1,
        "metadata_file": str(metadata_filename),
        "tracks": results,
    }
    with open(results_filename, "wb") as results_file:
        results_file.write(orjson.dumps(output, option=orjson.OPT_INDENT_2))


async def search_youtube(query: str) -> dict[str, Any]:
    """Return the first YouTube search result title for ``query``."""
    print(f"- Searching for {query}")
    try:
        search = VideosSearch(query, limit=1)
        response: dict[str, Any] = await search.next()
        items = response.get("result", [])
    except (PyYTSearchError, OSError, ValueError, TypeError) as ex:
        print(f"YouTube search failed for {query!r}: {ex}")
        return {"title": None, "description": None, "error": str(ex)}
    finally:
        await asyncio.sleep(SEARCH_DELAY_SECONDS)

    if not items:
        return {"title": None, "description": None, "error": None}

    description_snippet = items[0].get("descriptionSnippet")
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
        "title": items[0].get("title"),
        "description": description,
        "error": None,
    }


def debug_youtube_search(
    metadata_filename: os.PathLike[str] | str = METADATA_FILENAME,
    results_filename: os.PathLike[str] | str = RESULTS_FILENAME,
    batch_size: int = 5,
) -> bool:
    """Search YouTube for a maximum of ``batch_size`` new tracks."""
    with open(metadata_filename, "rb") as metadata_file:
        data: dict[str, Any] = orjson.loads(metadata_file.read())

    metadata_tracks: dict[str, dict[str, Any]] = data.get("tracks", {})
    tracks: list[Track] = list(Track.objects.filter(
        musicbrainz_recordingid__in=metadata_tracks
    ).prefetch_related("artists"))

    return asyncio.run(
        _debug_youtube_search(
            metadata_filename,
            results_filename,
            metadata_tracks,
            tracks,
            batch_size,
        )
    )


async def _debug_youtube_search(
    metadata_filename: os.PathLike[str] | str,
    results_filename: os.PathLike[str] | str,
    metadata_tracks: dict[str, dict[str, Any]],
    tracks: list[Track],
    batch_size: int,
) -> bool:
    """Run all searches and write the comparison artifact."""

    results = load_existing_results(results_filename)
    tracks_processed = 0
    consecutive_errors = 0
    stop_requested = False
    for track in tracks:
        if tracks_processed >= batch_size or stop_requested:
            break

        mbid = track.musicbrainz_recordingid
        if mbid in results:
            continue

        metadata = metadata_tracks[track.musicbrainz_recordingid]
        afirst = sync_to_async(track.artists.first)
        artist = await afirst()
        artist_name = artist.name if artist else ""
        title_artist_query = f"{track.title} {artist_name}".strip()
        print(f"Processing track {track.title} {track.musicbrainz_recordingid}")

        isrc_results: dict[str, dict[str, Any]] = {}
        for isrc in dict.fromkeys(metadata.get("isrcs", [])):
            search_result = await search_youtube(isrc)
            isrc_results[isrc] = search_result
            if search_result["error"] is None:
                consecutive_errors = 0
            else:
                consecutive_errors += 1
                if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                    print(
                        f"Stopping after {MAX_CONSECUTIVE_ERRORS} "
                        "consecutive search errors."
                    )
                    stop_requested = True
                    break
        title_artist_search = skipped_search_result()
        if not stop_requested:
            title_artist_search = await search_youtube(title_artist_query)
            if title_artist_search["error"] is None:
                consecutive_errors = 0
            else:
                consecutive_errors += 1
                if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                    print(
                        f"Stopping after {MAX_CONSECUTIVE_ERRORS} "
                        "consecutive search errors."
                    )
                    stop_requested = True

        results[mbid] = {
            "mbid": mbid,
            "metadata_title": metadata.get("title"),
            "track_title": track.title,
            "isrc_searches": isrc_results,
            "title_artist_search": {
                "query": title_artist_query,
                **title_artist_search,
            },
        }
        tracks_processed += 1
        save_results(results_filename, metadata_filename, results)

    print(
        f"Saved YouTube search results for {tracks_processed} new tracks "
        f"to {results_filename}."
    )
    return True


if __name__ == "__main__":
    debug_youtube_search(batch_size=200)