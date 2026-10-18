import os, logging, sys, django, time, orjson
from dotenv import dotenv_values
from django.conf import settings
from pathlib import Path

log = logging.getLogger(__name__)


if __name__ == "__main__":
    # If the script is called from CLI, run the Django setup
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    sys.path.append(BASE_DIR.as_posix())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "music_recommendation.settings")
    django.setup()
    # Set logger to output to console
    log.addHandler(logging.StreamHandler(sys.stdout))
    log.setLevel(logging.INFO)
else:
    BASE_DIR = settings.BASE_DIR

import ingest.core.track_processing_helpers as tph

# Ensure libarchive can be used. On Windows it requires a prebuilt DLL.
# Link: https://github.com/li-ruijie/libarchive
if os.name == "nt":
    os.environ["LIBARCHIVE"] = (Path(__file__).parent.resolve() / "libarchive-3.8.10.dll").as_posix()
import libarchive


def stream_track_json(path: str, mbid: str):
    mbid = mbid.lower()

    with libarchive.file_reader(path) as archive:
        for entry in archive:
            name: str = entry.pathname or ""
            if not (
                entry.isfile and name.endswith(".json") and mbid in name
            ):
                continue

            try:
                data = b"".join(entry.get_blocks())
            except Exception as e:
                log.warning("Failed reading %s: %s", name, e)
                continue

            yield name, data


def get_track_submissions(
    mbid: str, use_sample: bool = False, num_parts: int | None = None
):
    if not tph.is_mbid(mbid):
        log.error("The mbid param is not a valid UUID")
        return None

    config = dotenv_values(settings.BASE_DIR / ".env")

    # Different directories where AcousticBrainz data is stored
    if use_sample:
        # 100k records
        dataset_path = config.get("AB_SAMPLE_ROOT")
        if not dataset_path:
            raise ValueError(
                "Path to sample dataset is not defined in .env, please set a value for AB_SAMPLE_ROOT"
            )
    else:
        # 1M records
        dataset_path = config.get("AB_HIGHLEVEL_ROOT")
        if not dataset_path:
            raise ValueError(
                "Path to datasets is not defined in .env, please set a value for AB_HIGHLEVEL_ROOT"
            )

    archive_paths = [
        os.path.join(dataset_path, fname)
        for fname in os.listdir(dataset_path)
        if fname.lower().endswith(".tar.zst")
    ]

    if num_parts is not None:
        archive_paths = archive_paths[:num_parts]

    search_start = time.time()
    results = []
    for archive_path in archive_paths:
        log.info(f"Checking archive {archive_path}")
        check_start = time.time()
        for filename, raw_json in stream_track_json(archive_path, mbid):
            results.append(orjson.loads(raw_json))
        check_end = time.time()
        log.info(f"Finished check in {check_end - check_start:.2f}s")

    search_end = time.time()
    log.info(f"\nSearch took {search_end - search_start:.2f}s")

    return results


if __name__ == "__main__":
    enter_sandman_mbid = "62c2e20a-559e-422f-a44c-9afa7882f0c4"
    output = get_track_submissions(enter_sandman_mbid, use_sample=False, num_parts=None)

    # Stats for prediction values
    aggr_count = 0
    aggr_sum = 0
    naggr_count = 0
    naggr_sum = 0
    # Stats for prediction probabilities
    pred_count = 0
    pred_aggr_sum = 0
    pred_naggr_sum = 0
    if output is not None:
        for track in output:
            try:
                mood_aggressive = track.get("highlevel", {}).get("mood_aggressive", {})
                predictions = mood_aggressive.get("all", {})
                predictions_aggr = predictions.get("aggressive", None)
                predictions_naggr = predictions.get("not_aggressive", None)
                probability = mood_aggressive.get("probability", None)
                value = mood_aggressive.get("value", None)
                version = mood_aggressive.get("version", {})
                essentia_version = version.get("essentia", None)
                gaia_version = version.get("gaia", None)

                if predictions_aggr is not None and predictions_naggr is not None:
                    pred_aggr_sum += predictions_aggr
                    pred_naggr_sum += predictions_naggr
                    pred_count += 1

                if value is not None and probability is not None:
                    if value == "aggressive":
                        aggr_count += 1
                        aggr_sum += probability
                    if value == "not_aggressive":
                        naggr_count += 1
                        naggr_sum += probability

                print(f"{value} {probability:3f} {predictions} {essentia_version} {gaia_version}")
            except (KeyError, IndexError, TypeError, ValueError):
                log.exception("Missing data")

    print()
    print(f"# Averages across all predictions")
    print(f"Aggressive prediction average: {pred_aggr_sum / pred_count}.")
    print(f"Not aggressive prediction average: {pred_naggr_sum / pred_count}.")
    print()
    print(f"# Averages by prediction type")
    print(f"Aggressive vs not aggressive count: {aggr_count} / {naggr_count}")
    print(f"Average confidence for aggressive prediction: {aggr_sum / aggr_count}")
    print(f"Average confidence for non aggressive prediction: {naggr_sum / naggr_count}")
