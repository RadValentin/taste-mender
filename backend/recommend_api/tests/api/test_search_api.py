from django.urls import reverse
from rest_framework.test import APITestCase
from unittest.mock import patch
from recommend_api.models import Album, Artist, Track
from recommend_api.tests.factories import ArtistFactory, AlbumFactory, TrackFactory


ITEM_COUNT: int = 10
EVEN_ITEM_COUNT: int = ITEM_COUNT // 2

class SearchAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tracks: list[Track] = []
        cls.albums: list[Album] = []
        cls.artists: list[Artist] = []
        for i in range(ITEM_COUNT):
            new_album = AlbumFactory.create(
                name=f"Album {'odd' if i % 2 == 1 else 'even'} {i}"
            )
            cls.albums.append(new_album)
            cls.tracks.append(TrackFactory.create(
                title=f"Track {'odd' if i % 2 == 1 else 'even'} {i}",
                album=new_album,
                artists_text=f"mockart {i}",
                submissions=0
            ))
            cls.artists.append(ArtistFactory.create(
                name=f"Artist {'odd' if i % 2 == 1 else 'even'} {i}"
            ))

    def test_400_on_missing_query(self):
        url = reverse("api:search")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 400)

    def test_400_on_invalid_type(self):
        url = reverse("api:search")
        resp = self.client.get(url, {"q": "tes", "type": "badtype"})
        self.assertEqual(resp.status_code, 400)

    def test_response_format(self):
        url = reverse("api:search")
        resp = self.client.get(url, {"q": "eve"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["query"], "eve")
        self.assertEqual(resp.data["type"], "track")
        self.assertIn("response_time", resp.data)
        self.assertEqual(resp.data["count"], EVEN_ITEM_COUNT)
        self.assertEqual(len(resp.data["results"]), EVEN_ITEM_COUNT)
        self.assertFalse(resp.data["has_more"])

    def test_search_for_track_single_word(self):
        url = reverse("api:search")
        resp = self.client.get(url, {"q": "eve", "type": "track"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], EVEN_ITEM_COUNT)
        self.assertContains(resp, "Track even", EVEN_ITEM_COUNT)

    def test_search_for_track_multi_word(self):
        url = reverse("api:search")
        resp = self.client.get(url, {"q": "tra odd", "type": "track"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], EVEN_ITEM_COUNT)
        self.assertContains(resp, "Track odd", EVEN_ITEM_COUNT)

    def test_search_for_track_by_artists_text(self):
        url = reverse("api:search")
        resp = self.client.get(url, {"q": "mockart 1", "type": "track"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], 1)
        self.assertEqual(resp.data["results"][0]["title"], "Track odd 1")

    def test_search_defaults_to_tracks(self):
        url = reverse("api:search")
        resp = self.client.get(url, {"q": "eve"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], EVEN_ITEM_COUNT)
        self.assertContains(resp, "Track even", EVEN_ITEM_COUNT)

    def test_search_for_track_offset(self):
        url = reverse("api:search")
        resp = self.client.get(url, {"q": "eve", "limit": 2, "offset": 2})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], 2)
        self.assertEqual(len(resp.data["results"]), 2)
        self.assertNotIn("Track even 0", [result["title"] for result in resp.data["results"]])
        self.assertNotIn("Track even 2", [result["title"] for result in resp.data["results"]])

    def test_search_for_track_offset_upper_bound(self):
        url = reverse("api:search")

        with patch("recommend_api.api.search.MAX_SEARCH_RESULTS", 4):
            for offset in (4, 5):
                with self.subTest(offset=offset):
                    resp = self.client.get(url, {"q": "eve", "limit": 2, "offset": offset})
                    self.assertEqual(resp.status_code, 200)
                    self.assertEqual(resp.data["count"], 0)
                    self.assertEqual(resp.data["results"], [])

    def test_search_for_track_more_entries_found(self):
        url = reverse("api:search")
        resp = self.client.get(url, {"q": "eve", "limit": 2})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], 2)
        self.assertEqual(len(resp.data["results"]), 2)
        self.assertTrue(resp.data["has_more"])

    def test_search_for_track_no_more_entries_found(self):
        url = reverse("api:search")

        for offset in (4, 5):
            with self.subTest(offset=offset):
                resp = self.client.get(url, {"q": "eve", "limit": 2, "offset": offset})
                self.assertEqual(resp.status_code, 200)
                self.assertEqual(resp.data["count"], EVEN_ITEM_COUNT - offset)
                self.assertFalse(resp.data["has_more"])

    def test_search_for_artist_single_word(self):
        url = reverse("api:search")
        resp = self.client.get(url, {"q": "eve", "type": "artist"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], EVEN_ITEM_COUNT)
        self.assertContains(resp, "Artist even", EVEN_ITEM_COUNT)

    def test_search_for_artist_multi_word(self):
        url = reverse("api:search")
        resp = self.client.get(url, {"q": "art odd", "type": "artist"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], EVEN_ITEM_COUNT)
        self.assertContains(resp, "Artist odd", EVEN_ITEM_COUNT)

    def test_search_for_artist_offset(self):
        url = reverse("api:search")
        resp = self.client.get(url, {"q": "art eve", "type": "artist", "limit": 2, "offset": 2})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], 2)
        self.assertEqual(len(resp.data["results"]), 2)
        self.assertNotIn("Artist even 0", [result["name"] for result in resp.data["results"]])
        self.assertNotIn("Artist even 2", [result["name"] for result in resp.data["results"]])

    def test_search_for_album_single_word(self):
        url = reverse("api:search")
        resp = self.client.get(url, {"q": "eve", "type": "album"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], EVEN_ITEM_COUNT)
        self.assertContains(resp, "Album even", EVEN_ITEM_COUNT)

    def test_search_for_album_multi_word(self):
        url = reverse("api:search")
        resp = self.client.get(url, {"q": "alb odd", "type": "album"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], EVEN_ITEM_COUNT)
        self.assertContains(resp, "Album odd", EVEN_ITEM_COUNT)

    def test_search_for_album_offset(self):
        url = reverse("api:search")
        resp = self.client.get(url, {"q": "alb eve", "type": "album", "limit": 2, "offset": 2})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], 2)
        self.assertEqual(len(resp.data["results"]), 2)
        self.assertNotIn("Album even 0", [result["name"] for result in resp.data["results"]])
        self.assertNotIn("Album even 2", [result["name"] for result in resp.data["results"]])

    def test_limit(self):
        url = reverse("api:search")
        resp = self.client.get(url, {"q": "odd", "limit": 0})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], EVEN_ITEM_COUNT)
        self.assertContains(resp, "Album odd", EVEN_ITEM_COUNT)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        AlbumFactory.reset_sequence(0)
        ArtistFactory.reset_sequence(0)
        TrackFactory.reset_sequence(0)