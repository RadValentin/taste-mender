import requests
from datetime import timedelta
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.utils import timezone
from recommend_api.models import Track, Artist, TrackSource
from recommend_api.tests.factories import TrackFactory, ArtistFactory, TrackSourceFactory
from recommend_api.services.youtube_sources import (
    get_youtube_source,
    YOUTUBE_SEARCH_URL,
    YOUTUBE_VIDEOS_URL,
    SOURCE_LOOKUP_FAILURE_TTL,
)


class YoutubeSourcesTests(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mock_yt_api_key = "foo-bar-key"
        # YT API search response
        cls.search_response_json = {
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
        cls.list_response_json = {
            "items": [{
                "id": "vid6969",
                "snippet": {
                    "title": "List Track Title",
                    "channelTitle": "List Channel X",
                    "thumbnails": {"medium": {"url": "http://list-thumb"}},
                },
                "status": {
                    "embeddable": True
                }
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

        self.search_response = MagicMock()
        self.search_response.raise_for_status.return_value = None
        self.search_response.json.return_value = self.search_response_json

        self.list_response = MagicMock()
        self.list_response.raise_for_status.return_value = None
        self.list_response.json.return_value = self.list_response_json

        url_mapping = {
            YOUTUBE_SEARCH_URL: self.search_response,
            YOUTUBE_VIDEOS_URL: self.list_response
        }

        self.patched_requests = patch(
            "recommend_api.services.youtube_sources.requests.get",
            side_effect=lambda url, *args, **kwargs: url_mapping.get(url, MagicMock())
        )
        self.mock_get = self.patched_requests.start()

    # Source is present in DB cache and not stale
    def test_gets_source_from_cache(self):
        cached_source: TrackSource = TrackSourceFactory(track=self.track)
        result: TrackSource | None = get_youtube_source(self.track)

        self.assertIsNotNone(result)
        self.mock_get.assert_not_called()
        self.assertEqual(result, cached_source)

    def test_increments_count_for_cached_source(self):
        cached_source: TrackSource = TrackSourceFactory(track=self.track, source_request_count=6)
        result: TrackSource | None = get_youtube_source(self.track)
        cached_source.refresh_from_db()

        self.assertIsNotNone(result)
        self.mock_get.assert_not_called()
        self.assertEqual(result, cached_source)
        self.assertEqual(result.source_request_count, 7)

    # Source is present in DB cache but is stale
    def test_raises_for_missing_api_key_when_source_stale(self):
        TrackSourceFactory(
            track=self.track,
            source_id="cached-video",
            refreshed_at=timezone.now() - timedelta(days=31)
        )

        with patch("recommend_api.services.youtube_sources.YOUTUBE_SOURCE_CACHE_DAYS", 30):
            with patch(
                "recommend_api.services.youtube_sources.dotenv_values",
                return_value={"YOUTUBE_API_KEY": None},
            ):
                self.assertRaises(RuntimeError, get_youtube_source, self.track)

    def test_refreshes_stale_source(self):
        cached_source = TrackSourceFactory(
            track=self.track,
            source_id="cached-video",
            refreshed_at=timezone.now() - timedelta(days=31)
        )

        with patch("recommend_api.services.youtube_sources.YOUTUBE_SOURCE_CACHE_DAYS", 30):
            result = get_youtube_source(self.track)

        # Queries YouTube for the video's metadata
        self.assertIsNotNone(result)
        self.mock_get.assert_called_once()
        self.mock_get.assert_called_once_with(YOUTUBE_VIDEOS_URL, params={
            "part": "snippet,status,id",
            "id": cached_source.source_id,
            "key": self.mock_yt_api_key
        }, timeout=8)

        # Updates the cached video metadata
        old_refreshed_at = cached_source.refreshed_at
        cached_source.refresh_from_db()
        self.assertEqual(result.source_id, self.list_response_json["items"][0]["id"])
        self.assertEqual(cached_source.source_id, self.list_response_json["items"][0]["id"])
        self.assertNotEqual(cached_source.refreshed_at, old_refreshed_at)
        self.assertEqual(cached_source.source_request_count, 2)

    def test_returns_none_when_stale_source_verification_fails(self):
        cached_source = TrackSourceFactory(
            track=self.track,
            source_id="cached-video",
            refreshed_at=timezone.now() - timedelta(days=31),
        )
        self.mock_get.side_effect = requests.RequestException("YouTube unavailable")

        with patch("recommend_api.services.youtube_sources.YOUTUBE_SOURCE_CACHE_DAYS", 30):
            result = get_youtube_source(self.track)

        cached_source.refresh_from_db()
        self.assertIsNone(result)
        self.mock_get.assert_called_once_with(YOUTUBE_VIDEOS_URL, params={
            "part": "snippet,status,id",
            "id": cached_source.source_id,
            "key": self.mock_yt_api_key,
        }, timeout=8)
        self.assertEqual(cached_source.source_request_count, 2)

    def test_fallback_to_search_when_stale_source_not_on_yt(self):
        TrackSourceFactory(track=self.track, refreshed_at=timezone.now() - timedelta(days=31))

        with patch("recommend_api.services.youtube_sources.YOUTUBE_SOURCE_CACHE_DAYS", 30):
            self.list_response.json.return_value = {"items": []}
            result = get_youtube_source(self.track)

        urls = [call.args[0] for call in self.mock_get.call_args_list]
        self.assertEqual(self.mock_get.call_count, 2)
        self.assertIn(YOUTUBE_VIDEOS_URL, urls)
        self.assertIn(YOUTUBE_SEARCH_URL, urls)
        self.assertIsNotNone(result)
        self.assertEqual(result.source_id, self.search_response_json["items"][0]["id"]["videoId"])

    def test_clears_stale_source_when_fallback_search_fails(self):
        cached_source = TrackSourceFactory(
            track=self.track,
            source_id="cached-video",
            title="Cached title",
            channel="Cached channel",
            refreshed_at=timezone.now() - timedelta(days=31),
        )
        self.list_response.json.return_value = {"items": []}
        self.search_response.json.return_value = {"items": []}

        with patch("recommend_api.services.youtube_sources.YOUTUBE_SOURCE_CACHE_DAYS", 30):
            result = get_youtube_source(self.track)

        cached_source.refresh_from_db()
        self.assertIsNone(result)
        self.assertIsNotNone(cached_source.last_lookup_failed_at)
        self.assertIsNone(cached_source.source_id)
        self.assertIsNone(cached_source.title)
        self.assertIsNone(cached_source.channel)
        self.assertIsNone(cached_source.thumbnail)
        self.assertIsNone(cached_source.url)
        self.assertEqual(cached_source.source_request_count, 2)

    def test_fallback_to_search_when_stale_source_not_embeddable(self):
        TrackSourceFactory(track=self.track, refreshed_at=timezone.now() - timedelta(days=31))

        with patch("recommend_api.services.youtube_sources.YOUTUBE_SOURCE_CACHE_DAYS", 30):
            self.list_response.json.return_value = {
                "items": [{"id": "test", "status": {"embeddable": False}}]
            }
            result = get_youtube_source(self.track)

        urls = [call.args[0] for call in self.mock_get.call_args_list]
        self.assertEqual(self.mock_get.call_count, 2)
        self.assertIn(YOUTUBE_VIDEOS_URL, urls)
        self.assertIn(YOUTUBE_SEARCH_URL, urls)
        self.assertIsNotNone(result)
        self.assertEqual(result.source_id, self.search_response_json["items"][0]["id"]["videoId"])

    # Source is missing from DB cache
    def test_raises_for_missing_api_key_when_source_missing(self):
        with patch(
            "recommend_api.services.youtube_sources.dotenv_values",
            return_value={"YOUTUBE_API_KEY": None},
        ):
            self.assertRaises(RuntimeError, get_youtube_source, self.track)

    def test_makes_request_to_youtube_search(self):
        get_youtube_source(self.track)
        self.mock_get.assert_called_once()
        self.mock_get.assert_called_once_with(YOUTUBE_SEARCH_URL, params={
            "part": "snippet",
            "q": f"{self.track.title} {self.artist.name}".strip(),
            "videoEmbeddable": "true",
            "type": "video",
            "maxResults": 10,
            "key": self.mock_yt_api_key
        }, timeout=8)
        self.assertIsInstance(self.artist.name, str)

    def test_returns_no_items_for_empty_yt_response(self):
        self.search_response.json.return_value = {}
        self.assertIsNone(get_youtube_source(self.track))

    def test_records_search_request_failure(self):
        self.mock_get.side_effect = requests.RequestException("YouTube unavailable")

        result = get_youtube_source(self.track)
        cached_source = TrackSource.objects.get(track=self.track)

        self.assertIsNone(result)
        self.mock_get.assert_called_once()
        self.assertIsNotNone(cached_source.last_lookup_failed_at)
        self.assertIsNone(cached_source.source_id)
        self.assertIsNone(cached_source.url)
        self.assertEqual(cached_source.source_request_count, 1)

    def test_does_not_search_again_within_failure_ttl(self):
        self.search_response.json.return_value = {"items": []}

        self.assertIsNone(get_youtube_source(self.track))
        self.mock_get.assert_called()
        self.mock_get.reset_mock()

        result = get_youtube_source(self.track)
        cached_source = TrackSource.objects.get(track=self.track)

        self.assertIsNone(result)
        self.mock_get.assert_not_called()
        self.assertIsNotNone(cached_source.last_lookup_failed_at)
        self.assertEqual(cached_source.source_request_count, 2)

    def test_searches_again_after_failure_ttl(self):
        TrackSourceFactory(
            track=self.track,
            last_lookup_failed_at=(
                timezone.now() - SOURCE_LOOKUP_FAILURE_TTL - timedelta(seconds=1)
            ),
        )
        result = get_youtube_source(self.track)

        self.assertIsNotNone(result)
        self.mock_get.assert_called_once()
        self.mock_get.assert_called_once_with(YOUTUBE_SEARCH_URL, params={
            "part": "snippet",
            "q": f"{self.track.title} {self.artist.name}".strip(),
            "videoEmbeddable": "true",
            "type": "video",
            "maxResults": 10,
            "key": self.mock_yt_api_key
        }, timeout=8)
        cached_source = TrackSource.objects.get(track=self.track)
        self.assertIsNone(cached_source.last_lookup_failed_at)

    def test_returns_new_source_from_yt_search(self):
        result: TrackSource | None = get_youtube_source(self.track)
        json_source = self.search_response_json["items"][0]

        assert result is not None
        self.assertIsInstance(result, TrackSource)

        self.assertEqual(result.source_id, json_source["id"]["videoId"])
        self.assertEqual(result.title, json_source["snippet"]["title"])
        self.assertEqual(result.channel, json_source["snippet"]["channelTitle"])
        self.assertEqual(result.thumbnail, json_source["snippet"]["thumbnails"]["medium"]["url"])
        self.assertIn(json_source["id"]["videoId"], result.url)
        self.assertEqual(result.source_request_count, 1)

    def test_caches_source_from_yt_search(self):
        result: TrackSource | None = get_youtube_source(self.track)
        cached_source = TrackSource.objects.filter(track=self.track).first()

        self.assertIsNotNone(result)
        self.assertIsNotNone(cached_source)
        self.assertEqual(result, cached_source)

    def tearDown(self):
        TrackSource.objects.all().delete()
        self.patched_dotenv.stop()
        self.patched_requests.stop()
