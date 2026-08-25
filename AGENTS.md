# TasteMender – Agent Operating Instructions

> **Source-of-truth precedence (highest → lowest)**
>
> 1. Current code and database migrations (`backend/`)
> 2. Tests and auto-generated OpenAPI schema (`backend/recommend_api/tests/`, `/api/v1/schema/`)
> 3. Architecture documentation (`docs/PROJECT_CONTEXT.md`)
> 4. Summaries in this file
> 5. Historical university reports and older chats
>
> When this file conflicts with the code, trust the code. Verify behavioural details
> (algorithm steps, field names, response shapes) against the implementation before
> acting on them.

---

## What Is TasteMender?

A **music discovery web app** that recommends songs by acoustic similarity (danceability,
energy, mood, genre) rather than listening history or collaborative filtering.

- **Live URL:** https://taste-mender.com/
- **Stack:** Django 5.2 + DRF · PostgreSQL 18 · React 19 + TypeScript · Docker

For the full architecture, data models, API reference, and algorithm details see
**[`docs/PROJECT_CONTEXT.md`](docs/PROJECT_CONTEXT.md)**.

For planned work and goals first check [GitHub issues](https://github.com/RadValentin/taste-mender/issues) then **[`docs/ROADMAP.md`](docs/ROADMAP.md)**.

---

## Quick Commands

```bash
# Backend – run from backend/
pip install -r requirements.txt
python manage.py migrate
python manage.py test          # unit tests (uses factory_boy + Faker)
python manage.py runserver     # dev server on :8000

# Ingest (requires AcousticBrainz dumps, see README.md)
python manage.py build_db --sample   # ~85k tracks for dev

# Frontend – run from frontend/
npm install
npm run dev    # Vite dev server
npm run build  # production build (output goes to frontend/dist/, served by WhiteNoise)

# Docker (production-like)
cd backend/
docker-compose up -d --build
docker-compose exec django python manage.py migrate
```

---

## Key Conventions

- All resource identifiers are called **MBID** (MusicBrainz ID) everywhere in the codebase,
  regardless of whether they identify a track, artist, or album.
- API responses expose `mbid` (not the raw DB column name `musicbrainz_recordingid`);
  the serializer performs the mapping.
- All state lives in React component state and context for now.
- The feature matrix (`features_and_index.npz`) is resolved relative to `recommender.py`,
  not the Django project root. It is **not** committed to the repository.
- Error responses follow `{ "error": { "code": "...", "message": "..." } }`.
- List responses follow the DRF pagination shape `{ count, next, previous, results }`.
- All resource objects include a `links` field (HATEOAS) with URLs to related endpoints.
- Collections can also include a `links` field to tell the client exactly what sub-collections, filters, or specific actions are available without requiring them to read hardcoded external documentation.
- Project decisions:
  - [`ADR-001`](docs/DECISIONS/ADR-001-in-memory-feature-matrix.md): In-memory feature matrix.
  - [`ADR-002`](docs/DECISIONS/ADR-002-cache-analysis-targets-production.md): Production-first
    cache analysis.
