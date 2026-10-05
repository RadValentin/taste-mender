# url: https://musicbrainz.org/ws/2/recording/00000baf-9215-483a-8900-93756eaf1cfc?inc=isrcs&fmt=json
# response:
# {
#     "isrcs": [
#         "DEG189810182"
#     ],
#     "video": false,
#     "first-release-date": "1998-05-01",
#     "title": "Como Poden",
#     "length": 201853,
#     "id": "00000baf-9215-483a-8900-93756eaf1cfc",
#     "disambiguation": ""
# }


# NOTE: since I'm getting data from MusicBrainz anyway, why not get the most out of it.
# Let's enhance Track with as much metadata as possible.
import os, requests, orjson
from django.conf import settings
from datetime import datetime
from recommend_api.models import Track
from typing import Any

OUTBOUND_USER_AGENT = f"{settings.APP_NAME}/{settings.APP_VERSION} ({settings.APP_AUTHOR_EMAIL})"
OUTPUT_FILENAME =  os.path.join(settings.BASE_DIR, "ingest", "enrichments", "musicbrainz_track_metadata.json")
MB_RECORDING_URL = "https://musicbrainz.org/ws/2/recording/"

def gather_musicbrainz_metadata(override_file=False):
    # Create the output file if it doesn't exist
    if not os.path.exists(OUTPUT_FILENAME) or override_file:
        print(f"{OUTPUT_FILENAME} not found, will create it from scratch.")
        try:
            with open(OUTPUT_FILENAME, "wb+") as f:
                output_json = {
                    "schema_version": 1,
                    "run_started_at": datetime.now(),
                    "run_finished_at": None,
                    "tracks": {}
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
    json_tracks: dict[str, dict]  = data.get("tracks", {})
    enriched_mbids: list = list(json_tracks.keys())
    # Tracks to be enriched
    target_tracks = Track.objects.exclude(
        musicbrainz_recordingid__in=enriched_mbids
    ).order_by("-submissions")[:1]

    for track in target_tracks:
        try:
            mbid = track.musicbrainz_recordingid
            response = requests.get(f"{MB_RECORDING_URL}{mbid}", params={
                "inc": "isrcs",
                "fmt": "json"
            }, headers={"User-Agent": OUTBOUND_USER_AGENT}, timeout=8)
            response.raise_for_status()
        except requests.RequestException as ex:
            print(f"Could not fetch metadata for track {mbid}. Exception: {ex}")
            return False

        # Add the retrieved metadata to current state
        meta = response.json()
        json_tracks[mbid] = meta
        data["tracks"] = json_tracks
        enriched_mbids.append(mbid)

        # Update the enrichment file
        try:
            with open(OUTPUT_FILENAME, "wb") as f:
                f.write(orjson.dumps(data, option=orjson.OPT_INDENT_2))
        except:
            print(f"Could not write metadata fro track {mbid} to disk. Exception: {ex}")

    return True

if __name__ == "__main__":
    gather_musicbrainz_metadata()
