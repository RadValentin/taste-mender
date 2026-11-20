import os, shutil,  logging, sys, django, time, orjson
from dotenv import dotenv_values
from django.conf import settings
from pathlib import Path, PurePosixPath
from typing import Any, Iterator

log = logging.getLogger("ingest")


if __name__ == "__main__":
    # If the script is called from CLI, run the Django setup
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    sys.path.append(BASE_DIR.as_posix())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "music_recommendation.settings")
    django.setup()
else:
    BASE_DIR = settings.BASE_DIR

from ingest.core.cli_helpers import spinner
from ingest.core.lmdb_index import LMDBTrackIndex, validate_compression_dictionary

# Ensure libarchive can be used. On Windows it requires a prebuilt DLL.
# Link: https://github.com/li-ruijie/libarchive
if os.name == "nt":
    os.environ["LIBARCHIVE"] = (
        Path(__file__).resolve().parents[1] / "core" / "libarchive-3.8.10.dll"
    ).as_posix()
import libarchive


def stream_tracks_json(path: str) -> Iterator[tuple[str, bytes]]:
    with libarchive.file_reader(path) as archive:
        for entry in archive:
            name: str = entry.pathname or ""
            if not (entry.isfile and name.endswith(".json")):
                continue

            try:
                data = b"".join(entry.get_blocks())
            except Exception as e:
                log.warning("Failed reading %s: %s", name, e)
                continue

            mbid = PurePosixPath(name).stem.rsplit("-", 1)[0]
            yield mbid, data


def build_cache_for_analysis(
    use_sample: bool = False, num_parts: int | None = None, override: bool = False
):
    """
    Goes over the AcousticBrainz dataset archives, extracts submission data and builds an
    LMDB index keyed by MBID. Useful for inspecting the raw high-level features in the dataset.
    """

    lmdb_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lmdb_data_analysis")
    os.makedirs(lmdb_root, exist_ok=True)

    if (use_sample):
        log.info("Will build cache for sample dataset.")
        lmdb_dir = os.path.join(lmdb_root, "sample")
    elif num_parts:
        log.info(f"Will build cache for {num_parts} parts of the dataset.")
        lmdb_dir = os.path.join(lmdb_root, f"parts-{num_parts}")
    else:
        log.info("Will build cache for the full dataset.")
        lmdb_dir = os.path.join(lmdb_root, "full")

    if os.path.exists(lmdb_dir) and not override:
        log.warning(f"Cache already present at {lmdb_dir}, giving up.")
        return

    config: dict[str, Any] = dotenv_values(settings.BASE_DIR / ".env")

    # Different directories where AcousticBrainz data is stored
    if use_sample:
        # 100k records
        dataset_path = config.get("AB_SAMPLE_ROOT")
        if not dataset_path:
            raise ValueError(
                "Path to sample dataset is not defined in .env, please set a value for AB_SAMPLE_ROOT"
            )
    else:
        # 1M+ records
        dataset_path = config.get("AB_HIGHLEVEL_ROOT")
        if not dataset_path:
            raise ValueError(
                "Path to datasets is not defined in .env, please set a value for AB_HIGHLEVEL_ROOT"
            )

    archive_paths: list[str] = [
        os.path.join(dataset_path, fname)
        for fname in os.listdir(dataset_path)
        if fname.lower().endswith(".tar.zst")
    ]

    if num_parts is not None:
        archive_paths = archive_paths[:num_parts]

    if not archive_paths:
        raise ValueError(f"No dataset archives found in {dataset_path}")

    dictionary_path = Path(__file__).resolve().parent / "analysis-zstd.dict"
    try:
        dictionary = dictionary_path.read_bytes()
    except FileNotFoundError:
        from ingest.analysis.analysis_train_zstd_dict import read_samples, train_dictionary

        log.info("Dictionary not found; training from %s.", archive_paths[0])
        samples = read_samples(archive_paths[0], 8_000)
        dictionary = train_dictionary(samples).as_bytes()
        validate_compression_dictionary(dictionary)
        dictionary_path.write_bytes(dictionary)
        log.info("Saved dictionary to %s.", dictionary_path)
    else:
        validate_compression_dictionary(dictionary)

    if os.path.exists(lmdb_dir):
        shutil.rmtree(lmdb_dir)

    os.makedirs(lmdb_dir, exist_ok=True)

    # Adjust map size to 1.5GB per 1M files
    MAP_SIZE = len(archive_paths) * 3 * 1024**3 // 2
    track_index: LMDBTrackIndex = LMDBTrackIndex(
        lmdb_dir, map_size=MAP_SIZE, compression_dictionary=dictionary,
    )

    build_start = time.time()
    for archive_path in archive_paths:
        with spinner(f"Loading archive {archive_path}"):
            for mbid, raw_json in stream_tracks_json(archive_path):
                try:
                    data = orjson.loads(raw_json)
                    track_index.append(mbid, {"highlevel": data.get("highlevel", {})})
                except orjson.JSONDecodeError:
                    log.exception("Bad JSON string")

    track_index.mark_complete()
    log.info("Live index pages: %.2f GiB", track_index.size_pages() / 1024**3)
    log.info("LMDB map size: %.2f GiB", track_index.map_size() / 1024**3)
    track_index.close()
    log.info("Finished building cache.")
    log.info(f"Build took took {time.time() - build_start:.2f}s")


if __name__ == "__main__":
    build_cache_for_analysis(use_sample=True, override=True)
