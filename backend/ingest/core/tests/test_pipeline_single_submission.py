from django.test import SimpleTestCase
from ingest.core.pipeline import prepare_single_submission


class SingleSubmissionTests(SimpleTestCase):
    def setUp(self):
        self.track = {
            "title": "Track",
            "duration": 120.5,
            "numeric_features": [0.1, 0.5],
            "genre_dortmund": "rock",
            "genre_rosamerica": "roc",
            "moods_mirex": [0.1, 0.2, 0.0, 0.0, 0.0],
            "artist_pairs": [["b", "Second"], ["a", "First"]],
            "album_info": ["album", "Album", None],
        }

    def test_prepares_track_without_mutating_original(self):
        result = prepare_single_submission(self.track)
        self.assertIsNotNone(result)
        self.assertEqual(result["submissions"], 1)
        self.assertEqual(result["duration"], 120.5)
        self.assertEqual(result["numeric_features"], self.track["numeric_features"])
        self.assertEqual(result["artist_pairs"], [["a", "First"], ["b", "Second"]])
        self.assertEqual(result["album_info"], ["album", "Album", None])
        self.assertEqual(result["moods_mirex"], self.track["moods_mirex"])
        self.assertNotIn("submissions", self.track)
        self.assertEqual(self.track["artist_pairs"][0][0], "b")

    def test_missing_artist_is_dropped(self):
        self.track["artist_pairs"] = []
        self.assertIsNone(prepare_single_submission(self.track))

    def test_album_without_id_is_ignored(self):
        self.track["album_info"] = [None, "Album", "2000-01-01"]
        result = prepare_single_submission(self.track)
        self.assertIsNotNone(result)
        self.assertIsNone(result["album_info"])
