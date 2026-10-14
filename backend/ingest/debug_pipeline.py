# mprof run python ingest/debug_pipeline.py --sample
# mprof plot --flame
import os, json, orjson, uuid, shutil
import sys
import django
import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "music_recommendation.settings")
django.setup()

from ingest.core.pipeline import build_database
from ingest.core.lmdb_index import LMDBTrackIndex
import ingest.core.track_processing_helpers as tph

build_database(use_sample=True)
