import logging, math
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import APIException, NotFound, ValidationError
from rest_framework.generics import GenericAPIView
from rest_framework.parsers import JSONParser, FormParser
from rest_framework.response import Response
from recommend_api.models import *
from recommend_api.serializers import *
import recommend_api.services.recommender as rec

log = logging.getLogger(__name__)


class RecommenderDataUnavailable(APIException):
    status_code = 503
    default_detail = "Recommendation data unavailable."
    default_code = "service_unavailable"


class RecommendView(GenericAPIView):
    serializer_class = RecommendRequestSerializer
    parser_classes = [JSONParser, FormParser]

    @extend_schema(
        request=RecommendRequestSerializer,
        responses=RecommendResponseSerializer,
        description="Recommend similar tracks for a given MusicBrainz recording ID. Returns the target track, a list of similar tracks (with similarity scores), and recommendation statistics."
    )
    def post(self, request):
        # Process options
        serializer = RecommendRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_mbid: str = serializer.validated_data.get("mbid")
        if not target_mbid:
            raise ValidationError("Missing 'mbid' parameter.")

        listened_mbids: list = serializer.validated_data.get("listened_mbids", [])
        filters: dict = serializer.validated_data.get("filters", {})
        feature_weights: dict = serializer.validated_data.get("feature_weights", {})
        total_weights: dict = serializer.validated_data.get("total_weights", {})
        limit: int = serializer.validated_data.get("limit", 10)
        limit: int = min(limit, 50)
        use_ros: bool = filters.get("genre_classification", "rosamerica") == "rosamerica"
        same_genre: bool = filters.get("same_genre", True)
        same_decade: bool = filters.get("same_decade", True)

        try:
            target_track: Track = Track.objects.select_related(
                "album",
                "genre_dortmund",
                "genre_rosamerica",
            ).prefetch_related("artists").get(musicbrainz_recordingid=target_mbid)
            target_artist: Artist = target_track.artists.first()
        except Track.DoesNotExist:
            raise NotFound("Target track not found")

        # Get the recommendations dict, ask for a large number of similar tracks (50)
        # so we can have a buffer in case we need to filter the data
        # (e.g. same artist shows up multiple times)
        try:
            recommendations = rec.recommend(
                target_mbid=target_mbid,
                options={
                    "k": limit*10,
                    "use_ros": use_ros,
                    "exclude_mbids": listened_mbids,
                    "match_genre": same_genre,
                    "match_decade": same_decade,
                    "feature_weights": feature_weights,
                }
            )
            top_tracks = recommendations["top_tracks"]
        except ValueError as e:
            # MBID not found in feature matrix
            raise ValidationError(str(e))
        except FileNotFoundError as e:
            # Feature matrix data couldn't be loaded from disk
            raise RecommenderDataUnavailable(detail=str(e))
        except Exception as e:
            # Any other error
            log.exception(f"Unexpected error in similar_tracks: {e}")
            raise APIException("Unexpected error while generating recommendations.")

        # Build the QuerySet for the similar track data and create an index based on MBID
        top_mbids = [t["mbid"] for t in top_tracks]
        track_map = {
            t.musicbrainz_recordingid: t
            for t in Track.objects.filter(
                musicbrainz_recordingid__in=top_mbids
            ).select_related(
                "album",
                "genre_dortmund",
                "genre_rosamerica",
            ).prefetch_related("artists")
        }

        # add popularity and combined score
        similarity_weight = total_weights.get("similarity", 0.9)
        popularity_weight = total_weights.get("popularity", 0.1)
        for track in top_tracks:
            submissions = track_map.get(track["mbid"]).submissions
            # simple blend: mostly similarity, small nudge from popularity
            track["final_score"] = (
                similarity_weight * track["similarity"] +
                popularity_weight * math.log1p(submissions)
            )

        # rerank by final score
        top_tracks.sort(key=lambda x: x["final_score"], reverse=True)


        # Go through the similar tracks and extract a subset by filtering for
        # artist name, track title, etc.
        seen_artists = set()
        similar_list = []
        for track in top_tracks:
            # Skip is target track is encountered again somehow
            if track["mbid"] == target_mbid:
                continue

            track_obj = track_map.get(track["mbid"])
            if not track_obj:
                continue

            artist = track_obj.artists.first()
            artist_name = artist.name if artist else "Unknown Artist"

            # Skip if it's the same song by the same artist as the target track
            if (artist_name == target_artist.name and track_obj.title == target_track.title):
                continue

            # Only allow 1 track per artist
            if artist in seen_artists:
                continue
            seen_artists.add(artist)

            # Include similarity score for the track
            track_obj.similarity = track["similarity"]
            similar_list.append(track_obj)

            # Limit the subset
            if len(similar_list) >= limit:
                break

        data = {
            "target_track": target_track,
            "similar_list": similar_list,
            "stats": recommendations["stats"],
        }
        response_serializer = RecommendResponseSerializer(data)
        return Response(response_serializer.data)
