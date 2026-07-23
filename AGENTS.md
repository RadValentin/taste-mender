# TasteMender – AI Agent Context Document

This document provides a full description of the TasteMender project so that an AI agent can understand what it is, how it works, and why it was built. Use this as a starting point for any conversation about new features, architecture decisions, or technical changes.

---

## What Is TasteMender?

TasteMender is a **music discovery web application** that recommends songs based on audio similarity. Given a track the user is already listening to, TasteMender finds other tracks that *sound* like it — matching on acoustic properties such as danceability, energy, mood, and genre — rather than relying on listening history, social data, or collaborative filtering.

- **Live URL:** https://taste-mender.com/
- **Repository:** https://github.com/RadValentin/taste-mender/

The project began as a BSc Computer Science final project at Goldsmiths, University of London, and is being evolved into a fully deployable music discovery web app.

---

## Core Features

1. **Track search** – Find tracks by title using full-text and trigram similarity search.
2. **Audio-feature-based recommendations** – Given a seed track, return the most acoustically similar tracks from the database, with optional genre and decade filtering.
3. **YouTube playback** – Each track is resolved to a playable YouTube video via the YouTube Data API. The player is embedded in the UI using the YouTube IFrame API.
4. **Auto-play queue** – When a video ends, the top recommendation is automatically loaded and played next.
5. **Tunable recommendation filters** – Users can adjust:
   - Genre guardrails: same-genre filter using Rosamerica or Dortmund classification systems.
   - Era guardrails: same-decade filter.
   - Feature weights: 11 audio features + 5 MIREX mood features, each adjustable with a slider.
   - Ranking balance: how much to weight cosine similarity vs. track popularity.
6. **Top tracks** – Default view shows the most popular (most-submitted) tracks in the database.
7. **REST API** – All data is served through a versioned REST API with Swagger/ReDoc documentation.
8. **Album cover art** – Served via the Cover Art Archive (CAA) using the track's MusicBrainz release ID.

---

## Tech Stack

### Backend
| Technology | Role |
|---|---|
| **Python 3.14** | Primary backend language |
| **Django 5.2** | Web framework, ORM, management commands |
| **Django REST Framework (DRF)** | REST API layer, serializers, pagination |
| **drf-spectacular** | Auto-generated OpenAPI schema, Swagger UI, ReDoc |
| **PostgreSQL 18** | Primary database (with trigram and full-text search extensions) |
| **psycopg2** | PostgreSQL adapter for Python |
| **NumPy** | In-memory feature matrix storage and vector operations |
| **scikit-learn** | Cosine similarity computation for recommendations |
| **Gunicorn** | Production WSGI server |
| **WhiteNoise** | Static file serving from Django |
| **orjson** | Fast JSON parsing during data ingest |
| **zstandard** | Decompression of `.tar.zst` dataset archives |
| **python-dotenv** | Environment variable management |
| **dj-database-url** | DATABASE_URL parsing |
| **django-cors-headers** | CORS support |
| **django-filter** | Query-string-based filtering for list endpoints |

### Frontend
| Technology | Role |
|---|---|
| **React 19** | UI framework |
| **TypeScript** | Type-safe frontend code |
| **Vite** | Build tool and dev server |
| **Axios** | HTTP client for API calls |
| **YouTube IFrame API** | Embedded video player |
| **Font Awesome** | UI icons |

### Infrastructure & Deployment
| Technology | Role |
|---|---|
| **Docker / Docker Compose** | Container-based deployment (multi-stage build) |
| **Nginx** | Reverse proxy, HTTPS termination, static file caching |
| **Let's Encrypt / Certbot** | SSL certificate management |
| **DigitalOcean** (implied) | Cloud hosting (VPS / Droplet) |

---

## Architecture Overview

```
Browser
  └── Nginx (HTTPS, reverse proxy)
        └── Gunicorn (WSGI)
              └── Django app (port 8000)
                    ├── REST API (/api/v1/*)
                    │     ├── recommend_api (recommendation + browse endpoints)
                    │     └── ingest (DB build management commands)
                    ├── Static files (WhiteNoise serves frontend/dist/)
                    └── PostgreSQL 18 (separate Docker container)
```

The frontend is a single-page React app (SPA). It is built at Docker image build time (`npm run build`) and served as static files by WhiteNoise from Django. In production, Nginx proxies all traffic (both API and frontend) to the single Django/Gunicorn container on port 8000.

