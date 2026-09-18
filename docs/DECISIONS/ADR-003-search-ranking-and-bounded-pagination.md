# ADR-003: Hybrid ranked search with bounded offset pagination

**Date:** 2026-09-18
**Status:** Accepted

---

## Context

Taste Mender searches millions of tracks in PostgreSQL. Search must balance relevance, typo tolerance, artist-name matching, and popularity while keeping the initial response fast.

Search is a discovery feature: users should find a useful result near the start of the ranked set. Exhaustive traversal and an exact total are not requirements. Earlier implementations that returned or counted a large result set increased initial latency; the evaluated full-pagination approach approximately doubled it.

## Decision

### Ranking

Track search uses PostgreSQL full-text search (FTS) over a materialized vector containing weighted track-title and artist-name terms. Results are ranked using textual relevance and AcousticBrainz submission count as a popularity proxy:

```text
combined_rank =
    0.4 * full_text_search_rank
    + 0.6 * ln(submissions + 1)
```

Trigram matches not already found by FTS are appended as a fallback for misspellings and partial titles. Single-word queries use trigram word distance; multi-word queries use regular trigram distance.

Artist and album searches use trigram matching without a popularity signal. All rankings use the primary key as a deterministic tie-breaker.

Search depends on PostgreSQL GIN and GiST indexes. Tracks store denormalized artist text and a materialized search vector so the searchable document is not rebuilt per request.

### Pagination

Search uses offset pagination with:

- `limit`, defaulting to 100;
- `offset`, defaulting to 0; and
- a maximum searchable window of 500 results.

The endpoint requests `limit + 1` results. The extra result is removed and used to calculate `has_more`, avoiding a separate total-count query.

The response uses a custom envelope:

```json
{
  "query": "search terms",
  "type": "track",
  "response_time": 0.123,
  "count": 100,
  "results": [],
  "has_more": true
}
```

`count` is the number of returned results, not the total number of matches. This is an intentional exception to the standard DRF list envelope containing `count`, `next`, `previous`, and `results`.

For track searches, ranked FTS and trigram IDs are merged before applying the offset. Only the selected page is then hydrated with its related artists and albums.

## Consequences

### Benefits

- No total-count query is required.
- The initial response contains only the records needed by the UI.
- Search supports semantic token matching, artist names, misspellings, partial titles, and popularity.
- `has_more` directly supports the frontend's load-more interaction.
- The 500-result cap bounds the cost of increasingly deep offsets.
- Deterministic tie-breaking makes adjacent pages stable for a mostly immutable dataset.

### Trade-offs

- Later pages are slower because a larger ranked prefix must be recalculated.
- Matches beyond the first 500 results are inaccessible.
- Consumers cannot show an exact total and need a search-specific pagination adapter.
- Denormalized search fields must remain synchronized with source data.
- Submission count is an imperfect, dataset-specific popularity proxy.
- Text rank and popularity are not normalized to the same scale, so the current weights are empirical and popularity may dominate some queries.
- Results may shift between requests if searchable data or submission counts change.

## Alternatives Considered

- **Standard DRF pagination with total counts:** rejected because counting ranked matches increased initial latency without helping the load-more UI.
- **Return 500 results for client-side pagination:** rejected because it increases initial query, serialization, transfer, and rendering costs.
- **FTS only:** rejected because it does not adequately handle misspellings and partial titles.
- **Trigram only:** rejected for tracks because it handles token relevance and artist-name matching less effectively.
- **Cursor pagination:** deferred because a reliable cursor across merged FTS and trigram rankings with computed scores would add substantial complexity.
- **Dedicated search service:** deferred because its operational cost is not justified while PostgreSQL provides adequate performance.

Revisit this decision if users need deeper traversal, exact totals or facets, later-page latency becomes unacceptable, or relevance testing shows that the ranking weights perform poorly.
