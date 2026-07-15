import logging, time
import numpy as np
from collections import OrderedDict
from datetime import datetime
from django.conf import settings
from django.urls import reverse
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import viewsets, status
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
        description="Random selection of popular tracks seeded by the current date, cached for 24h"
    )
    @action(detail=False, methods=["get"], url_path="daily_picks")
    def daily_picks(self, request, *args, **kwargs):
        tracks = Track.objects.order_by("pk")[:20]
        serializer = self.get_serializer(tracks, many=True)
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
    @action(detail=False, methods=["get"], url_path="on_this_day")
    def on_this_day(self, request, *args, **kwargs):
        # Try to parse request date, default to server date if invalid.
        day: int = datetime.today().day
        month: int = datetime.today().month
        mmdd: str = request.GET.get("mmdd", "").strip()

        if mmdd:
            try:
                struct_time = time.strptime(f"1904 {mmdd}", "%Y %m-%d")
                day = struct_time.tm_mday
                month = struct_time.tm_mon
            except ValueError:
                log.warning(f"Failed to parse date {mmdd}, falling back to server date.")

        queryset = Track.objects.filter(album__date__month=month, album__date__day=day)[:5000]
        queryset_objs = sorted(queryset, key=lambda o: o.submissions, reverse=True)
        page = self.paginate_queryset(queryset_objs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset_objs, many=True)
        return Response(serializer.data)