The **feature matrix** (`features_and_index.npz`) is a NumPy `.npz` file that stores all audio feature vectors. It is loaded once into memory at process startup via a singleton `FeatureStore` class. Cosine similarity comparisons happen entirely in RAM against this matrix, making recommendations extremely fast (typically under 10ms for 80k+ tracks).

---

## Repository Structure

```
taste-mender/
├── backend/
│   ├── music_recommendation/     # Django project settings, WSGI, URLs
│   ├── recommend_api/            # Main Django app
│   │   ├── models.py             # Track, Artist, Album, Genre models
│   │   ├── serializers.py        # DRF serializers
│   │   ├── views.py              # DRF viewsets
│   │   ├── urls.py               # URL routing
│   │   ├── router.py             # DRF router config
│   │   ├── api/                  # Additional API view modules
│   │   ├── services/
│   │   │   ├── recommender.py    # Core recommendation logic (FeatureStore + cosine similarity)
│   │   │   └── youtube_sources.py # YouTube Data API integration
│   │   └── tests/                # Unit tests
│   ├── ingest/
│   │   └── management/commands/
│   │       ├── build_db.py       # Dataset ingest & DB build command
│   │       └── recommend.py      # CLI command to test recommendations
│   ├── Dockerfile                # Multi-stage Docker build (Node for FE, Python for BE)
│   ├── docker-compose.yml        # Django + PostgreSQL services
│   ├── requirements.txt          # Python dependencies
│   └── .env.example              # Environment variable template
├── frontend/
│   ├── src/
│   │   ├── App.tsx               # Root component (search, top tracks, layout)
│   │   ├── api.ts                # Typed API client (Axios)
│   │   ├── types.ts              # TypeScript interfaces for all API types
│   │   ├── PlayerContext.tsx     # React context for player open/close state
│   │   ├── PlayerProvider.tsx    # Context provider wrapper
│   │   └── components/
│   │       ├── Player.tsx        # YouTube player + recommendations + stats
│   │       ├── Filters.tsx       # Recommendation settings panel
│   │       ├── Header.tsx        # App header with search bar
│   │       ├── TrackList.tsx     # Renders a list of TrackItem
│   │       ├── TrackItem.tsx     # Single track row with play button
│   │       ├── PlayButton.tsx    # Reusable play button
│   │       ├── ImageLoader.tsx   # Album art with fallback
│   │       └── LoadingSpinner.tsx
│   └── package.json
└── docs/                         # Design documents, API spec, progress log, ERD
```

---

## Data Models

All primary keys are **MusicBrainz IDs (MBIDs)** — 36-character UUID strings used by the MusicBrainz open music encyclopedia.

### `Track`
- `musicbrainz_recordingid` (PK) – unique recording ID
- `title` – track title
- `duration` – in seconds
- `album` (FK → `Album`, nullable)
- `artists` (M2M → `Artist` via `TrackArtist`)
- `genre_dortmund` (FK → `GenreDortmund`)
- `genre_rosamerica` (FK → `GenreRosamerica`)
- `submissions` – how many times this track appears in the AcousticBrainz dataset (used as a proxy for popularity)
- `artists_text` – denormalized plain-text artist names for fast full-text search
- `search_vector` – PostgreSQL `tsvector` for full-text search
- `source_found_count` / `source_not_found_count` – tracks how often a YouTube source was or was not found

### `Artist`
- `musicbrainz_artistid` (PK)
- `name`

### `Album`
- `musicbrainz_albumid` (PK)
- `name`
- `date` (nullable release date)
- `artists` (M2M → `Artist` via `AlbumArtist`)

### `GenreDortmund` / `GenreRosamerica`
- `code` (numeric PK)
- `label` (genre name string)

There are two genre classification systems in the dataset: **Rosamerica** (fewer, broader classes) and **Dortmund** (more granular). Both are stored and either can be used for filtering recommendations.

---

## Audio Features

Each track has a 16-dimensional feature vector stored in the NumPy feature matrix. The features are extracted by the AcousticBrainz analysis pipeline from raw audio:

**Perceptual / mood features (11):**
- danceability, aggressiveness, happiness, sadness, relaxedness, partyness, acousticness, electronicness, instrumentalness, tonality, brightness

