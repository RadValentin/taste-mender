import os
import tempfile
from django.test import SimpleTestCase
from ingest.core.lmdb_index import LMDBTrackIndex
from ingest.core.pipeline import try_load_track_index


class PipelineCacheTests(SimpleTestCase):
    def test_empty_store_is_not_reused(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = os.path.join(temp_dir, "index")
            LMDBTrackIndex(path, map_size=20 * 1024**2).close()

            self.assertIsNone(try_load_track_index(path, map_size=20 * 1024**2))

    def test_readable_nonempty_store_is_reused(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = os.path.join(temp_dir, "index")
            store = LMDBTrackIndex(path, map_size=20 * 1024**2)
            track_id = "9a7f8913-7a6f-4708-9017-cf4d0c857756"
            store[track_id] = [{"value": "raw"}]
            store.mark_complete()
            store.close()

            cached_store = try_load_track_index(path, map_size=20 * 1024**2)
            if cached_store is None:
                self.fail("Expected the readable track index to be reused.")
            self.assertEqual(cached_store.get(track_id), [{"value": "raw"}])
            cached_store.close()
