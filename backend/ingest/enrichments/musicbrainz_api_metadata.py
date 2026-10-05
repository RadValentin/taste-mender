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

OUTPUT_FILENAME =  os.path.join(settings.BASE_DIR, "ingest", "enrichments", "musicbrainz_track_metadata.json")
print(OUTPUT_FILENAME)
MB_RECORDING_URL = "https://musicbrainz.org/ws/2/recording/00000baf-9215-483a-8900-93756eaf1cfc?inc=isrcs&fmt=json"

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
                    "tracks": {
                        "foo": {
                            "bar": "baz"
                        }
                    }
                }
                count = f.write(orjson.dumps(output_json))
                print(f"Created {OUTPUT_FILENAME} ({count} bytes).")

        except Exception as ex:
            os.remove(OUTPUT_FILENAME)
            print(f"Could not create file, aborting. Exception: {ex}")
            return

    # Load enrichment data from disk
    print("Load enrichment data from disk")
    try:
        with open(OUTPUT_FILENAME, "rb") as f:
            bytes = f.read()
            data = orjson.loads(bytes)
            tracks: dict[str, dict] = data.get("tracks")


            print(tracks.keys())

    except Exception as ex:
        print(ex)
    return True

if __name__ == "__main__":
    gather_musicbrainz_metadata(override_file=True)

