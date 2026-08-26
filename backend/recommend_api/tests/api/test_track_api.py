import numpy as np
import uuid
from datetime import date, datetime, timedelta
from unittest.mock import patch
from django.urls import reverse
from rest_framework.test import APITestCase
from recommend_api.services.youtube_sources import YTSource
from recommend_api.models import Album, Track
from recommend_api.tests.factories import (
    TrackFactory,
    AlbumFactory,
    ArtistFactory,
    GenreDortmundFactory,
    GenreRosamericaFactory,
)


class TrackAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.albums = {
            "album_today": AlbumFactory.create(date=datetime.today()),
            "album_feb29": AlbumFactory.create(date=datetime.fromisoformat('2024-02-29')),
            "album_yesterday": AlbumFactory.create(date=datetime.today() - timedelta(days=1)),
        }
        cls.track_tuples = [
            (str(uuid.uuid4()), "Song A", cls.albums["album_today"]),
            (str(uuid.uuid4()), "Song B", cls.albums["album_feb29"]),
            (str(uuid.uuid4()), "Song C", cls.albums["album_today"]),
            (str(uuid.uuid4()), "Song D", cls.albums["album_yesterday"]),
        ]
        cls.tracks: list[Track] = []
        for mbid, title, album in cls.track_tuples:
            cls.tracks.append(
                TrackFactory.create(
                    musicbrainz_recordingid=mbid,
                    title=title,
                    album=album,
                )
            )

    def test_get_list(self):
        url = reverse("api:track-list")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], len(self.tracks))
        self.assertEqual(len(resp.data["results"]), len(self.tracks))
        self.assertCountEqual(
            [r["mbid"] for r in resp.data["results"]],
            [mbid for mbid, _, _ in self.track_tuples]
        )

    def test_get_detail(self):
        track_tuple = self.track_tuples[0]
        url = reverse("api:track-detail", kwargs={"mbid": track_tuple[0]})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["mbid"], track_tuple[0])
        self.assertEqual(resp.data["title"], track_tuple[1])

    def test_get_detail_not_found_error_shape(self):
        url = reverse("api:track-detail", kwargs={"mbid": str(uuid.uuid4())})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 404)

    def test_get_features_includes_raw_features(self):
        mbid = self.track_tuples[0][0]
        with patch("recommend_api.api.track.rec") as mock_rec:
            features = np.array([0.5, 0.2])
            features_raw = np.array([50.0, 20.0])
            mock_rec.STORE.feature_names = ["danceability", "aggressiveness"]
            mock_rec.STORE.get_track_features.return_value = features
            mock_rec.STORE.get_track_features_raw.return_value = features_raw

            url = reverse("api:track-features", kwargs={"mbid": mbid})
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.data["track"]["mbid"], mbid)
            self.assertDictEqual(resp.data["features"], {
                "danceability": features[0], "aggressiveness": features[1]
            })
            self.assertDictEqual(resp.data["raw_features"], {
                "danceability": features_raw[0], "aggressiveness": features_raw[1]
            })

    def test_get_features_omits_raw_features_when_none(self):
        mbid = self.track_tuples[0][0]
        with patch("recommend_api.api.track.rec") as mock_rec:
            features = np.array([0.5, 0.2])
            mock_rec.STORE.feature_names = ["danceability", "aggressiveness"]
            mock_rec.STORE.get_track_features.return_value = features
            mock_rec.STORE.get_track_features_raw.return_value = None

            url = reverse("api:track-features", kwargs={"mbid": mbid})
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.data["track"]["mbid"], mbid)
            self.assertDictEqual(resp.data["features"], {
                "danceability": features[0], "aggressiveness": features[1]
            })
            self.assertNotIn("raw_features", resp.data)

    def test_get_sources(self):
        mbid = self.track_tuples[0][0]
        with patch("recommend_api.api.track.get_youtube_source") as mock_source:
            source = YTSource(
                video_id="foo-id",
                title="I Fooed 1000 Bars",
                channel="Mr. Foo",
                thumbnail="foo.png",
                url="http://foo.com",
            )
            mock_source.return_value = source
            url = reverse("api:track-sources", kwargs={"mbid": mbid})
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.data["track"]["mbid"], mbid)
            self.assertEqual(resp.data["sources"][0], {
                "provider": "youtube",
                "id": source.video_id,
                "title": source.title,
                "channel": source.channel,
                "thumbnail": source.thumbnail,
                "url": source.url,
            })

    def test_get_sources_not_found(self):
        mbid = self.track_tuples[0][0]
        with patch("recommend_api.api.track.get_youtube_source") as mock_source:
            mock_source.return_value = None
            url = reverse("api:track-sources", kwargs={"mbid": mbid})
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.data["track"]["mbid"], mbid)
            self.assertEqual(resp.data["sources"], [])

    def test_get_on_this_day_no_date(self):
        url = reverse("api:track-on-this-day")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        for result in resp.data["results"]:
            self.assertEqual(result["album"]["date"], datetime.today().strftime("%Y-%m-%d"))

    def test_get_on_this_day_default_cache_key_includes_server_date(self):
        url = reverse("api:track-on-this-day")
        with (
            patch("recommend_api.api.track.cache") as mock_cache,
            patch(
                "recommend_api.api.track.timezone.localdate",
                side_effect=[date(2026, 8, 25), date(2026, 8, 26)],
            ),
        ):
            mock_cache.get.return_value = None
            self.client.get(url)
            self.client.get(url)

        cache_keys = [call.args[0] for call in mock_cache.set.call_args_list]
        self.assertEqual(cache_keys, [
            "track:on_this_day:08-25:/api/v1/tracks/on_this_day/",
            "track:on_this_day:08-26:/api/v1/tracks/on_this_day/",
        ])

    def test_get_on_this_day_bad_date(self):
        url = reverse("api:track-on-this-day", query={"mmdd": "13-32"})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        for result in resp.data["results"]:
            self.assertEqual(result["album"]["date"], datetime.today().strftime("%Y-%m-%d"))

    def test_get_on_this_day_yesterday(self):
        yesterday = datetime.today() - timedelta(days=1)
        url = reverse("api:track-on-this-day", query={"mmdd": yesterday.strftime("%m-%d")})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        for result in resp.data["results"]:
            self.assertTrue(result["album"]["date"].endswith(yesterday.strftime("%m-%d")))

    def test_get_on_this_day_leap_year(self):
        url = reverse("api:track-on-this-day", query={"mmdd": "02-29"})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        for result in resp.data["results"]:
            self.assertTrue(result["album"]["date"].endswith("02-29"))

    def test_get_on_this_day_limits_tracks_per_artist(self):
        # Out of 2 tracks for the same artist released today, only one (popular one) is returned.
        artist = ArtistFactory.create()
        hit_track = TrackFactory.create(
            album=AlbumFactory.create(date=datetime.today()),
            submissions=2000,
        )
        mid_track = TrackFactory.create(
            album=AlbumFactory.create(date=datetime.today()),
            submissions=1000,
        )
        hit_track.artists.add(artist)
        mid_track.artists.add(artist)

        url = reverse("api:track-on-this-day")
        resp = self.client.get(url)

        self.assertEqual(resp.status_code, 200)
        result_mbids = [result["mbid"] for result in resp.data["results"]]
        self.assertIn(hit_track.musicbrainz_recordingid, result_mbids)
        self.assertNotIn(mid_track.musicbrainz_recordingid, result_mbids)

        artist_mbids = [
            artist["mbid"]
            for result in resp.data["results"]
            for artist in result["artists"]
        ]
        self.assertEqual(len(artist_mbids), len(set(artist_mbids)))

    def test_get_on_this_day_limits_tracks_per_album(self):
        album = AlbumFactory.create(date=datetime.today())
        hit_track = TrackFactory.create(album=album, submissions=2000)
        mid_track = TrackFactory.create(album=album, submissions=1000)
        hit_track.artists.add(ArtistFactory.create())
        mid_track.artists.add(ArtistFactory.create())

        url = reverse("api:track-on-this-day")
        resp = self.client.get(url)

        self.assertEqual(resp.status_code, 200)
        result_mbids = [result["mbid"] for result in resp.data["results"]]
        self.assertIn(hit_track.musicbrainz_recordingid, result_mbids)
        self.assertNotIn(mid_track.musicbrainz_recordingid, result_mbids)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        AlbumFactory.reset_sequence(0)
        TrackFactory.reset_sequence(0)


