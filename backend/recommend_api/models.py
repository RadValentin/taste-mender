from django.db import models
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex, GistIndex


class Artist(models.Model):
    musicbrainz_artistid = models.CharField(primary_key=True, max_length=36)
    name = models.CharField(max_length=255)

    class Meta:
        indexes = [
            GinIndex(fields=["name"], name="artist_name_trgm", opclasses=["gin_trgm_ops"]),
            GistIndex(fields=["name"], name="artist_name_trgm_gist", opclasses=["gist_trgm_ops"]),
        ]


class Album(models.Model):
    musicbrainz_albumid = models.CharField(primary_key=True, max_length=36)
    name = models.CharField(max_length=255)
    artists = models.ManyToManyField(Artist, through="AlbumArtist")
    date = models.DateField(null=True, blank=True)

    class Meta:
        indexes = [
            GinIndex(fields=["name"], name="album_name_trgm", opclasses=["gin_trgm_ops"]),
            GistIndex(fields=["name"], name="album_name_trgm_gist", opclasses=["gist_trgm_ops"]),
        ]


class AlbumArtist(models.Model):
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE)
    album = models.ForeignKey(Album, on_delete=models.CASCADE)
    # releasecountry = models.CharField(blank=True, null=True, max_length=255)

    class Meta:
        unique_together = [("artist", "album")]


class GenreDortmund(models.Model):
    code = models.PositiveSmallIntegerField(primary_key=True)
    label = models.CharField(max_length=64, unique=True)

    def __str__(self):
        return self.label


class GenreRosamerica(models.Model):
    code = models.PositiveSmallIntegerField(primary_key=True)
    label = models.CharField(max_length=64, unique=True)

    def __str__(self):
        return self.label


class Track(models.Model):
    musicbrainz_recordingid = models.CharField(primary_key=True, max_length=36)
    album = models.ForeignKey(Album, on_delete=models.CASCADE, null=True, blank=True)
    artists = models.ManyToManyField(
        Artist, through="TrackArtist", related_name="tracks"
    )
    title = models.TextField()
    duration = models.FloatField()
    genre_dortmund = models.ForeignKey(GenreDortmund, on_delete=models.PROTECT)
    genre_rosamerica = models.ForeignKey(GenreRosamerica, on_delete=models.PROTECT)
    submissions = models.IntegerField()
    artists_text = models.TextField(default="", blank=True)
    search_vector = SearchVectorField(null=True)

    source_found_count = models.IntegerField(default=0)
    source_not_found_count = models.IntegerField(default=0)

    class Meta:
        indexes = [
            # Speed up searching tracks by title for short queries (<= 3 chars)
            GinIndex(fields=["title"], name="track_title_trgm", opclasses=["gin_trgm_ops"]),
            # Speed up backfilling full-text results with tracks matched using trigram distance
            GistIndex(fields=["title"], name="track_title_trgm_gist", opclasses=["gist_trgm_ops"]),
            # Speed up full-text search on tracks by title + artist name
            GinIndex(fields=["search_vector"], name="track_search_vector_gin"),

            # Optimize retrieving most popular tracks
            models.Index(fields=["submissions"], name="track_subs_idx"),
        ]


class TrackArtist(models.Model):
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE)
    track = models.ForeignKey(Track, on_delete=models.CASCADE)

    class Meta:
        unique_together = [("track", "artist")]