**MIREX mood categories (5):**
- moods_mirex_1: Passionate / Cheerful / Rowdy
- moods_mirex_2: Poignant / Sad / Bittersweet
- moods_mirex_3: Humorous / Silly / Witty
- moods_mirex_4: Aggressive / Fiery / Intense
- moods_mirex_5: Peaceful / Relaxed / Calming

Features are **min-max normalized** to [0, 1] before storage. Cosine similarity is computed between the normalized feature vectors.

---

## Recommendation Algorithm

1. **Load seed track** – look up the target track's feature vector in the in-memory `FeatureStore` by MBID.
2. **Pre-filter candidates** – apply a boolean mask to the entire feature matrix to keep only tracks that match the desired genre (optional) and decade (optional), and are not in the excluded/listened list.
3. **Apply feature weights** – multiply the candidate feature matrix by a weight vector, where each weight (0–1) controls how much each audio feature influences similarity.
4. **Compute cosine similarity** – compare the target vector against all candidate vectors using `sklearn.metrics.pairwise.cosine_similarity`. This runs against a potentially large slice of an 80k+ row matrix in RAM.
5. **Rank and return top-k** – sort by descending similarity, take the top `k` tracks.
6. **Re-rank by popularity** – final score = `(similarity_weight × similarity) + (popularity_weight × normalized_submissions)`.
7. **Return stats** – alongside the results, return `candidate_count`, `search_time`, `mean`, `std`, `p95`, and `max` similarity scores.

The `FeatureStore` is a **singleton** loaded once at Django startup. All read-only arrays are `mmap`-backed and flagged non-writable to avoid accidental mutation.

---

## REST API

Base path: `/api/v1/`

Auto-generated docs:
- Swagger UI: `/api/v1/swagger-ui/`
- ReDoc: `/api/v1/redoc/`
- OpenAPI YAML: `/api/v1/schema/`

### Browse Endpoints
| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/` | List available endpoints |
| GET | `/api/v1/tracks/` | Paginated track list (orderable by `title`, `album__date`) |
| GET | `/api/v1/tracks/<mbid>/` | Track detail |
| GET | `/api/v1/tracks/<mbid>/features/` | Audio feature values (raw + normalized) |
| GET | `/api/v1/tracks/<mbid>/sources/` | YouTube video sources for a track |
| GET | `/api/v1/artists/` | Paginated artist list |
| GET | `/api/v1/artists/<mbid>/` | Artist detail |
| GET | `/api/v1/artists/<mbid>/tracks/` | All tracks by artist |
| GET | `/api/v1/artists/<mbid>/top-tracks/` | Most popular tracks by artist |
| GET | `/api/v1/artists/<mbid>/albums/` | Albums by artist |
| GET | `/api/v1/albums/` | Paginated album list |
| GET | `/api/v1/albums/<mbid>/` | Album detail |
| GET | `/api/v1/albums/<mbid>/art/` | Redirects to Cover Art Archive for cover art |
| GET | `/api/v1/genres/` | All genre labels in both Rosamerica and Dortmund systems |
| GET | `/api/v1/search/` | Search by `q` and `type` (`track`/`artist`/`album`) |

### Recommendation Endpoint
| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/recommend/` | Get similar tracks for a given MBID |

**POST `/api/v1/recommend/` request body:**
```json
{
  "mbid": "<recording-mbid>",
  "listened_mbids": ["<mbid>", ...],
  "filters": {
    "exclude_artists": ["<artist-mbid>"],
    "same_genre": true,
    "same_decade": true,
    "genre_classification": "rosamerica"
  },
  "feature_weights": {
    "danceability": 0.5,
    "aggressiveness": 0.5,
    ...
  },
  "total_weights": {
    "similarity": 0.7,
    "popularity": 0.3
  },
  "limit": 10
}
```

**Response:**
```json
{
  "target_track": { "mbid": "...", "title": "..." },
  "similar_list": [{ "mbid": "...", "title": "...", "similarity": 0.93, ... }],
  "stats": {
    "candidate_count": 79448,
    "search_time": 0.008,
    "mean": 0.40,
    "std": 0.32,
    "p95": 0.81,
    "max": 0.99
  }
}
```

All list responses follow the DRF pagination shape: `{ count, next, previous, results }`.

All error responses follow the shape: `{ "error": { "code": "...", "message": "..." } }`.

All resource objects include a `links` field (HATEOAS) with URLs to related endpoints.

