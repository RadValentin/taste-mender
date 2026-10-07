import os, orjson, tempfile, requests
from django.test import TestCase
from unittest.mock import patch, MagicMock
from ingest.enrichments.musicbrainz_api_metadata import (
    gather_musicbrainz_metadata,
    load_musicbrainz_metadata,
    MB_RECORDING_URL,
    OUTBOUND_USER_AGENT,
)
from recommend_api.models import Track
from recommend_api.tests.factories import TrackFactory


class MusicbrainzAPIMetadataTests_Gather(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.output_filename = os.path.join(cls.temp_dir.name, "metadata.json")
        cls.temp_filename = os.path.join(cls.temp_dir.name, "metadata.tmp.json")
        cls.output_filename_patcher = patch(
            "ingest.enrichments.musicbrainz_api_metadata.OUTPUT_FILENAME",
            cls.output_filename,
        )
        cls.temp_filename_patcher = patch(
            "ingest.enrichments.musicbrainz_api_metadata.TEMP_FILENAME",
            cls.temp_filename,
        )
        cls.output_filename_patcher.start()
        cls.temp_filename_patcher.start()

        cls.sleep_patcher = patch("ingest.enrichments.musicbrainz_api_metadata.time.sleep",
                                  return_value=None)
        cls.sleep_patcher.start()

    def setUp(self) -> None:
        self.tracks: list[Track] = []
        for i in range(10):
            self.tracks.append(TrackFactory.create(title=f"Track {i}", submissions=10-i))

        self.patched_response = MagicMock()
        self.patched_response.raise_for_status.return_value = None
        self.patched_response.json.return_value = {}

        self.patched_requests = patch(
            "ingest.enrichments.musicbrainz_api_metadata.requests.get",
            return_value=self.patched_response,
        )
        self.mock_get = self.patched_requests.start()

    def test_creates_empty_json(self):
        Track.objects.all().delete()
        result = gather_musicbrainz_metadata()

        self.assertTrue(result)
        self.assertTrue(os.path.exists(self.output_filename))
        self.assertFalse(os.path.exists(self.temp_filename))

        with open(self.output_filename, "rb") as output_file:
            data = orjson.loads(output_file.read())

        self.assertEqual(data["schema_version"], 1)
        self.assertEqual(data["tracks"], {})
        self.assertIsNotNone(data["first_ran_at"])
        self.assertIsNone(data["last_run_finished_at"])

    def test_fetches_data_from_api(self):
        gather_musicbrainz_metadata()

        self.assertEqual(self.mock_get.call_count, len(self.tracks))
        for i in range(len(self.tracks)):
            self.mock_get.assert_any_call(
                f"{MB_RECORDING_URL}{self.tracks[i].musicbrainz_recordingid}",
                params={"inc": "isrcs", "fmt": "json"},
                headers={"User-Agent": OUTBOUND_USER_AGENT},
                timeout=8,
            )

    def test_stores_metadata_in_artifact(self):
        track = Track.objects.order_by("-submissions").first()
        assert track is not None
        mbid = track.musicbrainz_recordingid
        self.patched_response.json.return_value = {
            "id": "YT Video ID",
            "isrcs": ["A", "B", "C"],
            "title": "YT Video Title"
        }

        gather_musicbrainz_metadata(batch_size=1)

        with open(self.output_filename, "rb") as f:
            data = orjson.loads(f.read())

        self.assertEqual(data["tracks"][mbid]["id"], "YT Video ID")
        self.assertEqual(data["tracks"][mbid]["isrcs"], ["A", "B", "C"])
        self.assertEqual(data["tracks"][mbid]["title"], "YT Video Title")
        self.assertIn("checked_at", data["tracks"][mbid])
        self.assertIsNotNone(data["last_run_finished_at"])

    def test_limits_tracks_to_batch_size(self):
        gather_musicbrainz_metadata(batch_size=3)

        self.assertEqual(self.mock_get.call_count, 3)

    def test_skips_tracks_already_in_artifact(self):
        existing_mbid = self.tracks[0].musicbrainz_recordingid

        with open(self.output_filename, "wb") as f:
            f.write(orjson.dumps({
                "schema_version": 1,
                "first_ran_at": "2026-10-06T00:00:00",
                "last_run_finished_at": None,
                "tracks": {
                    existing_mbid: {
                        "id": existing_mbid,
                        "isrcs": [],
                        "checked_at": "2026-10-06T00:00:00",
                    }
                },
            }))

        gather_musicbrainz_metadata(batch_size=10)

        requested_urls = [
            call.args[0] for call in self.mock_get.call_args_list
        ]
        self.assertNotIn(
            f"{MB_RECORDING_URL}{existing_mbid}",
            requested_urls,
        )

    def test_skips_tracks_with_existing_isrcs(self):
        self.tracks[0].isrc = ["USABC1234567"]
        self.tracks[0].save(update_fields=["isrc"])

        gather_musicbrainz_metadata(batch_size=10)

        requested_urls = [
            call.args[0] for call in self.mock_get.call_args_list
        ]
        self.assertNotIn(
            f"{MB_RECORDING_URL}{self.tracks[0].musicbrainz_recordingid}",
            requested_urls,
        )

    def test_skips_http_failures(self):
        self.patched_response.raise_for_status.side_effect = requests.HTTPError(
            "MusicBrainz unavailable"
        )
        gather_musicbrainz_metadata(batch_size=1)

        with open(self.output_filename, "rb") as output_file:
            data = orjson.loads(output_file.read())
            self.assertEqual(data["tracks"], {})

    def test_skips_invalid_json_response(self):
        self.patched_response.json.side_effect = requests.exceptions.JSONDecodeError(
            "Invalid JSON", "", 0,
        )
        gather_musicbrainz_metadata(batch_size=1)

        with open(self.output_filename, "rb") as output_file:
            data = orjson.loads(output_file.read())
            self.assertEqual(data["tracks"], {})

    def test_skips_non_dict_response(self):
        self.patched_response.json.return_value = ["unexpected", "payload"]
        gather_musicbrainz_metadata(batch_size=1)

        with open(self.output_filename, "rb") as output_file:
            data = orjson.loads(output_file.read())
            self.assertEqual(data["tracks"], {})

    def tearDown(self) -> None:
        self.patched_requests.stop()
        TrackFactory.reset_sequence(0)
        if os.path.exists(self.output_filename):
            os.remove(self.output_filename)
        if os.path.exists(self.temp_filename):
            os.remove(self.temp_filename)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp_filename_patcher.stop()
        cls.output_filename_patcher.stop()
        cls.temp_dir.cleanup()
        cls.sleep_patcher.stop()


class MusicbrainzAPIMetadataTests_Load(TestCase):
    pass
