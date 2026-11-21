import os, logging, sys, django
import pandas as pd
from collections import defaultdict
from django.conf import settings
from pathlib import Path
from statistics import mean, median, stdev
from typing import Any

log = logging.getLogger("ingest")


if __name__ == "__main__":
    # If the script is called from CLI, run the Django setup
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    sys.path.append(BASE_DIR.as_posix())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "music_recommendation.settings")
    django.setup()
else:
    BASE_DIR = settings.BASE_DIR

import ingest.core.track_processing_helpers as tph
from ingest.core.cli_helpers import style, fg
from ingest.core.pipeline import try_load_track_index
from recommend_api.models import Track

# Size of on-disk track index, set an arbitrary default 2GB
MAP_SIZE = 1024 * 1024 * 1024 * 2


def get_tracks_submissions(
    mbids: list[str], use_sample: bool = False, num_parts: int | None = None
):
    mbids = list(map(lambda mbid: mbid.strip().lower(), mbids))
    if not all(map(tph.is_mbid, mbids)):
        log.error("One or all of the mbids param is not a valid UUID")
        return None

    lmdb_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lmdb_data_analysis")
    os.makedirs(lmdb_root, exist_ok=True)

    if (use_sample):
        lmdb_dir = os.path.join(lmdb_root, "sample")
    elif num_parts:
        lmdb_dir = os.path.join(lmdb_root, f"parts-{num_parts}")
    else:
        lmdb_dir = os.path.join(lmdb_root, "full")

    track_index = try_load_track_index(lmdb_dir, MAP_SIZE) if os.path.exists(lmdb_dir) else None

    if track_index is not None:
        log.info("Trying to get submissions from cache.")
        results = defaultdict(list)

        for mbid in mbids:
            submissions = []
            for _, values in track_index.iter_prefix(mbid):
                submissions.extend(values)
            results[mbid] = submissions
        return results

    else:
        log.info("Could not get submissions from cache, please rebuild cache.")
        return None


TARGET_FEATURES = {
    "danceability": {
        "pos_pred_key": "danceable",
        "neg_pred_key": "not_danceable"
    },
    "mood_aggressive": {
        "pos_pred_key": "aggressive",
        "neg_pred_key": "not_aggressive"
    },
    "mood_happy": {
        "pos_pred_key": "happy",
        "neg_pred_key": "not_happy"
    },
    "mood_sad": {
        "pos_pred_key": "sad",
        "neg_pred_key": "not_sad"
    }
}


