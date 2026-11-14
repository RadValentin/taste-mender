from copy import deepcopy
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import SimpleTestCase
from joblib import Memory

from ingest.core.analysis_helpers import aggregate_stats


class AggregateStatsTests(SimpleTestCase):
    def setUp(self):
        self.mbid = "f367ad6e-efd5-4496-aba5-21a4edcd82c6"
        self.features = {
            "mood_happy": {"pos_pred_key": "happy", "neg_pred_key": "not_happy"},
        }
        submissions = {
            self.mbid: [{"highlevel": {
                "mood_happy": {"all": {"happy": 0.8, "not_happy": 0.2}},
                "mood_sad": {"all": {"sad": 0.3, "not_sad": 0.7}},
            }}],
        }
        loader = patch(
            "ingest.core.analysis_helpers.get_tracks_submissions",
            return_value=submissions,
        )
        self.load_submissions = loader.start()
        self.addCleanup(loader.stop)

    def test_explicit_features_override_defaults(self):
        with patch("ingest.core.analysis_helpers.TARGET_FEATURES", self.features):
            defaults = aggregate_stats([self.mbid])
            explicit = aggregate_stats([self.mbid], target_features={
                "mood_sad": {"pos_pred_key": "sad", "neg_pred_key": "not_sad"},
            })
            empty = aggregate_stats([self.mbid], target_features={})

        self.assertEqual(defaults[self.mbid]["mood_happy"]["predictions"], [(0.8, 0.2)])
        self.assertEqual(set(explicit[self.mbid]), {"mood_sad"})
        self.assertEqual(explicit[self.mbid]["mood_sad"]["predictions"], [(0.3, 0.7)])
        self.assertEqual(empty, {})

    def test_cache_recomputes_when_feature_configuration_changes(self):
        with TemporaryDirectory() as cache_dir:
            cached = Memory(cache_dir, verbose=0).cache(aggregate_stats)
            first = cached([self.mbid], target_features=self.features)
            self.assertEqual(
                cached([self.mbid], target_features=deepcopy(self.features)), first
            )
            self.assertEqual(self.load_submissions.call_count, 1)

            self.features["mood_sad"] = {
                "pos_pred_key": "sad", "neg_pred_key": "not_sad",
            }
            expanded = cached([self.mbid], target_features=self.features)
            self.assertEqual(
                expanded[self.mbid]["mood_sad"]["predictions"], [(0.3, 0.7)]
            )

            self.features["mood_happy"]["pos_pred_key"] = "not_happy"
            self.features["mood_happy"]["neg_pred_key"] = "happy"
            changed_keys = cached([self.mbid], target_features=self.features)
            self.assertEqual(
                changed_keys[self.mbid]["mood_happy"]["predictions"], [(0.2, 0.8)]
            )
            self.assertEqual(self.load_submissions.call_count, 3)

            del self.features["mood_sad"]
            reduced = cached([self.mbid], target_features=self.features)
            self.assertEqual(set(reduced[self.mbid]), {"mood_happy"})
            self.assertEqual(self.load_submissions.call_count, 4)
