# TasteMender – Copilot Agent Instructions

## Project Overview

TasteMender is a music recommendation web app with two parts:

- **Backend** (`backend/`): Django 5.2 REST API (Python 3.13.13) backed by PostgreSQL 17. Uses `scikit-learn` cosine similarity on a NumPy feature matrix loaded from `features_and_index.npz` to find similar tracks. Audio features come from the [AcousticBrainz](https://acousticbrainz.org/download) dataset.
- **Frontend** (`frontend/`): React 19 + TypeScript SPA built with Vite. It is served statically by the Django backend via WhiteNoise.

All track/artist/album identifiers are [MusicBrainz UUIDs](https://musicbrainz.org/doc/MusicBrainz_Identifier) (referred to as "MBIDs" throughout the codebase).

---

## Repository Structure

```
backend/
  music_recommendation/   # Django project (settings, urls, wsgi, asgi)
  recommend_api/          # Main Django app
    api/                  # API endpoint views (one file per resource)
    migrations/           # Django DB migrations
    services/
      recommender.py      # Cosine-similarity recommendation logic + FeatureStore singleton
      youtube_sources.py  # YouTube Data API v3 source lookup
    tests/
      api/                # APITestCase tests for each endpoint
      services/           # Unit tests for services
      factories.py        # factory_boy model factories
    models.py             # Track, Artist, Album, GenreDortmund, GenreRosamerica, …
    serializers.py        # DRF serializers (request + response)
    router.py             # Custom DRF router with HATEOAS root view
    urls.py               # URL routing
    views.py              # SPAView (serves frontend/dist/index.html)
  ingest/                 # Dataset ingestion scripts
    management/commands/
      build_db.py         # `python manage.py build_db` – builds DB + features_and_index.npz
      recommend.py        # CLI helper for checking recommendations
    pipeline.py           # Core ingestion pipeline (excluded from coverage)
    lmdb_index.py         # LMDB-backed track deduplication index
  manage.py
  requirements.txt        # Production + dev dependencies
  requirements-test.txt   # Test-only dependencies (lighter subset)
  .env.example            # Template for required environment variables
  .coveragerc             # Coverage config (min 80%, branch coverage)
  Dockerfile              # Docker image for production
  docker-compose.yml      # Production deployment (Django + PostgreSQL containers)

frontend/
  src/
    App.tsx               # Root component
    api.ts                # Axios API client
    types.ts              # TypeScript types
    components/           # React components (Player, TrackList, Header, …)
    PlayerContext.tsx      # React context for playback state
    PlayerProvider.tsx
  package.json
  vite.config.ts
  eslint.config.js
  tsconfig.app.json

docs/
  api-design.md           # Endpoint checklist and design notes
  requirements.md
  progress-log.md
  postgres-optimization.md
```

---

## Key Architecture Notes

### Feature Matrix (`features_and_index.npz`)
- **Not committed to git.** Required for `/api/v1/recommend/` and `/api/v1/tracks/<mbid>/features/` endpoints.
- Loaded once as a singleton (`FeatureStore` in `recommend_api/services/recommender.py`) using `mmap_mode="r"` for efficiency.
- Contains: `feature_matrix`, `feature_matrix_raw` (debug only), `feature_names`, `mbids` (V16 UUID bytes), `years`, `genre_dortmund`, `genre_rosamerica`.
- If the file is missing at startup, the service logs a warning and raises `FileNotFoundError` on the first recommendation request (returns HTTP 503).
- Tests **mock** `rec.recommend` via `unittest.mock.patch`; they do NOT need the `.npz` file.

### Database
- PostgreSQL 17 with the `pg_trgm` extension (required for `GinIndex`/`GistIndex` trigram search on track/artist/album names).
- Full-text search uses Django's `SearchVectorField` (populated during ingest and updated via `update search_vector` on track create).
- The `search_vector` field on `Track` combines `title` (weight A) + `artists_text` (weight B).

### URL Structure
- `/api/v1/` – DRF router root (tracks, albums, artists)
- `/api/v1/genres/` – genre list
- `/api/v1/recommend/` – POST, main recommendation endpoint
- `/api/v1/search/` – GET, search tracks/artists/albums
- `/api/v1/tracks/<mbid>/features/` – audio feature values for a track
- `/api/v1/tracks/<mbid>/sources/` – YouTube source lookup
- `/api/v1/albums/<mbid>/art/` – Cover Art Archive proxy
- `/api/v1/schema/`, `/api/v1/swagger-ui/`, `/api/v1/redoc/` – OpenAPI docs
- Everything else → React SPA (`frontend/dist/index.html`)

### Serializers
- Every serializer field that represents a MusicBrainz ID is named `mbid` in the API response (source fields like `musicbrainz_recordingid` are mapped with `source=`).
- Response serializers are named `*ResponseSerializer`; request serializers are named `*RequestSerializer`.
- `SimilarTrackSerializer` extends `TrackSerializer` with an added `similarity: float` field (attached to the model instance at runtime, not a DB field).

---

## Environment Variables

See `backend/.env.example` for the full list. Key variables:

| Variable | Required for tests? | Notes |
|---|---|---|
| `DATABASE_URL` | Yes | `postgres://user:pass@host:port/db` |
| `DJANGO_SECRET_KEY` | Yes | Any string works in tests |
| `YOUTUBE_API_KEY` | No | Skipped when `"test" in sys.argv` |
| `DJANGO_DEBUG` | No | Defaults to `"False"` |
| `DJANGO_ALLOWED_HOSTS` | No | Defaults to `"localhost"` |
| `AB_HIGHLEVEL_ROOT` | No | Only for dataset ingest (`build_db`) |
| `AB_SAMPLE_ROOT` | No | Only for dataset ingest (`build_db`) |

Settings prefers real environment variables over `.env` file values (`os.getenv` first, then `dotenv_values`).

---

## Running the Backend

```bash
cd backend/

# Install dependencies
pip install -r requirements-test.txt   # for tests
pip install -r requirements.txt         # for full dev/prod

# Apply migrations
python manage.py migrate

# Run the development server (needs DATABASE_URL, DJANGO_SECRET_KEY, YOUTUBE_API_KEY)
python manage.py runserver
```

### Running Tests

```bash
cd backend/

# Run tests with coverage (minimum 80% required)
coverage run manage.py test
coverage report

# Run a specific test module
python manage.py test recommend_api.tests.api.test_recommend_api
```

**CI environment variables** (set in `.github/workflows/django.yml`):
```
DATABASE_URL=postgres://postgres:postgres@127.0.0.1:5432/taste_mender_db
DJANGO_SECRET_KEY=unit-tests
DJANGO_DEBUG=True
```

CI uses a `postgres:17` service container. The `django` user must have `CREATEDB` permission for Django's test DB creation.

---

## Running the Frontend

```bash
cd frontend/

npm install
npm run dev      # Vite dev server on http://localhost:5173
npm run build    # tsc + vite build → frontend/dist/
npm run lint     # ESLint
```

In production, `frontend/dist/` is served by Django via WhiteNoise (`STATICFILES_DIRS = [BASE_DIR.parent / "frontend" / "dist"]`).

---

## Testing Conventions

- All backend tests live under `backend/recommend_api/tests/` (and `backend/ingest/tests/`).
- Use `django.test.TestCase` for DB tests and `rest_framework.test.APITestCase` for API endpoint tests.
- Use `factory_boy` (`DjangoModelFactory`) for creating test data. Factories are in `recommend_api/tests/factories.py`.
- Prefer `setUpTestData` for immutable shared fixtures; use `setUp` for per-test state or mocks.
- Mock external services (recommender, YouTube) with `unittest.mock.patch`. The `recommend_api.services.recommender.STORE` singleton and `rec.recommend` function are the typical patch targets.
- Always call `Factory.reset_sequence(0)` in `tearDownClass` after using sequences.
- Coverage is measured on `recommend_api` and `ingest` packages; `ingest/pipeline.py` is excluded.
- **Coverage must stay above 80%** (`fail_under = 80` in `.coveragerc`). Falling below will fail CI.

### Adding a New API Endpoint

1. Add model/migration if needed.
2. Add serializer(s) to `recommend_api/serializers.py`.
3. Add view to the appropriate file in `recommend_api/api/` (or create a new file).
4. Register in `recommend_api/urls.py` (router or explicit `path()`).
5. Add tests in `recommend_api/tests/api/`.
6. Decorate views with `@extend_schema(...)` from `drf_spectacular` for OpenAPI docs.

---

## Migrations

```bash
cd backend/
python manage.py makemigrations
python manage.py migrate
```

Migrations live in `backend/recommend_api/migrations/`. Always commit migration files.

---

## Docker / Production

The backend is packaged with `backend/Dockerfile` and `backend/docker-compose.yml`. The compose file starts two containers: `taste-mender-web` (Django + Gunicorn) and `taste-mender-postgres`.

```bash
cd backend/
docker-compose up -d --build
docker-compose exec django python manage.py migrate
```

---

## Common Errors and Workarounds

### `ValueError: Missing required environment variables: YOUTUBE_API_KEY`
Occurs when running the server (not tests) without setting `YOUTUBE_API_KEY`. Set it in `backend/.env` or as an environment variable. This check is skipped when `"test"` is in `sys.argv`.

### `FileNotFoundError` on recommendation requests
The `features_and_index.npz` file is missing. Build it with `python manage.py build_db --sample` (requires AcousticBrainz dataset dumps and `AB_SAMPLE_ROOT` env var). Tests mock around this; only the live server needs the file.

### `pg_trgm` extension missing
Required for trigram indexes on `Artist.name`, `Album.name`, and `Track.title`. Enable in PostgreSQL:
```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```
Django migrations attempt to create `GinIndex`/`GistIndex` with `gin_trgm_ops` / `gist_trgm_ops`, which will fail without this extension.

### `FeatureStore already initialized with … cannot reinitialize`
The `FeatureStore` singleton enforces a single path. This error means the module was imported from two different paths. Ensure consistent imports from `recommend_api.services.recommender`.

### Frontend not found (HTTP 404 on `/`)
Run `npm run build` in `frontend/` to produce `frontend/dist/index.html` before starting the Django server. In development, the Vite dev server (`npm run dev`) on port 5173 handles the frontend directly.

---

## Code Style

- Python: no enforced linter/formatter beyond Django conventions. Type hints are used throughout the services layer.
- TypeScript: ESLint with `typescript-eslint` and `eslint-plugin-react-hooks`/`eslint-plugin-react-refresh`.
- Imports in Python API files typically use `from recommend_api.models import *` and `from recommend_api.serializers import *` (star imports are conventional in this project).