class TrackAPITests_DailyPicks(APITestCase):
    @classmethod
    def setUpTestData(cls):
        genre_dortmund = GenreDortmundFactory.create()
        genre_rosamerica = GenreRosamericaFactory.create()

        cls.track_tuples = []
        for i in range(100):
            submissions = 50 if i < 10 else 100 + i
            cls.track_tuples.append((str(uuid.uuid4()), f"Daily Pick Song {i}", submissions))

        Track.objects.bulk_create([
            Track(
                musicbrainz_recordingid=mbid,
                title=title,
                duration=180.0,
                genre_dortmund=genre_dortmund,
                genre_rosamerica=genre_rosamerica,
                submissions=subs,
            )
            for mbid, title, subs in cls.track_tuples
        ])

    def test_get_daily_picks(self):
        url = reverse("api:track-daily-picks")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], 90)
        for result in resp.data["results"]:
            self.assertGreaterEqual(result["submissions"], 100)

    def test_daily_picks_stable_order(self):
        url = reverse("api:track-daily-picks")
        first_resp = self.client.get(url)
        second_resp = self.client.get(url)

        self.assertEqual(first_resp.status_code, 200)
        self.assertEqual(second_resp.status_code, 200)

        first_mbids = [r["mbid"] for r in first_resp.data["results"]]
        second_mbids = [r["mbid"] for r in second_resp.data["results"]]
        self.assertEqual(first_mbids, second_mbids)

    def test_get_daily_picks_random_order(self):
        first_day = datetime.fromisoformat("2026-01-01").date()
        second_day = datetime.fromisoformat("2024-03-12").date()
        url = reverse("api:track-daily-picks")

        with patch("recommend_api.api.track.timezone.localdate", return_value=first_day):
            first_resp = self.client.get(url)

        with patch("recommend_api.api.track.timezone.localdate", return_value=second_day):
            second_resp = self.client.get(url)

        self.assertEqual(first_resp.status_code, 200)
        self.assertEqual(second_resp.status_code, 200)

        first_mbids = [r["mbid"] for r in first_resp.data["results"]]
        second_mbids = [r["mbid"] for r in second_resp.data["results"]]
        self.assertNotEqual(first_mbids, second_mbids)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()


