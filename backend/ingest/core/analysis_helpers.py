import os, logging, sys, django, time, orjson
from collections import defaultdict
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
from ingest.core.cli_helpers import style, fg, bg
from recommend_api.models import Track, Artist

# Ensure libarchive can be used. On Windows it requires a prebuilt DLL.
# Link: https://github.com/li-ruijie/libarchive
if os.name == "nt":
    os.environ["LIBARCHIVE"] = (Path(__file__).parent.resolve() / "libarchive-3.8.10.dll").as_posix()
import libarchive


def stream_tracks_json(path: str, mbids: list[str]):
    with libarchive.file_reader(path) as archive:
        for entry in archive:
            name: str = entry.pathname or ""
            if not (entry.isfile and name.endswith(".json")):
                continue

            matched_mbids = list(filter(lambda mbid: mbid in name, mbids))
            if len(matched_mbids) < 1:
                continue
            found_mbid = matched_mbids[0]

            try:
                data = b"".join(entry.get_blocks())
            except Exception as e:
                log.warning("Failed reading %s: %s", name, e)
                continue

            yield name, found_mbid, data


def get_tracks_submissions(
    mbids: list[str], use_sample: bool = False, num_parts: int | None = None
):
    mbids = list(map(lambda mbid: mbid.lower(), mbids))
    if not all(map(tph.is_mbid, mbids)):
        log.error("One or all of the mbids param is not a valid UUID")
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
    results = defaultdict(list)
    for archive_path in archive_paths:
        log.info(f"Checking archive {archive_path}")
        check_start = time.time()
        for _, mbid, raw_json in stream_tracks_json(archive_path, mbids):
            results[mbid].append(orjson.loads(raw_json))

        check_end = time.time()
        log.info(f"Finished check in {check_end - check_start:.2f}s")

    search_end = time.time()
    log.info(f"\nSearch took {search_end - search_start:.2f}s")

    return results

def main():
    target_mbids = ["62c2e20a-559e-422f-a44c-9afa7882f0c4"]
    target_features = {
        "danceability": {
            "pos_pred_key": "danceable",
            "neg_pred_key": "not_danceable"
        },
        "mood_aggressive": {
            "pos_pred_key": "aggressive",
            "neg_pred_key": "not_aggressive"
        }
    }
    submissions_by_mbid = get_tracks_submissions(target_mbids, use_sample=False, num_parts=1)

    if submissions_by_mbid is None:
        return False

    # Get relevant feature data from JSON dict
    output: dict[str, dict] = defaultdict(dict)
    for mbid in target_mbids:
        for feature_name, feature_keys in target_features.items():
            stats = {
                # Stats for prediction values
                "pos_count": 0,
                "pos_sum": 0,
                "neg_count": 0,
                "neg_sum": 0,
                # Stats for prediction probabilities
                "pred_count": 0,
                "pred_pos_sum": 0,
                "pred_neg_sum": 0,
                "essentia_version": defaultdict(int),
                "gaia_version": defaultdict(int)
            }

            for submission in submissions_by_mbid[mbid]:
                try:
                    feature = submission.get("highlevel", {}).get(feature_name, {})
                    predictions = feature.get("all", {})
                    predictions_pos = predictions.get(feature_keys["pos_pred_key"], None)
                    predictions_neg = predictions.get(feature_keys["neg_pred_key"], None)
                    probability = feature.get("probability", None)
                    value = feature.get("value", None)
                    version = feature.get("version", {})
                    essentia_version = version.get("essentia", None)
                    gaia_version = version.get("gaia", None)

                    if predictions_pos is not None and predictions_neg is not None:
                        stats["pred_pos_sum"] += predictions_pos
                        stats["pred_neg_sum"] += predictions_neg
                        stats["pred_count"] += 1

                    if value is not None and probability is not None:
                        if value == feature_keys["pos_pred_key"]:
                            stats["pos_count"] += 1
                            stats["pos_sum"] += probability
                        if value == feature_keys["neg_pred_key"]:
                            stats["neg_count"] += 1
                            stats["neg_sum"] += probability

                    if essentia_version is not None:
                        stats["essentia_version"][essentia_version] += 1
                    if gaia_version is not None:
                        stats["gaia_version"][gaia_version] += 1

                except (KeyError, IndexError, TypeError, ValueError):
                    log.exception("Missing data")

            output[mbid][feature_name] = stats

    # Print data
    for mbid in target_mbids:
        track = Track.objects.filter(musicbrainz_recordingid=mbid).prefetch_related("artists").first()
        if not track:
            continue
        artists = ", ".join(artist.name for artist in track.artists.all())

        print(f"{style.BRIGHT}{fg.GREEN}Stats for: {track.title} by {artists} ({mbid})", style.RESET_ALL)
        for feature_name, feature_keys in target_features.items():
            data = output[mbid][feature_name]
            pos_name = feature_keys["pos_pred_key"]
            neg_name = feature_keys["neg_pred_key"]

            print(f"{style.BRIGHT}{fg.MAGENTA}{feature_name}", style.RESET_ALL)
            if data["pred_count"] > 0:
                print(f"{style.BRIGHT}Averages across all predictions", style.RESET_ALL)
                print(f"{pos_name} prediction average: {data["pred_pos_sum"] / data["pred_count"]}.")
                print(f"{neg_name} prediction average: {data["pred_neg_sum"] / data["pred_count"]}.")

            print()
            print(f"{style.BRIGHT}Averages by prediction type", style.RESET_ALL)
            print(f"{pos_name} vs {neg_name} count: {data["pos_count"]} / {data["neg_count"]}")
            if data["pos_count"] > 0:
                print(f"Average confidence for {pos_name} prediction: {data["pos_sum"] / data["pos_count"]}")
            if data["neg_count"] > 0:
                print(f"Average confidence for non {neg_name} prediction: {data["neg_sum"] / data["neg_count"]}")
            print()
            print(f"{style.BRIGHT}Tool versions", style.RESET_ALL)
            print([f"{k}: {v}" for k, v in data["essentia_version"].items()])
            print([f"{k}: {v}" for k, v in data["gaia_version"].items()])


if __name__ == "__main__":
    main()
