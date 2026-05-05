import numpy as np
import uuid
from django.test import SimpleTestCase
from unittest.mock import patch
import recommend_api.services.recommender as rec

class RecommenderTests(SimpleTestCase):
    responseKeys = [
        'target_year', 'target_genre_dortmund', 'target_genre_rosamerica', 'top_tracks', 'stats'
    ]

    def setUp(self):
        # Override the local variables of the module, removes the need to load feature matrix
        # and metadata from disk
        self.patched_store = patch("recommend_api.services.recommender.STORE")
        self.mock_store = self.patched_store.start()

        # 4 tracks, 3-dim features
        self.mock_store.feature_matrix = np.array([
            [1.0, 0.0, 0.0],  # A
            [0.9, 0.1, 0.0],  # B  (most similar to A)
            [0.2, 1.0, 0.0],  # C
            [0.1, 0.0, 1.0],  # D
        ], dtype=float)

        self.uuids = {
            'A': str(uuid.uuid4()),
            'B': str(uuid.uuid4()),
            'C': str(uuid.uuid4()),
            'D': str(uuid.uuid4()),
        }
        self.mock_store.mbid_to_idx = np.array(
            [
                uuid.UUID(self.uuids["A"]).bytes,
                uuid.UUID(self.uuids["B"]).bytes,
                uuid.UUID(self.uuids["C"]).bytes,
                uuid.UUID(self.uuids["D"]).bytes,
            ],
            dtype="V16",
        )
        # A,B,C in 1990s decade; D in 1980s
        self.mock_store.years = np.array([1991, 1992, 1994, 1983])
        # Put A,B,C in same Rosamerica genre (code=1), D different (code=2)
        self.mock_store.genre_rosamerica = np.array([1, 1, 1, 2], dtype=np.uint16)
        # A,C,D in same Dortmund genre (code=10), B different (code=11)
        self.mock_store.genre_dortmund = np.array([10, 11, 10, 10], dtype=np.uint16)
        self.mock_store.feature_names = np.array(['danceability', 'aggressiveness', 'brightness'])

    def test_recommend_rosamerica(self):
        out = rec.recommend(self.uuids['A'], options={"k":2, "use_ros":True})

        self.assertListEqual(list(out.keys()), self.responseKeys)
        # Candidates are B,C (same decade + same ros genre)
        self.assertEqual(out['stats']['candidate_count'], 2)
        self.assertEqual(out['top_tracks'][0]['mbid'], self.uuids['B'])
        self.assertEqual(out['top_tracks'][1]['mbid'], self.uuids['C'])
        self.assertEqual(len(out['top_tracks']), 2)

    def test_exclude(self):
        out = rec.recommend(self.uuids['A'], options={"k":2, "use_ros":True, "exclude_mbids":[self.uuids['B']]})

        self.assertListEqual(list(out.keys()), self.responseKeys)
        # Only C is candidate, B was excluded
        self.assertEqual(out['stats']['candidate_count'], 1)
        self.assertEqual(out['top_tracks'][0]['mbid'], self.uuids['C'])
        self.assertEqual(len(out['top_tracks']), 1)

    def test_recommend_dortmund(self):
        out = rec.recommend(self.uuids['A'], options={"k":2, "use_ros": False})

        self.assertListEqual(list(out.keys()), self.responseKeys)
        self.assertEqual(out['stats']['candidate_count'], 1)
        self.assertEqual(out['top_tracks'][0]['mbid'], self.uuids['C'])
        self.assertEqual(len(out['top_tracks']), 1)

    def test_genre_guardrails_off(self):
        out = rec.recommend(self.uuids['A'], options={"k":2, "use_ros": False, "match_genre": False})

        self.assertListEqual(list(out.keys()), self.responseKeys)
        self.assertEqual(out['stats']['candidate_count'], 2)
        self.assertEqual(out['top_tracks'][0]['mbid'], self.uuids['B'])
        self.assertEqual(out['top_tracks'][1]['mbid'], self.uuids['C'])
        self.assertEqual(len(out['top_tracks']), 2)

    def test_decade_guardrails_off(self):
        out = rec.recommend(self.uuids['A'], options={"k":2, "use_ros": False, "match_decade": False})

        self.assertListEqual(list(out.keys()), self.responseKeys)
        self.assertEqual(out['stats']['candidate_count'], 2)
        self.assertEqual(out['top_tracks'][0]['mbid'], self.uuids['C'])
        self.assertEqual(out['top_tracks'][1]['mbid'], self.uuids['D'])
        self.assertEqual(len(out['top_tracks']), 2)

    def test_feature_stats(self):
        # Make one column near-constant to trigger near_zero_col_count
        fm = self.mock_store.feature_matrix.copy()
        fm[:, 2] = 0.000001
        self.mock_store.feature_matrix = fm

        stats = rec.get_feature_stats()
        assert stats['unique_track_count'] == 4
        assert stats['total_col_count'] == 3
        assert stats['near_zero_col_count'] >= 1

    def tearDown(self):
        self.patched_store.stop()