---

## Dataset

**Source:** [AcousticBrainz](https://acousticbrainz.org/download) – a community-driven open dataset of pre-extracted audio features for millions of tracks, keyed by MusicBrainz IDs.

- **Sample dataset:** ~100k tracks (good for development). After deduplication: ~85k unique tracks.
- **Full dataset:** ~30M tracks across multiple `.tar.zst` archive files.

### Ingest Pipeline (`python manage.py build_db`)
1. Stream JSON from `.tar.zst` archives in parallel (`ThreadPoolExecutor`).
2. Extract title, audio features, artist, album, and genre from each JSON file.
3. Deduplicate tracks by MBID: for duplicates, select the **most common value** for each field.
4. Build Django models: `Track`, `Artist`, `Album`, `AlbumArtist`, `TrackArtist`.
5. Export audio features to `features_and_index.npz` (NumPy compressed array file).

The `features_and_index.npz` file is **not stored in the repository** and must be built locally or copied to the server before deployment.

---

## Frontend UI

The React SPA consists of a single-page layout:

1. **Header** – app name/logo and a search bar.
2. **Main content area** – shows either:
   - "Top tracks" (default, ordered by `submissions` descending), or
   - Search results when the user types a query.
3. **Player (bottom drawer)** – slides up from the bottom when a track is selected:
   - **Footer bar** (always visible when a track is loaded): cover art, track title, artist, album, play/pause, next track, maximize/minimize buttons.
   - **Maximized overlay** (full-screen): contains:
     - **Recommendation Settings panel** (Filters component) with genre/decade toggles, ranking balance sliders, and per-feature weight sliders.
     - **YouTube iframe player.**
     - **Stats panel** showing candidate count, similarity scores, search time, listened count.
     - **"Up Next"** (first recommendation) and **"Other Recommendations"** list.

Auto-advance: when a YouTube video ends, the first recommendation is automatically played.

---

## Deployment

Production uses a **two-container Docker Compose** setup:
- `taste-mender-postgres` – PostgreSQL 18 (Alpine), data persisted in a named volume.
- `taste-mender-web` – Python 3.14 slim image with Django + Gunicorn, serving on port 8000.

Nginx runs directly on the host, acts as the HTTPS-terminating reverse proxy, and forwards all traffic to the Django container.

### Required Environment Variables (backend/.env)
- `DJANGO_SECRET_KEY` – Django secret key
- `DJANGO_ALLOWED_HOSTS` – comma-separated allowed hostnames
- `DATABASE_URL` – PostgreSQL connection URL
- `POSTGRES_USER` / `POSTGRES_PASSWORD` – Postgres credentials (used by both services)
- `YOUTUBE_API_KEY` – YouTube Data API v3 key (for `/sources/` endpoint)
- `AB_HIGHLEVEL_ROOT` / `AB_SAMPLE_ROOT` – paths to AcousticBrainz dump files (only needed for ingest)

---

## Testing

```bash
# Run Django unit tests
cd backend/
python manage.py test
```

Coverage is tracked via `codecov`. Test utilities use `factory_boy` and `Faker` for model factories.

---

## Known Limitations & Planned Work

- The AcousticBrainz project is no longer actively maintained, so the dataset is frozen at its June 2022 dump.
- CORS is configured but rate limiting is not yet implemented.
- The `/api/v1/artists/<mbid>/similar-artists/` endpoint is designed but not yet implemented.
- The full recommendation UI (auto-playing queue, filter tuning) exists but the feature could be expanded further (e.g., a "dislike" mechanism that excludes an artist from future recommendations in a session).
- Cover art falls back to a text initial when no CAA image is available; Discogs or YouTube thumbnails could serve as additional fallbacks.
- Feature weights submitted by the user are not normalized server-side; weights are applied as raw multipliers.
- Caching headers (`ETag`, `Cache-Control`) for static API resources are not yet implemented.

---

## Conventions

- All resource identifiers throughout the codebase are referred to as **MBID** (MusicBrainz ID), regardless of whether they identify a track, artist, or album.
- API responses use `mbid` as the field name (not `musicbrainz_recordingid` etc.) — the serializer maps the internal DB field name to the shorter `mbid`.
- The frontend is a pure SPA with no routing library; all state is managed in React component state and context.
- The feature matrix file path is resolved relative to the `recommender.py` source file, not the Django project root.
