import os, orjson, tempfile, requests
from asgiref.sync import sync_to_async
from datetime import datetime
from django.conf import settings
from django.test import SimpleTestCase, TestCase, TransactionTestCase
from django.utils import timezone
from py_yt.exceptions import PyYTSearchError
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch, AsyncMock, MagicMock
from ingest.enrichments.youtube_source_metadata import (
    MAX_CONSECUTIVE_ERRORS,
    SearchStatus,
    titles_are_for_same_track,
    normalize_text,
    search_youtube,
    gather_youtube_metadata,
    agather_youtube_metadata,
    load_youtube_metadata
)
from recommend_api.models import Track, Artist, TrackSource
from recommend_api.tests.factories import TrackFactory, ArtistFactory, TrackSourceFactory

class YouTubeSourceMetadataTests_Titles(SimpleTestCase):
    # Text normalization
    def test_normalizes_to_lower_case(self):
        self.assertEqual(normalize_text("MASTER of Puppets"), "master of puppets")

    def test_strips_annotations(self):
        text_tuples = [
            ("Jason Aldean - Don't You Wanna Stay (with Kelly Clarkson) (Lyric Video)", "jason aldean - don't you wanna stay (with kelly clarkson)"),
            ("Good Times Roll (2016 Remaster)", "good times roll"),
            ("Good Times Roll (Remaster 2019)", "good times roll"),
            ("Good Times Roll ( remaster )", "good times roll"),
            ("Good Times Roll [2019 Remaster]", "good times roll"),
            ("Good Times Roll [Remastered 2019]", "good times roll"),
            ("Brothers In Arms (Remastered 1996)", "brothers in arms"),
            ("Brothers In Arms (Official Music Video)", "brothers in arms"),
            ("We Can Work It Out (Official Music Video) [Remastered 2015]", "we can work it out")
        ]

        for raw_text, normalized_text in text_tuples:
            self.assertEqual(normalize_text(raw_text), normalized_text)

    # All searches
    def test_rejects_empty_titles(self):
        self.assertEqual(titles_are_for_same_track("Titanium", ""), (False, 0.0))
        self.assertEqual(titles_are_for_same_track("", "Titanium"), (False, 0.0))

    # ISRC searches
    def test_matches_identical_titles(self):
        is_match, _ = titles_are_for_same_track(
            "master of puppets", "master of puppets", is_isrc=True
        )
        self.assertTrue(is_match)

    def test_matches_different_capitalization(self):
        is_match, _ = titles_are_for_same_track(
            "Master Of Puppets", "master of puppets", is_isrc=True
        )
        self.assertTrue(is_match)

    def test_matches_titles_with_extra_terms(self):
        # contains tuples of (canonical title, search result title, a)
        title_tuples = [
            ("Titanium", "Titanium (feat. Sia)"),
            ("Titanium", "David Guetta - Titanium ft. Sia (Official Video)"),
            ("Don’t You Wanna Stay", "Don't You Wanna Stay (with Kelly Clarkson)"),
            ("Don’t You Wanna Stay", "Jason Aldean - Don't You Wanna Stay (with Kelly Clarkson) (Lyric Video)"),
            ("Ode To My Family", "The Cranberries - Ode To My Family (Official Music Video)"),
            ("Statesboro Blues", "The Allman Brothers Band - Statesboro Blues ( At Fillmore East, 1971 )"),
            ("(Sittin’ on) The Dock of the Bay", "[Sittin' On] the Dock of the Bay"),
            ("(Sittin’ on) The Dock of the Bay", "(Sittin' On) the Dock of the Bay [Mono]"),
            ("Sabbath Bloody Sabbath", 'BLACK SABBATH - "Sabbath Bloody Sabbath" (Official Video)'),
            ("Stars", "Simply Red - Stars (Official Video)"),
            ("Thorn in My Side", "Eurythmics, Annie Lennox, Dave Stewart - Thorn In My Side (Official Video)"),
            ("Blowin’ in the Wind", "Blowin' in the Wind (Album Version)"),
            ("Satisfaction", "(I Can't Get No) Satisfaction (Official Lyric Video)"),
            ("D’yer Mak’er", "Led Zeppelin - D'yer Mak'er (Official Audio)"),
            ("Do You Remember Rock ’n’ Roll Radio?", "Ramones - Do You Remember Rock and Roll Radio?"),
        ]

        for original_title, comparison_title in title_tuples:
            is_match, _ = titles_are_for_same_track(original_title, comparison_title, is_isrc=True)
            self.assertTrue(is_match)

    def test_does_not_match_distinct_titles(self):
        title_tuples = [
            ("Ramble On", "Moby Dick (Intro / Outro Rough Mix)")
        ]

        for original_title, comparison_title in title_tuples:
            is_match, _ = titles_are_for_same_track(original_title, comparison_title, is_isrc=True)
            self.assertFalse(is_match)

    # Title + Artist searches
    def test_rejects_wrong_artist_when_artist_is_known(self):
        is_match, _ = titles_are_for_same_track(
            "Fast Car",
            "Jonas Blue - Fast Car ft. Dakota",
            artists=["Tracy Chapman"],
        )
        self.assertFalse(is_match)

    def test_accepts_artist(self):
        title_tuples = [
            (
                "Don’t You Wanna Stay",
                "Jason Aldean - Don't You Wanna Stay (with Kelly Clarkson) (Lyric Video)",
                ["Kelly Clarkson"],
            ), (
                "Ode to My Family",
                "The Cranberries - Ode To My Family (Official Music Video)",
                ["The Cranberries"]
            )
        ]

        for original_title, comparison_title, artists in title_tuples:
            is_match, _ = titles_are_for_same_track(
                original_title,
                comparison_title,
                artists=artists,
            )
            self.assertTrue(is_match)