def aggregate_stats(
    target_mbids: list[str] | None = None,
    use_sample=False,
    num_parts=None,
    *,
    target_features: dict[str, dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Aggregate predictions; make sure to pass `target_features` explicitly when caching."""
    if target_mbids is None or len(target_mbids) < 1:
        return {}

    features = TARGET_FEATURES if target_features is None else target_features
    submissions_by_mbid = get_tracks_submissions(target_mbids, use_sample, num_parts)
    if submissions_by_mbid is None:
        return {}

    # Get relevant feature data from JSON dict
    output: dict[str, dict] = defaultdict(dict)
    for mbid in target_mbids:
        for feature_name, feature_keys in features.items():
            stats = {
                # Stats for prediction probabilities
                "predictions": [],
                "pred_count": 0,
                "essentia_version": defaultdict(int),
                "gaia_version": defaultdict(int)
            }

            for submission in submissions_by_mbid[mbid]:
                try:
                    feature = submission.get("highlevel", {}).get(feature_name, {})
                    predictions = feature.get("all", {})
                    predictions_pos = predictions.get(feature_keys["pos_pred_key"], None)
                    predictions_neg = predictions.get(feature_keys["neg_pred_key"], None)
                    version = feature.get("version", {})
                    essentia_version = version.get("essentia", None)
                    gaia_version = version.get("gaia", None)

                    if predictions_pos is not None and predictions_neg is not None:
                        pos = float(predictions_pos)
                        neg = float(predictions_neg)

                        if not (0 <= pos <= 1 and 0 <= neg <= 1):
                            raise ValueError("Prediction probabilities must be between 0 and 1")

                        stats["predictions"].append((pos, neg))
                        stats["pred_count"] += 1

                    if essentia_version is not None:
                        stats["essentia_version"][essentia_version] += 1
                    if gaia_version is not None:
                        stats["gaia_version"][gaia_version] += 1

                except (KeyError, IndexError, TypeError, ValueError, AttributeError):
                    log.exception("Missing data")

            if stats["pred_count"] != 0:
                output[mbid][feature_name] = stats

    return dict(output)


def print_stats(stats: dict[str, Any]):
    target_mbids = stats.keys()

    # Print data
    for mbid in target_mbids:
        track = Track.objects.filter(musicbrainz_recordingid=mbid).prefetch_related("artists").first()
        if not track:
            print(f"{style.BRIGHT}{fg.GREEN}Stats for: Unknown track ({mbid})", style.RESET_ALL)
        else:
            artists = ", ".join(artist.name for artist in track.artists.all())
            print(f"{style.BRIGHT}{fg.GREEN}Stats for: {track.title} by {artists} ({mbid})", style.RESET_ALL)

        for feature_name, feature_keys in TARGET_FEATURES.items():
            data = stats[mbid][feature_name]
            pos_name = feature_keys["pos_pred_key"]
            neg_name = feature_keys["neg_pred_key"]
            pos_won_predictions = [pos for pos, neg in data["predictions"] if pos > neg]
            neg_won_predictions = [neg for pos, neg in data["predictions"] if neg > pos]
            all_pos_predictions = [pos for pos, _ in data["predictions"]]
            all_neg_predictions = [neg for _, neg in data["predictions"]]

            if data["pred_count"] < 1:
                continue

            print(f"{style.BRIGHT}{fg.MAGENTA}{feature_name}", style.RESET_ALL)
            print(f"Total submissions: {style.BRIGHT}{data["pred_count"]}", style.RESET_ALL)
            print(f"Predicted {pos_name} / {neg_name}: {len(pos_won_predictions)} / {len(neg_won_predictions)}")
            print()

            if len(pos_won_predictions) > 1:
                print(f"{style.BRIGHT}Stats for submissions tagged {pos_name}", style.RESET_ALL)
                print(f" Mean {mean(pos_won_predictions)}")
                print(f" Median {median(pos_won_predictions)}")
                print(f" Standard deviation {stdev(pos_won_predictions)}")
                print()

            if len(neg_won_predictions) > 1:
                print(f"{style.BRIGHT}Stats for submissions tagged {neg_name}", style.RESET_ALL)
                print(f" Mean {mean(neg_won_predictions)}")
                print(f" Median {median(neg_won_predictions)}")
                print(f" Standard deviation {stdev(neg_won_predictions)}")
                print()

            if len(all_pos_predictions) > 1:
                print(f"{style.BRIGHT}Stats for all submissions regardless of class", style.RESET_ALL)
                print(f" {pos_name} Mean {mean(all_pos_predictions)}")
                print(f" {pos_name} Median {median(all_pos_predictions)}")
                print(f" {pos_name} Standard deviation {stdev(all_pos_predictions)}")
                print()

            if len(all_neg_predictions) > 1:
                print(f" {neg_name} Mean {mean(all_neg_predictions)}")
                print(f" {neg_name} Median {median(all_neg_predictions)}")
                print(f" {neg_name} Standard deviation {stdev(all_neg_predictions)}")
                print()

            print(f"{style.BRIGHT}Tool versions", style.RESET_ALL)
            print("essentia: ", [f"{k}: {v}" for k, v in data["essentia_version"].items()])
            print("gaia: ", [f"{k}: {v}" for k, v in data["gaia_version"].items()])
            print()


def export_stats(
    stats: dict[str, Any],
    feature: str | None = None,
    target_mbids: list[str] | None = None,
) -> pd.DataFrame:
    """Flatten already aggregated stats into one row per MBID.

    Feature-prefixed columns contain counts, tagged/all prediction summaries,
    and version-count dictionaries. As in print_stats, summary statistics are
    omitted (NaN) for groups with fewer than two predictions. Ties count toward
    all-prediction summaries but neither tagged group.

    By default all MBIDs and features are included. target_mbids filters rows in
    their original stats order; an empty list selects none, and MBIDs absent from
    stats are ignored. feature filters the exported feature columns.
    """
    features = {
        name: keys for name, keys in TARGET_FEATURES.items()
        if feature is None or name == feature
    }
    columns = ["title", "artists"]
    for name, keys in features.items():
        labels = (keys["pos_pred_key"], keys["neg_pred_key"])
        columns.extend([f"total_pred", *(f"{label}_count" for label in labels)])
        columns.extend(
            f"{group}_{label}_{metric}"
            for group in ("tagged", "all")
            for label in labels
            for metric in ("mean", "median", "std")
        )
        columns.extend([f"essentia_ver", f"gaia_ver"])
    columns.append("mbid")

    if target_mbids is not None:
        selected_mbids = set(target_mbids)
        stats = {mbid: data for mbid, data in stats.items() if mbid in selected_mbids}

    if not stats:
        return pd.DataFrame(columns=columns)

    tracks = {
        track.musicbrainz_recordingid: track
        for track in Track.objects.filter(
            musicbrainz_recordingid__in=list(stats)
        ).prefetch_related("artists")
    }
    rows = []
    for mbid, track_stats in stats.items():
        track = tracks.get(mbid)
        row: dict[str, Any] = {
            "mbid": mbid,
            "title": track.title if track else "Unknown track",
            "artists": ", ".join(artist.name for artist in track.artists.all()) if track else "",
        }
        for name, keys in features.items():
            data = track_stats.get(name, {})
            predictions = data.get("predictions", [])
            pos_name, neg_name = keys["pos_pred_key"], keys["neg_pred_key"]
            tagged_pos = [pos for pos, neg in predictions if pos > neg]
            tagged_neg = [neg for pos, neg in predictions if neg > pos]
            row[f"total_pred"] = data.get("pred_count", 0)
            row[f"{pos_name}_count"] = len(tagged_pos)
            row[f"{neg_name}_count"] = len(tagged_neg)

            groups = (
                ("tagged", pos_name, tagged_pos),
                ("tagged", neg_name, tagged_neg),
                ("all", pos_name, [pos for pos, _ in predictions]),
                ("all", neg_name, [neg for _, neg in predictions]),
            )
            for group, label, values in groups:
                for metric, calculate in (("mean", mean), ("median", median), ("std", stdev)):
                    row[f"{group}_{label}_{metric}"] = (
                        calculate(values) if len(values) > 1 else float("nan")
                    )
            for tool in ("essentia", "gaia"):
                row[f"{tool}_ver"] = dict(data.get(f"{tool}_version", {}))
        rows.append(row)

    return pd.DataFrame(rows, columns=columns)


def main():
    target_mbids = [
        "62c2e20a-559e-422f-a44c-9afa7882f0c4", "acc8f927-65e9-4662-8665-8127efe76e6a"
    ]
    print_stats(aggregate_stats(target_mbids, use_sample=True))


if __name__ == "__main__":
    main()
