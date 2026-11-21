import os,  logging, sys, django, orjson
import zstandard as zstd
from dotenv import dotenv_values
from django.conf import settings
from pathlib import Path
from typing import Any
from itertools import islice

log = logging.getLogger("ingest")


if __name__ == "__main__":
    # If the script is called from CLI, run the Django setup
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    sys.path.append(BASE_DIR.as_posix())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "music_recommendation.settings")
    django.setup()
else:
    BASE_DIR = settings.BASE_DIR

from ingest.analysis.analysis_cache_build import stream_tracks_json


def read_samples(archive: str, limit: int) -> list[bytes]:
    return [
        orjson.dumps([{"highlevel": orjson.loads(raw).get("highlevel", {})}])
        for _, _, raw in islice(stream_tracks_json(archive), limit)
    ]


def train_dictionary(samples: list[bytes]) -> zstd.ZstdCompressionDict:
    if len(samples) < 8_000:
        raise ValueError("The training archive needs at least 8,000 submissions")
    return zstd.train_dictionary(64 * 1024, samples[:8_000])


def main():
    config: dict[str, Any] = dotenv_values(settings.BASE_DIR / ".env")
    dataset_path = config.get("AB_HIGHLEVEL_ROOT")
    if not dataset_path:
        raise ValueError("Path to datasets is not defined in .env, please set AB_HIGHLEVEL_ROOT")

    archive_names = os.listdir(dataset_path)
    archive_paths = []
    for part in range(4):
        matches = [
            os.path.join(dataset_path, fname)
            for fname in archive_names
            if fname.lower().endswith(f"-{part}.tar.zst")
        ]
        if len(matches) != 1:
            raise ValueError(f"Expected one archive for part {part} in {dataset_path}; found {len(matches)}")
        archive_paths.append(matches[0])

    samples = read_samples(archive_paths[0], 10_000)
    dictionary = train_dictionary(samples)
    test = samples[8_000:]
    if not test:
        raise ValueError("The training archive needs more than 8,000 submissions for the benchmark")

    dictionary_path = Path(__file__).resolve().parent / "analysis-zstd.dict"
    dictionary_path.write_bytes(dictionary.as_bytes())

    plain = zstd.ZstdCompressor(level=1)
    with_dict = zstd.ZstdCompressor(level=1, dict_data=dictionary)
    for index, archive in enumerate(archive_paths[:4]):
        test_samples = test if index == 0 else read_samples(archive, 2_000)
        if not test_samples:
            raise ValueError(f"No submissions found in {archive}")
        without_dict = sum(len(plain.compress(s)) for s in test_samples)
        with_dictionary = sum(len(with_dict.compress(s)) for s in test_samples)
        savings = (1 - with_dictionary / without_dict) * 100
        print(f"Part {index}: {archive} ({len(test_samples)} submissions)")
        print(f"Without dictionary: {without_dict}")
        print(f"With dictionary:    {with_dictionary} ({savings:.1f}% smaller)")


if __name__ == "__main__":
    main()
