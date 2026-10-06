import os, requests, orjson, time
from random import random
from django.db.models import Q
from django.conf import settings
from datetime import datetime
from functools import reduce
from recommend_api.models import Track
from typing import Any

OUTBOUND_USER_AGENT = (
    f"{settings.APP_NAME}/{settings.APP_VERSION} ({settings.APP_AUTHOR_EMAIL})"
)
OUTPUT_FILENAME = os.path.join(
    settings.BASE_DIR, "ingest", "enrichments", "musicbrainz_track_metadata.json"
)
TEMP_FILENAME = os.path.join(
    settings.BASE_DIR, "ingest", "enrichments", "musicbrainz_track_metadata_temp.json"
)
MB_RECORDING_URL = "https://musicbrainz.org/ws/2/recording/"


def gather_musicbrainz_metadata(batch_size=10, override_file=False):
    """
    Builds a JSON file with metadata from MusicBrainz API for the Tracks with most submissions.
    The file is used as an index to check which Tracks were already processed in previous runs.
    Script will give up after encountering repeated errors.

    Args:
        batch_size: how many tracks to check
        override_file: If true, build the output file from scratch on every run
    """
    class Counters:
        # Count errors so we can abort after a certain number of them.
        errors: int = 0
        current_run_checked: int = 0
        all_runs_checked: int = 0
        current_run_isrcs: int = 0
        all_runs_isrcs: int = 0

    # Create the output file if it doesn't exist
    if not os.path.exists(OUTPUT_FILENAME) or override_file:
        print(f"{OUTPUT_FILENAME} not found, will create it from scratch.")
        try:
            with open(OUTPUT_FILENAME, "wb+") as f:
                output_json = {
                    "schema_version": 1,
                    "first_ran_at": datetime.now(),
                    "last_run_finished_at": None,
                    "tracks": {},
                }
                count = f.write(orjson.dumps(output_json))
                print(f"Created {OUTPUT_FILENAME} ({count} bytes).")

        except Exception as ex:
            os.remove(OUTPUT_FILENAME)
            print(f"Could not create file, aborting. Exception: {ex}")
            return

    # Load enrichment data from disk
    print("Loading enrichment data from disk.")
    try:
        with open(OUTPUT_FILENAME, "rb") as f:
            bytes = f.read()
            data: dict[str, Any] = orjson.loads(bytes)
    except Exception as ex:
        print(ex)
        return False

    # Tracks and ids for which enrichment was previously run
    json_tracks: dict[str, dict] = data.get("tracks", {})
    enriched_mbids: list = list(json_tracks.keys())
    Counters.all_runs_checked = len(enriched_mbids)
    Counters.all_runs_isrcs = reduce(
        lambda acc, curr: acc + 1 if len(curr.get("isrcs", [])) > 0 else acc, json_tracks.values(), 0
    )
    # Tracks to be enriched
    target_tracks = Track.objects.exclude(
        Q(musicbrainz_recordingid__in=enriched_mbids) |
        Q(isrc__len__gt=0)
    ).prefetch_related("artists").order_by("-submissions")[:batch_size]

    for track in target_tracks:
        artist = track.artists.first()
        print(f"Checking track: {track.title} by {artist.name if artist else "Unknown Artist"} ({track.musicbrainz_recordingid})")
        try:
            mbid = track.musicbrainz_recordingid
            response = requests.get(
                f"{MB_RECORDING_URL}{mbid}",
                params={"inc": "isrcs", "fmt": "json"},
                headers={"User-Agent": OUTBOUND_USER_AGENT},
                timeout=8,
            )
            response.raise_for_status()
        except requests.RequestException as ex:
            print(f"Could not fetch metadata for track {mbid}. Exception: {ex}")
            if Counters.errors > 5:
                break
            else:
                Counters.errors += 1
                continue

        # Add the retrieved metadata to current state
        try:
            meta = response.json()
        except requests.exceptions.JSONDecodeError as ex:
            print(f"Could not parse metadata for track {mbid}. Exception: {ex}")
            continue

        if not isinstance(meta, dict):
            print(f"API response for track {mbid} was not a dict. Got {type(meta)} with contents {meta}")
            continue

        json_tracks[mbid] = meta
        json_tracks[mbid]["checked_at"] = datetime.now()
        data["tracks"] = json_tracks
        enriched_mbids.append(mbid)
        Counters.current_run_checked += 1
        Counters.current_run_isrcs = Counters.current_run_isrcs + 1 if len(meta.get("isrcs", [])) > 0 else Counters.current_run_isrcs

        # Save data to a temp file. In case of errors we'll not lose all the data.
        try:
            with open(TEMP_FILENAME, "wb+") as f:
                f.write(orjson.dumps(data, option=orjson.OPT_INDENT_2))
        except Exception as ex:
            print(f"Could not write metadata to temp file for track {mbid}. Exception: {ex}")

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
        print(f"Could not write metadata to disk. Exception: {ex}")

    # Display stats before exiting
    print(f"The current run checked {Counters.current_run_checked} tracks, {Counters.current_run_isrcs} has ISRC codes.")
    print(f"Previous runs had checked {Counters.all_runs_checked} tracks, {Counters.all_runs_isrcs} had ISRC codes.")

    return True


def load_musicbrainz_metadata():
    if not os.path.exists(OUTPUT_FILENAME):
        print(f"{OUTPUT_FILENAME} not found, cannot continue.")
        return False

    with open(OUTPUT_FILENAME, "rb") as f:
        bytes = f.read()
        try:
            data: dict[str, Any] = orjson.loads(bytes)
        except orjson.JSONDecodeError as ex:
            print(f"Error parsing JSON, cannot continue. Exception {ex}")
            return False

        json_tracks: dict[str, dict] = data.get("tracks", {})
        enriched_mbids: list = list(json_tracks.keys())

        for mbid in enriched_mbids:
            track = Track.objects.filter(musicbrainz_recordingid=mbid).prefetch_related("artists").first()

            if track is None:
                print(f"Track with MBID: {mbid} not found in database")
                continue

            artist = track.artists.first()
            print(f"Updating track: {track.title} by {artist.name if artist else "Unknown Artist"} ({track.musicbrainz_recordingid})")

            raw_isrcs = json_tracks.get(mbid, {}).get("isrcs", [])
            json_isrcs = set(raw_isrcs) if isinstance(raw_isrcs, list) else set()
            track_isrcs = set(track.isrc)
            track.isrc = list(json_isrcs | track_isrcs)
            track.save(update_fields=["isrc"])

    return True


if __name__ == "__main__":
    gather_musicbrainz_metadata()