class TrackAPITests_TopTracks(APITestCase):
    @classmethod
    def setUpTestData(cls):
        shared_album = AlbumFactory.create()
        shared_artist = ArtistFactory.create()
        other_artists = [ArtistFactory.create() for _ in range(3)]

        cls.tracks = [
            TrackFactory.create(album=shared_album, submissions=400),
            TrackFactory.create(album=shared_album, submissions=300),
            TrackFactory.create(album=AlbumFactory.create(), submissions=200),
            TrackFactory.create(album=AlbumFactory.create(), submissions=100),
        ]
        cls.tracks[0].artists.add(shared_artist)
        cls.tracks[1].artists.add(other_artists[0])
        cls.tracks[2].artists.add(shared_artist)
        cls.tracks[3].artists.add(other_artists[1])

    def test_get_top_tracks_limits_albums_and_artists(self):
        url = reverse("api:track-top-tracks")
        resp = self.client.get(url)

        self.assertEqual(resp.status_code, 200)
        self.assertLess(resp.data["count"], len(self.tracks))

        album_mbids = [result["album"]["mbid"] for result in resp.data["results"]]
        artist_mbids = [
            artist["mbid"]
            for result in resp.data["results"]
            for artist in result["artists"]
        ]
        self.assertEqual(len(album_mbids), len(set(album_mbids)))
        self.assertEqual(len(artist_mbids), len(set(artist_mbids)))
