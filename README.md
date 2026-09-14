# TasteMender: A stateless music recommendation API

[![codecov](https://codecov.io/gh/RadValentin/taste-mender/graph/badge.svg?token=JfbmGuIWGl)](https://codecov.io/gh/RadValentin/taste-mender)

> [!NOTE]
> Originally developed as a final project for the BSc Computer Science degree at Goldsmiths, University of London (available [here](https://github.com/RadValentin/CM3070-FP-Music-Recommendation)). This repository continues that work, aiming to transform it into a deployable music discovery web app.

TasteMender is a music discovery app that recommends songs based on acoustic characteristics such as danceability, energy, mood, and genre. It takes a privacy-first approach: user behaviour is not tracked, and recommendations are based solely on each song’s characteristics. Users can also control how recommendations are generated through a robust set of filters.

It uses a Django REST API with a React frontend, and identifies tracks, artists, and albums using MusicBrainz IDs. Audio features and metadata are taken from the [AcousticBrainz dataset](https://acousticbrainz.org/).

For more information, see the [development guidelines](docs/DEVELOPMENT.md) and [testing guidelines](docs/TESTING.md).

## Repo Structure

- `backend/`
  - `music_recommendation/` - the main Django project
  - `recommend_api/` - recommendation API
    - `services/`
      - `recommender.py` - recommendation logic
      - `youtube_sources.py` - gets playable sources for tracks
    - `tests/` - unit tests
    - `api.py` - endpoint views
  - `ingest/` - scripts for building the DB
    - `management/commands/`
      - `build_db.py` - dataset ingest and DB build command
      - `recommend.py` - command for showing recommendations
- `frontend/` - standalone app that consumes the API

## How It Works

### Dataset Ingest

Track data is loaded from the [DB dumps](https://acousticbrainz.org/download) of the AcousticBrainz dataset. The build pipeline does the following:

1. Stream JSON data from `.tar.zst` archives, processing the archives in parallel
1. Extract relevant information from each file (title, audio features, metadata), discarding those that have missing or invalid data
1. Build a hashmap (`track_index`) of duplicate tracks indexed by their MusicBrainz ID (`musicbrainz_recordingid`)
1. Merge duplicates into a single entry by selecting the most common value for each field (title, audio features, metadata)
1. Build the DB models:
  1. `Track` from `track_index`
  1. `Artist`, `Album` and M2M pairings (`AlbumArtist`, `TrackArtist`) from the track metadata
1. Extract audio features to a separate file (`features_and_index.npz`), this will be loaded into memory by the Django app to allow for fast searching

Because many popular tracks are duplicated in the dataset, the final number of tracks that the app will be working with is considerably lower than what was ingested.

$$finalSize = datasetSize - duplicateCount - tracksMissingData - tracksMissingArtist$$

For the sample dataset (100k tracks), 85732 unique entries will be loaded:
$$85732 = 100000 - 11182 - 4 - 3082$$

