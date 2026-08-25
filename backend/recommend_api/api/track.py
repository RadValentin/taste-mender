import logging, time, random
from collections import OrderedDict
from django.conf import settings
from django.core.cache import cache
from django.db.models import Value, Func
from django.db.models.functions import Concat
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response
from recommend_api.models import *
from recommend_api.serializers import *
from recommend_api.services.youtube_sources import get_youtube_source
import recommend_api.services.recommender as rec

log = logging.getLogger(__name__)


class TrackViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TrackSerializer
    queryset = Track.objects.select_related(
        "album",
        "genre_dortmund",
        "genre_rosamerica",
    ).prefetch_related("artists")
    lookup_field = "musicbrainz_recordingid"
    lookup_url_kwarg = "mbid"
    filter_backends = [OrderingFilter]
    # fields that may be ordered against
    ordering_fields = ["title", "album__date", "submissions"]
    # default ordering
    ordering = ["pk"]

    def list(self, request, *args, **kwargs):
        response: Response = super().list(request, *args, **kwargs)
        links = {
            "self": request.build_absolute_uri(reverse("api:track-list")),
            "daily_picks": request.build_absolute_uri(reverse("api:track-daily-picks")),
            "on_this_day": request.build_absolute_uri(reverse("api:track-on-this-day")),
            "top_tracks": request.build_absolute_uri(reverse("api:track-top-tracks")),
        }
        response.data = OrderedDict(**response.data or {}, links=links)
        return response


    @extend_schema(
        responses=TrackFeaturesResponseSerializer,
        description="Get track metadata along with audio features (scaled and unscaled)"
    )
    @action(detail=True, methods=["get"], url_path="features")
    def features(self, request, *args, **kwargs):
        track: Track = self.get_object()
        mbid = track.musicbrainz_recordingid

        features_dict = {}
        raw_features_dict = {}
        features = None
        raw_features = None

        # Handle unlikely case that MBID doesn't have associated audio features.
        try:
            features = rec.STORE.get_track_features(mbid)
            raw_features = rec.STORE.get_track_features_raw(mbid)
            for i, feature in enumerate(features):
                features_dict[rec.STORE.feature_names[i]] = feature
                if raw_features is not None:
                    raw_features_dict[rec.STORE.feature_names[i]] = raw_features[i]
        except ValueError as e:
            log.exception(f"Failed to get track metadata, {e}")

        serializer = TrackFeaturesResponseSerializer({
            "track": track,
            "features": features_dict,
            **({"raw_features": raw_features_dict} if raw_features is not None else {}),
        })
        return Response(serializer.data)


    @extend_schema(
        description="Get a list of sources for a track (Youtube)"
    )
    @action(detail=True)
    def sources(self, request, *args, **kwargs):
        track = self.get_object()

        try:
            source = get_youtube_source(track)
        except Exception as e:
            log.exception(f"YouTube lookup failed, {e}")
            payload = {"track": TrackSerializer(track).data, "sources": []}
            if settings.DEBUG:
                payload["debug"] = {"error": str(e)}
            return Response(payload, status=200)

        if not source:
            payload = {"track": TrackSerializer(track).data, "sources": []}
            return Response(payload, status=200)

        data = [{
            "provider": "youtube",
            "id": source.video_id,
            "title": source.title,
            "channel": source.channel,
            "thumbnail": source.thumbnail,
            "url": source.url,
        }]

        return Response({
            "track": TrackSerializer(track).data,
            "sources": data
        })


    @extend_schema(
        description="Random selection of popular tracks seeded by the current date, cached for 24h."
    )
    @method_decorator(never_cache)
    @action(detail=False, methods=["get"], url_path="daily_picks")
    def daily_picks(self, request, *args, **kwargs):
        min_submissions = settings.DAILY_PICKS_MIN_SUBMISSIONS
        seed = timezone.localdate().isoformat()
        cache_key = f"track:daily_picks:{seed}:{request.get_full_path()}"
        cached = cache.get(cache_key)

        if cached is not None:
            return Response(cached)

        queryset = (
            self.get_queryset()
            .filter(submissions__gte=min_submissions)
            .annotate(
                stable_random_order=Func(
                    Concat(Value(seed), Value(":"), "musicbrainz_recordingid"),
                    function="MD5",
                )
            )
            .order_by("stable_random_order", "musicbrainz_recordingid")
        )

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            cache.set(cache_key, response.data, timeout=60 * 60 * 24)
            return response

        serializer = self.get_serializer(queryset, many=True)
        cache.set(cache_key, serializer.data, timeout=60 * 60 * 24)
        return Response(serializer.data)


    @extend_schema(
        description="Tracks released on today's date across the years. Defaults to server date for missing/invalid mmdd.",
        parameters=[
            OpenApiParameter(
                name="mmdd",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Release day and month, mm-dd format",
            )
        ],
    )
    @method_decorator(never_cache)
    @action(detail=False, methods=["get"], url_path="on_this_day")
    def on_this_day(self, request, *args, **kwargs):
        # Try to parse request date, default to server date if invalid.
        server_date = timezone.localdate()
        day: int = server_date.day
        month: int = server_date.month
        mmdd: str = request.GET.get("mmdd", "").strip()

        if mmdd:
            try:
                struct_time = time.strptime(f"1904 {mmdd}", "%Y %m-%d")
                day = struct_time.tm_mday
                month = struct_time.tm_mon
            except ValueError:
                log.warning("Failed to parse date %r, falling back to server date.", mmdd)

        cache_key = f"track:on_this_day:{month:02d}-{day:02d}:{request.get_full_path()}"
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        # In the worst case there can be 100K tracks+ released on a certain day.
        # Doing filter+sort in the QS would tank performance. It's easier to sort a limited subset.
        queryset = (
            Track.objects
            .filter(album__date__month=month, album__date__day=day)
            .prefetch_related("artists")[:5000]
        )

        queryset_objs = sorted(queryset, key=lambda o: o.submissions, reverse=True)

        seen_artists = set()
        unique_tracks = []

        for track in queryset_objs:
            artist_ids = {artist.pk for artist in track.artists.all()}

            if seen_artists.isdisjoint(artist_ids):
                unique_tracks.append(track)
                seen_artists.update(artist_ids)

        page = self.paginate_queryset(unique_tracks)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            cache.set(cache_key, response.data, timeout=60 * 60 * 24 * 30)
            return response

        serializer = self.get_serializer(unique_tracks, many=True)
        cache.set(cache_key, serializer.data, timeout=60 * 60 * 24 * 30)
        return Response(serializer.data)


    @extend_schema(
        description="Popular tracks with one track per album/artist, shuffled daily."
    )
    @method_decorator(never_cache)
    @action(detail=False, methods=["get"], url_path="top_tracks")
    def top_tracks(self, request, *args, **kwargs):
        seed = timezone.localdate().isoformat()
        cache_key = f"track:top_tracks:{seed}:{request.get_full_path()}"
        cached = cache.get(cache_key)

        if cached is not None:
            return Response(cached)

        # Start with genuinely popular tracks, then introduce some daily variety.
        tracks = list(
            self.get_queryset()
            .order_by("-submissions")[:500]
        )

        random.Random(seed).shuffle(tracks)

        seen_albums = set()
        seen_artists = set()
        unique_tracks = []

        for track in tracks:
            album_id = track.album_id
            artist_ids = {artist.pk for artist in track.artists.all()}

            if album_id in seen_albums:
                continue

            if not seen_artists.isdisjoint(artist_ids):
                continue

            unique_tracks.append(track)

            if album_id is not None:
                seen_albums.add(album_id)

            seen_artists.update(artist_ids)

        page = self.paginate_queryset(unique_tracks)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            cache.set(cache_key, response.data, timeout=60 * 60 * 24)
            return response

        serializer = self.get_serializer(unique_tracks, many=True)
        cache.set(cache_key, serializer.data, timeout=60 * 60 * 24)

        return Response(serializer.data)