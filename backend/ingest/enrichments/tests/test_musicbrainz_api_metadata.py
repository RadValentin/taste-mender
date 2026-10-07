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
        super().setUpClass()
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
        super().setUp()
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
        super().tearDown()
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
        super().tearDownClass()


class MusicbrainzAPIMetadataTests_Load(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.output_filename = os.path.join(cls.temp_dir.name, "metadata.json")
        cls.output_filename_patcher = patch(
            "ingest.enrichments.musicbrainz_api_metadata.OUTPUT_FILENAME",
            cls.output_filename,
        )
        cls.output_filename_patcher.start()

    def setUp(self) -> None:
        self.tracks: list[Track] = []
        for i in range(10):
            self.tracks.append(TrackFactory.create(title=f"Track {i}", submissions=10-i))

    def test_should_exit_when_artifact_not_found(self):
        result = load_musicbrainz_metadata()

        self.assertFalse(result)
        self.assertEqual(Track.objects.filter(isrc__len__gt=0).count(), 0)

    def test_should_exit_when_artifact_has_malformed_json(self):
        with open(self.output_filename, "wt") as f:
            f.write("poo poo")

        result = load_musicbrainz_metadata()
        self.assertFalse(result)

    def test_should_update_isrcs_from_artifact(self):
        first_mbid = self.tracks[0].musicbrainz_recordingid
        second_mbid = self.tracks[1].musicbrainz_recordingid

        with open(self.output_filename, "wb") as f:
            f.write(orjson.dumps({
                "schema_version": 1,
                "first_ran_at": "2026-10-06T00:00:00",
                "last_run_finished_at": None,
                "tracks": {
                    first_mbid : { "isrcs": ["USABC1234567"] },
                    second_mbid: { "isrcs": ["VALIX6666666"] }
                },
            }))

        result = load_musicbrainz_metadata()
        self.tracks[0].refresh_from_db()
        self.tracks[1].refresh_from_db()

        self.assertTrue(result)
        self.assertEqual(self.tracks[0].isrc, ["USABC1234567"])
        self.assertEqual(self.tracks[1].isrc, ["VALIX6666666"])
        for i in range(2, 10):
            self.tracks[i].refresh_from_db()
            self.assertEqual(len(self.tracks[i].isrc), 0)

    def test_should_preserve_existing_isrcs(self):
        track = self.tracks[0]
        track.isrc = ["USOLD1234567"]
        track.save(update_fields=["isrc"])

        with open(self.output_filename, "wb") as f:
            f.write(orjson.dumps({
                "schema_version": 1,
                "tracks": {
                    track.musicbrainz_recordingid: { "isrcs": ["USNEW1234567"] }
                }
            }))

        result = load_musicbrainz_metadata()
        track.refresh_from_db()

        self.assertTrue(result)
        self.assertCountEqual(track.isrc, ["USOLD1234567", "USNEW1234567"])

    def test_should_deduplicate_isrcs(self):
        track = self.tracks[0]

        with open(self.output_filename, "wb") as f:
            f.write(orjson.dumps({
                "tracks": {
                    track.musicbrainz_recordingid: { "isrcs": ["USABC1234567", "USABC1234567"] }
                }
            }))

        load_musicbrainz_metadata()
        track.refresh_from_db()

        self.assertEqual(track.isrc, ["USABC1234567"])

    def test_should_skip_unknown_mbid(self):
        with open(self.output_filename, "wb") as f:
            f.write(orjson.dumps({
                "tracks": {
                    "unknown-mbid": { "isrcs": ["USABC1234567"] }
                }
            }))

        self.assertTrue(load_musicbrainz_metadata())
        self.assertEqual(Track.objects.filter(isrc__len__gt=0).count(), 0)

    def test_should_ignore_invalid_isrc_payload(self):
        track = self.tracks[0]

        with open(self.output_filename, "wb") as f:
            f.write(orjson.dumps({
                "tracks": {
                    track.musicbrainz_recordingid: { "isrcs": "not-a-list" }
                }
            }))

        track.refresh_from_db()

        self.assertTrue(load_musicbrainz_metadata())
        self.assertEqual(track.isrc, [])

    def tearDown(self) -> None:
        super().tearDown()
        TrackFactory.reset_sequence(0)
        if os.path.exists(self.output_filename):
            os.remove(self.output_filename)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.output_filename_patcher.stop()
        cls.temp_dir.cleanup()
        super().tearDownClass()
