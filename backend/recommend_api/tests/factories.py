import factory # type: ignore[import-untyped]
from django.contrib.postgres.search import SearchVector
from factory.django import DjangoModelFactory
from random import randint, choice

DORTMUND_GENRES = [
    {"code": 0, "label": "electronic"},
    {"code": 1, "label": "folkcountry"},
    {"code": 2, "label": "blues"},
    {"code": 3, "label": "jazz"},
    {"code": 4, "label": "alternative"},
    {"code": 5, "label": "rock"},
    {"code": 6, "label": "raphiphop"},
    {"code": 7, "label": "pop"},
    {"code": 8, "label": "funksoulrnb"},
]

ROSAMERICA_GENRES = [
    {"code": 0, "label": "rhy"},
    {"code": 1, "label": "dan"},
    {"code": 2, "label": "pop"},
    {"code": 3, "label": "roc"},
    {"code": 4, "label": "cla"},
    {"code": 5, "label": "hip"},
    {"code": 6, "label": "jaz"},
    {"code": 7, "label": "spe"},
]
from recommend_api.models import Artist, Album, Track, GenreDortmund, GenreRosamerica


class ArtistFactory(DjangoModelFactory):
    class Meta:
        model = Artist

    musicbrainz_artistid = factory.Sequence(lambda n: f"artist-{n}")
    name = factory.Faker("name")


class AlbumFactory(DjangoModelFactory):
    class Meta:
        model = Album

    musicbrainz_albumid = factory.Sequence(lambda n: f"album-{n}")
    name = factory.Faker("sentence", nb_words=2)
    date = factory.Faker("date")


class GenreDortmundFactory(DjangoModelFactory):
    class Meta:
        model = GenreDortmund
        django_get_or_create = ("code", "label")
        exclude = ["_data"]

    _data = factory.LazyFunction(lambda: choice(DORTMUND_GENRES))
    code = factory.LazyAttribute(lambda o: o._data["code"])
    label = factory.LazyAttribute(lambda o: o._data["label"])


class GenreRosamericaFactory(DjangoModelFactory):
    class Meta:
        model = GenreRosamerica
        django_get_or_create = ("code", "label")
        exclude = ["_data"]

    _data = factory.LazyFunction(lambda: choice(ROSAMERICA_GENRES))
    code = factory.LazyAttribute(lambda o: o._data["code"])
    label = factory.LazyAttribute(lambda o: o._data["label"])


class TrackFactory(DjangoModelFactory):
    class Meta:
        model = Track

    musicbrainz_recordingid = factory.Sequence(lambda n: f"track-{n}")
    album = factory.SubFactory(AlbumFactory)
    title = factory.Faker("sentence", nb_words=2)
    duration = factory.LazyAttribute(lambda o: randint(1, 1000))
    genre_dortmund = factory.SubFactory(GenreDortmundFactory)
    genre_rosamerica = factory.SubFactory(GenreRosamericaFactory)
    submissions = factory.LazyAttribute(lambda o: randint(1, 100))

    # NOTE: These are used for full-text search logic.
    artists_text = ""
    search_vector = None

    @factory.post_generation
    def populate_search_vector(obj, create, extracted, **kwargs):
        """Populate search_vector after track is created (matches ingest pipeline)."""
        if create:
            search_vector = (
                SearchVector("title", config="simple", weight="A") +
                SearchVector("artists_text", config="simple", weight="B")
            )
            Track.objects.filter(pk=obj.pk).update(search_vector=search_vector)
            obj.refresh_from_db()
