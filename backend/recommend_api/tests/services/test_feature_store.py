import uuid
import numpy as np
import numpy.typing as npt
from django.test import SimpleTestCase
import recommend_api.services.recommender as rec


class FeatureStoreTests(SimpleTestCase):
    RAW_FEATURE_SCALE = 3.0

    def setUp(self):
        # Bypass singleton loading and build a minimal in-memory store for method tests.
        self.store = object.__new__(rec.FeatureStore)

        self.store.feature_matrix = np.array(
            [
                [1.0, 0.0, 0.0],  # A
                [0.9, 0.1, 0.0],  # B
                [0.2, 1.0, 0.0],  # C
                [0.1, 0.0, 1.0],  # D
            ],
            dtype=np.float32,
        )
        self.store.feature_matrix_raw = self.store.feature_matrix * self.RAW_FEATURE_SCALE

        self.uuids = {
            "A": str(uuid.uuid4()),
            "B": str(uuid.uuid4()),
            "C": str(uuid.uuid4()),
            "D": str(uuid.uuid4()),
        }
        self.store.mbid_to_idx = np.array(
            [
                uuid.UUID(self.uuids["A"]).bytes,
                uuid.UUID(self.uuids["B"]).bytes,
                uuid.UUID(self.uuids["C"]).bytes,
                uuid.UUID(self.uuids["D"]).bytes,
            ],
            dtype="V16",
        )


    def test_get_track_features(self):
        features = self.store.get_track_features(self.uuids["B"])
        np.testing.assert_allclose(features, self.store.feature_matrix[1])

    def test_get_track_features_raw(self):
        features_raw = self.store.get_track_features_raw(self.uuids["C"])
        if features_raw is None:
            self.fail("Expected raw feature vector")
        np.testing.assert_allclose(features_raw, self.store.feature_matrix_raw[2])

    def test_get_track_features_raw_returns_none_when_raw_missing(self):
        self.store.feature_matrix_raw = None
        self.assertIsNone(self.store.get_track_features_raw(self.uuids["A"]))