class YouTubeSourceMetadataTests_Search(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.mock_response = {
            "result": [{
                "foo": "bar",
                "motto": "yolo"
            }]
        }
        self.patched_search_next = patch(
            "ingest.enrichments.youtube_source_metadata.VideosSearch.next",
            new=AsyncMock(return_value=self.mock_response)
        )
        self.mock_next = self.patched_search_next.start()

        return await super().asyncSetUp()

    async def test_returns_found_item(self):
        result = await search_youtube("foo-query", is_isrc=True)

        self.mock_next.assert_awaited_once()
        self.assertEqual(result["query"], "foo-query")
        self.assertEqual(result["search_type"], "isrc")
        self.assertEqual(result["search_status"], SearchStatus.FOUND)
        self.assertEqual(result["meta"], self.mock_response["result"][0])
        self.assertIsNotNone(result["checked_at"])
        self.assertIsNone(result["error"])

    async def test_returns_found_item_title_artist_query(self):
        result = await search_youtube("foo-query")

        self.mock_next.assert_awaited_once()
        self.assertEqual(result["query"], "foo-query")
        self.assertEqual(result["search_type"], "title_artist")
        self.assertEqual(result["search_status"], SearchStatus.FOUND)
        self.assertEqual(result["meta"], self.mock_response["result"][0])
        self.assertIsNotNone(result["checked_at"])
        self.assertIsNone(result["error"])

    async def test_returns_empty(self):
        self.mock_next.return_value = {"result": []}
        result = await search_youtube("foo-query", is_isrc=True)

        self.mock_next.assert_awaited_once()
        self.assertEqual(result["query"], "foo-query")
        self.assertEqual(result["search_type"], "isrc")
        self.assertEqual(result["search_status"], SearchStatus.EMPTY)
        self.assertIsNone(result["meta"])
        self.assertIsNotNone(result["checked_at"])
        self.assertIsNone(result["error"])

    async def test_returns_error(self):
        self.mock_next.side_effect = PyYTSearchError("YouTube unavailable")
        result = await search_youtube("foo-query")

        self.mock_next.assert_awaited_once()
        self.assertEqual(result["query"], "foo-query")
        self.assertEqual(result["search_type"], "title_artist")
        self.assertEqual(result["search_status"], SearchStatus.ERROR)
        self.assertIsNone(result["meta"])
        self.assertIsNotNone(result["checked_at"])
        self.assertIsNotNone(result["error"])

    async def asyncTearDown(self) -> None:
        return await super().asyncTearDown()


class YouTubeSourceMetadataTests_Gather(TransactionTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.output_filename = os.path.join(cls.temp_dir.name, "yt-metadata.json")
        cls.temp_filename = os.path.join(cls.temp_dir.name, "yt-metadata.tmp.json")
        cls.output_filename_patcher = patch(
            "ingest.enrichments.youtube_source_metadata.OUTPUT_FILENAME",
            cls.output_filename,
        )
        cls.temp_filename_patcher = patch(
            "ingest.enrichments.youtube_source_metadata.TEMP_FILENAME",
            cls.temp_filename,
        )
        cls.output_filename_patcher.start()
        cls.temp_filename_patcher.start()

        cls.sleep_patcher = patch("ingest.enrichments.youtube_source_metadata.time.sleep",
                                  return_value=None)
        cls.sleep_patcher.start()

    def setUp(self) -> None:
        super().setUp()
        self.artists: list[Artist] = []
        self.tracks: list[Track] = []
        for i in range(10):
            new_artist = ArtistFactory()
            self.artists.append(new_artist)

            new_track: Track = TrackFactory.create(title=f"Track {i}", submissions=10-i)
            new_track.artists.add(new_artist)
            self.tracks.append(new_track)

        self.patched_yt_search = patch(
            "ingest.enrichments.youtube_source_metadata.search_youtube",
            new=AsyncMock(return_value={}),
        )
        self.mock_yt_search = self.patched_yt_search.start()

    def test_creates_empty_json(self):
        Track.objects.all().delete()
        result = gather_youtube_metadata(batch_size=1)

        self.assertTrue(result)
        self.assertTrue(os.path.exists(self.output_filename))
        self.assertFalse(os.path.exists(self.temp_filename))

        with open(self.output_filename, "rb") as output_file:
            data = orjson.loads(output_file.read())

        self.assertEqual(data["schema_version"], 1)
        self.assertEqual(data["sources"], {})
        self.assertEqual(data["isrcs"], {})
        self.assertIsNotNone(data["first_ran_at"])
        self.assertIsNone(data["last_run_finished_at"])

    async def test_fetches_data_from_yt(self):
        await agather_youtube_metadata(data={}, target_tracks=self.tracks)

        self.assertEqual(self.mock_yt_search.call_count, len(self.tracks))
        for i in range(len(self.tracks)):
            track = self.tracks[i]
            artists = await sync_to_async(
               lambda: [normalize_text(artist.name) for artist in track.artists.all()]
            )()
            all_artists_str = " ".join(artists)
            query = f"{track.title} {all_artists_str}".strip()
            self.mock_yt_search.assert_any_call(query, is_isrc=False)

    async def test_stores_titlartist_search_metadata_in_artifact(self):
        track: Track | None = await sync_to_async(Track.objects.order_by("-submissions").first)()
        assert track is not None
        mbid = track.musicbrainz_recordingid
        self.mock_yt_search.return_value = {
            "query": "YOLO",
            "search_type": "title_artist",
            "search_status": SearchStatus.FOUND,
            "meta": {"foo": "bar"},
            "checked_at": datetime.now(),
            "error": None
        }

        await agather_youtube_metadata(data={}, target_tracks=[self.tracks[0]])

        with open(self.output_filename, "rb") as f:
            data = orjson.loads(f.read())

        self.assertEqual(data["sources"][mbid]["query"], "YOLO")
        self.assertEqual(data["sources"][mbid]["search_type"], "title_artist")
        self.assertEqual(data["sources"][mbid]["search_status"], SearchStatus.FOUND)
        self.assertEqual(data["sources"][mbid]["meta"], {"foo": "bar"})
        self.assertIn("checked_at", data["sources"][mbid])
        self.assertIsNotNone(data["last_run_finished_at"])
        self.assertEqual(data["isrcs"], {})

    async def test_stores_isrc_search_metadata_in_artifact(self):
        track = self.tracks[0]
        track.isrc = ["USRC17607839"]
        await sync_to_async(track.save)()

        result = {
            "query": "USRC17607839",
            "search_type": "isrc",
            "search_status": SearchStatus.FOUND,
            "meta": {"title": track.title},
            "checked_at": datetime.now(),
            "error": None,
        }

        self.mock_yt_search.return_value = result
        data = {"sources": {}, "isrcs": {}}
        await agather_youtube_metadata(data=data, target_tracks=[track])

        self.assertEqual(data["sources"][track.musicbrainz_recordingid], result)
        self.assertEqual(data["isrcs"]["USRC17607839"], result)
        self.mock_yt_search.assert_awaited_once_with(query="USRC17607839", is_isrc=True)

    def test_limits_tracks_to_batch_size(self):
        gather_youtube_metadata(batch_size=3)

        self.assertEqual(self.mock_yt_search.call_count, 3)

    def test_gives_up_after_repeated_errors(self):
        self.mock_yt_search.return_value = {"search_status": SearchStatus.ERROR}
        result = gather_youtube_metadata(batch_size=10)

        self.assertEqual(self.mock_yt_search.call_count, MAX_CONSECUTIVE_ERRORS)
        self.assertFalse(result)

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


class YouTubeSourceMetadataTests_Load(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.output_filename = os.path.join(cls.temp_dir.name, "yt-metadata.json")
        cls.output_filename_patcher = patch(
            "ingest.enrichments.youtube_source_metadata.OUTPUT_FILENAME",
            cls.output_filename,
        )
        cls.output_filename_patcher.start()

    def setUp(self) -> None:
        self.source = {
            "query": "Track 0 Artist 0",
            "search_type": "title_artist",
            "search_status": SearchStatus.FOUND.value,
            "meta": {
                "type": "video",
                "id": "video-123",
                "title": "Track 0",
                "channel": {"name": "Artist 0"},
                "thumbnails": [{"url": "https://img.youtube.com/video-123.jpg"}],
                "link": "https://www.youtube.com/watch?v=video-123",
            },
            "checked_at": timezone.now(),
            "error": None,
        }
        self.tracks: list[Track] = []
        for i in range(10):
            self.tracks.append(TrackFactory.create(title=f"Track {i}", submissions=10-i))

    def test_should_exit_when_artifact_not_found(self):
        result = load_youtube_metadata()

        self.assertFalse(result)
        self.assertEqual(TrackSource.objects.count(), 0)

    def test_should_exit_when_artifact_has_malformed_json(self):
        with open(self.output_filename, "wt") as f:
            f.write("poo poo")

        result = load_youtube_metadata()

        self.assertFalse(result)
        self.assertEqual(TrackSource.objects.count(), 0)

    def test_should_skip_invalid_sources(self):
        mbid = self.tracks[0].musicbrainz_recordingid
        with open(self.output_filename, "wb") as f:
            f.write(orjson.dumps({
                "sources": {mbid: "poo-poo"}
            }))

        result = load_youtube_metadata()
        self.assertTrue(result)
        self.assertEqual(TrackSource.objects.count(), 0)

    def test_should_skip_invalid_mbids(self):
        mbid = "yolo-bro"
        with open(self.output_filename, "wb") as f:
            f.write(orjson.dumps({
                "sources": {mbid: self.source}
            }))

        result = load_youtube_metadata()
        self.assertTrue(result)
        self.assertEqual(TrackSource.objects.count(), 0)

    def test_loads_found_source(self):
        track = self.tracks[0]
        mbid = track.musicbrainz_recordingid
        with open(self.output_filename, "wb") as f:
            f.write(orjson.dumps({
                "sources": {mbid: self.source}
            }))

        result = load_youtube_metadata()

        self.assertTrue(result)
        source = TrackSource.objects.get(track=track)
        self.assertEqual(source.provider, TrackSource.Provider.YOUTUBE)
        self.assertEqual(source.source_id, "video-123")
        self.assertEqual(source.title, "Track 0")
        self.assertEqual(source.channel, "Artist 0")
        self.assertEqual(source.thumbnail, "https://img.youtube.com/video-123.jpg")
        self.assertEqual(source.url, "https://www.youtube.com/watch?v=video-123")
        self.assertIsNone(source.last_lookup_failed_at)

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