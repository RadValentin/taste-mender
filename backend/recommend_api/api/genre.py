import logging
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView
from recommend_api.models import *
from recommend_api.serializers import *

log = logging.getLogger(__name__)


class GenreView(APIView):
    @extend_schema(
        responses=GenreResponseSerializer,
        description="Get unique names of music genres in DB grouped by classifier.",
    )
    def get(self, request, *args, **kwargs):
        genres_dortmund = GenreDortmund.objects.values_list("label", flat=True).order_by("label")
        genres_rosamerica = GenreRosamerica.objects.values_list("label", flat=True).order_by("label")

        data = {
            "genre_dortmund": list(genres_dortmund),
            "genre_rosamerica": list(genres_rosamerica),
        }
        serializer = GenreResponseSerializer(data)
        return Response(serializer.data)
