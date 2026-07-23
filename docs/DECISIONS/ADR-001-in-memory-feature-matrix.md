# ADR-001: In-memory NumPy feature matrix for recommendations

**Date:** 2025  
**Status:** Accepted

---

## Context

The recommendation engine must compare a seed track's audio-feature vector against every
candidate in the dataset (up to ~85k tracks for the sample dataset, potentially millions
for the full dataset). The two main options considered were:

1. **Store feature vectors in PostgreSQL** (e.g., `pgvector` or a `float[]` column) and
   compute similarity with a SQL query.
2. **Load all feature vectors into RAM as a NumPy array** at process startup and compute
   cosine similarity in Python using scikit-learn.

## Decision

Option 2 — in-memory NumPy matrix — was chosen.

The feature matrix is stored as a compressed NumPy `.npz` file
(`features_and_index.npz`) and loaded once at Django startup via a singleton
`FeatureStore` class. All read-only arrays are `mmap`-backed and flagged non-writable.
Cosine similarity is computed with
`sklearn.metrics.pairwise.cosine_similarity` against the entire (or pre-filtered) matrix.

## Rationale

- **Speed.** For 85k tracks × 16 features, the full cosine similarity pass takes under
  10 ms in RAM. A PostgreSQL `pgvector` scan over the same data would be measurably
  slower and would add round-trip latency.
- **Simplicity.** NumPy + scikit-learn are already in the stack for other reasons; no
  additional PostgreSQL extension is needed.
- **Controlled memory footprint.** An 85k × 16 `float32` matrix is ~5 MB — negligible
  on a modern VPS. Even the full 30M-track dataset would be manageable (~2 GB) on a
  memory-optimised instance.
- **Immutability.** The dataset is frozen (AcousticBrainz, June 2022 dump), so
  the matrix never needs to be updated at runtime.

## Consequences

- The `.npz` file must be built during ingest and copied to the server before deployment;
  it is not stored in the repository.
- The file path is resolved relative to `recommender.py`, not the Django project root.
- Adding new tracks requires re-running ingest and redeploying the `.npz` file.
- If the server runs multiple Gunicorn workers, each worker loads its own copy of the
  matrix. Memory usage scales linearly with worker count.

## Alternatives Considered

- **pgvector** – would eliminate the out-of-band `.npz` file but adds a PostgreSQL
  extension dependency and complicates the deployment. Revisit if the dataset grows
  beyond what fits comfortably in RAM.
- **FAISS / Annoy** – approximate nearest-neighbour libraries would be faster at very
  large scale (millions of tracks) but add complexity and approximate results.
  Not needed for the current dataset size.
