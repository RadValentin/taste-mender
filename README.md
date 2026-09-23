<h1 align="center">TasteMender</h1>

<p align="center">
  <b>Privacy-first music discovery through acoustic similarity</b>
</p>

<p align="center">
  <a href="https://taste-mender.com/">
    <img src="https://img.shields.io/badge/demo-taste--mender.com-blue" alt="Live demo">
  </a>
  <a href="https://github.com/RadValentin/taste-mender/actions/workflows/django.yml">
    <img src="https://github.com/RadValentin/taste-mender/actions/workflows/django.yml/badge.svg?branch=main&amp;event=push" alt="Django CI">
  </a>
  <a href="https://codecov.io/gh/RadValentin/taste-mender">
    <img src="https://codecov.io/gh/RadValentin/taste-mender/graph/badge.svg?token=JfbmGuIWGl" alt="codecov">
  </a>
  <a href="LICENSE">
    <img src="https://img.shields.io/github/license/RadValentin/taste-mender" alt="License">
  </a>
</p>

## Overview

TasteMender is a music discovery app that recommends songs based on acoustic characteristics such as danceability, energy, mood, and genre. It takes a privacy-first approach: user behaviour is not tracked, and recommendations are based solely on each song's characteristics. Users have full control over how recommendations are generated through a robust set of filters.

It uses a Django REST API with a React frontend, and identifies tracks, artists, and albums using MusicBrainz IDs. Audio features and metadata are extracted from the [AcousticBrainz dataset](https://acousticbrainz.org/). Entities (tracks, artists, albums) are identified through [MusicBrainz IDs](https://musicbrainz.org/doc/MusicBrainz_Identifier) (MBID).

For more information, see the [development guidelines](docs/DEVELOPMENT.md) and [testing guidelines](docs/TESTING.md).

> [!NOTE]
> The app was originally developed as a final project for the BSc Computer Science degree at Goldsmiths, University of London (available [here](https://github.com/RadValentin/CM3070-FP-Music-Recommendation)). This repository continues that work, aiming to eventually provide a fully-featured music discovery experience.

### Motivation

I believe that finding new media to enjoy nowadays is an increasingly arduous task. Consumers' fragmenting tastes are tied to the ever growing breadth of available content and serendipitous discovery of interesting music, movies, games, etc. is a rare event. Online platforms pigeonhole users into highly personalized but restrictive content bubbles and don't offer much direct control over how content recommendations are made. Often times it feels impossible to find media that's outside of your own interests but that you can still enjoy.

I want for TasteMender to be an "eject button" from the behavior-driven machine. It's purposely built to give music recommendations solely based on the intrinsic characteristics of the songs themselves. It's not concerned with user behaviour in any way while at the same time giving them as much direct control as possible over what gets recommended. You actively tell the system what you want rather than it predicting that for you.

### Repo Structure

- `backend/`
  - `music_recommendation/` - the main Django project
  - `recommend_api/` - recommendation API
    - `api/` - endpoint implementations
    - `services/`
      - `recommender.py` - recommendation logic
      - `youtube_sources.py` - gets playable sources for tracks
    - `tests/` - API and service tests
    - `models.py` - database models
    - `serializers.py` - API response and validation serializers
  - `ingest/` - AcousticBrainz dataset processing and database-building tools
    - `management/commands/` - Django commands such as `build_db` and `recommend`
    - `tests/` - ingest pipeline tests
  - `features_and_index*.npz` - generated recommendation feature data
- `frontend/` - React and TypeScript app that consumes the API
  - `src/pages/` - application pages
  - `src/components/` - reusable UI components
  - `src/hooks/` - shared React hooks
  - `src/api.ts` - API client
- `docs/` - development, testing, architecture, roadmap, and decision records

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

