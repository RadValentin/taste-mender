from datetime import timedelta
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.utils import timezone
from recommend_api.models import Track, Artist, TrackSource
from recommend_api.tests.factories import TrackFactory, ArtistFactory, TrackSourceFactory
from recommend_api.services.youtube_sources import get_youtube_source, YOUTUBE_SEARCH_URL


class YoutubeSourcesTests(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mock_yt_api_key = "foo-bar-key"
        # YT API search response
        cls.search_response = {
            "items": [{
                "id": {"videoId": "vid123"},
                "snippet": {
                    "title": "Track Title",
                    "channelTitle": "Channel X",
                    "thumbnails": {"medium": {"url": "http://thumb"}},
                },
            }]
        }
        # YT API videos list response
        cls.list_response = {
            "items": [{
                "id": "vid6969",
                "snippet": {
                    "title": "List Track Title",
                    "channelTitle": "List Channel X",
                    "thumbnails": {"medium": {"url": "http://list-thumb"}},
                },
            }]
        }

        return super().setUpClass()

    def setUp(self):
        # Test data
        self.artist: Artist = ArtistFactory()
        self.track: Track = TrackFactory()
        self.track.artists.add(self.artist)

        # Mocks
        self.patched_dotenv = patch("recommend_api.services.youtube_sources.dotenv_values",
                                 return_value={"YOUTUBE_API_KEY": self.mock_yt_api_key})
        self.mock_dotenv = self.patched_dotenv.start()

        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = self.search_response
        self.patched_requests = patch("recommend_api.services.youtube_sources.requests.get",
                                 return_value = response)
        self.mock_get = self.patched_requests.start()

    def test_raises_for_missing_api_key(self):
        self.mock_dotenv.return_value = {}
        self.assertRaises(RuntimeError, get_youtube_source, self.track)

    def test_makes_request_to_youtube_search(self):
        get_youtube_source(self.track)
        self.assertTrue(self.mock_get.called)
        self.mock_get.assert_called_once_with(YOUTUBE_SEARCH_URL, params={
            "part": "snippet",
            "q": f"{self.track.title} {self.artist.name}".strip(),
            "videoEmbeddable": "true",
            "type": "video",
            "maxResults": 10,
            "key": self.mock_yt_api_key
        }, timeout=8)
        self.assertIsInstance(self.artist.name, str)

    def test_returns_no_items_for_empty_response(self):
        empty_response = MagicMock()
        empty_response.json.return_value = {}
        self.mock_get.return_value = empty_response
        self.assertIsNone(get_youtube_source(self.track))

    def test_uses_configured_cache_duration(self):
        TrackSourceFactory(
            track=self.track,
            source_id="cached-video",
            refreshed_at=timezone.now() - timedelta(days=31)
        )

        with patch("recommend_api.services.youtube_sources.YOUTUBE_SOURCE_CACHE_DAYS", 60):
            result = get_youtube_source(self.track)

        self.assertIsNotNone(result)
        self.assertEqual(result.source_id, "cached-video")
        self.mock_get.assert_not_called()

    def test_returns_youtube_sources(self):
        result: TrackSource | None = get_youtube_source(self.track)
        json_source = self.search_response["items"][0]

        assert result is not None
        self.assertIsInstance(result, TrackSource)

        self.assertEqual(result.source_id, json_source["id"]["videoId"])
        self.assertEqual(result.title, json_source["snippet"]["title"])
        self.assertEqual(result.channel, json_source["snippet"]["channelTitle"])
        self.assertEqual(result.thumbnail, json_source["snippet"]["thumbnails"]["medium"]["url"])
        self.assertIn(json_source["id"]["videoId"], result.url)
        self.assertEqual(result.source_request_count, 1)

    def test_increments_request_count_for_cached_source(self):
        cached_source = TrackSourceFactory(track=self.track)
        self.assertEqual(cached_source.source_request_count, 1)

        result = get_youtube_source(self.track)
        cached_source.refresh_from_db()

        self.assertIsNotNone(result)
        self.assertEqual(cached_source.source_request_count, 2)
        self.mock_get.assert_not_called()

    def tearDown(self):
        TrackSource.objects.all().delete()
        self.patched_dotenv.stop()
        self.patched_requests.stop()
