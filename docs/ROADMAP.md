# TasteMender – Roadmap

This document captures known limitations, planned features, and deliberate non-goals.
Update it as priorities shift; don't let it go stale.

---

## Known Limitations

- **Frozen dataset.** The AcousticBrainz project is no longer actively maintained; the
  dataset is frozen at the June 2022 dump. New tracks cannot be added without an
  alternative feature-extraction source.
- **No rate limiting.** CORS is configured but the API has no rate limiting.
- **Feature weights are not normalized server-side.** Weights submitted by the user are
  applied as raw multipliers, so a user who sets all weights to 1.0 gets the same result
  as all 0.5 — but weights of varying magnitudes will skew similarity toward higher-weight
  features non-linearly.
- **Cover art fallback is limited.** When no Cover Art Archive image is available, the UI
  falls back to a text initial. Discogs or YouTube thumbnails could serve as additional
  fallbacks.
- **No caching headers.** `ETag` and `Cache-Control` headers for static API resources are
  not yet implemented.
- **Single-artist deduplication is greedy.** The post-filter allows only one track per
  artist, which can push diverse but popular artists off the recommendation list if they
  appear many times in the top-k candidates.

---

## Near-term Priorities

- [ ] **Rate limiting** – add per-IP rate limiting to the API (e.g., via
  `django-ratelimit` or Nginx `limit_req`).
- [ ] **`/similar-artists/` endpoint** – the
  `/api/v1/artists/<mbid>/similar-artists/` endpoint is designed (see
  `docs/api-design.md`) but not yet implemented.
- [ ] **Cover art fallback chain** – try Discogs or YouTube thumbnail when CAA returns no
  image.
- [ ] **Normalize feature weights server-side** – divide each weight by the sum of all
  weights before applying, so the scale of user input doesn't affect results.

---

## Medium-term Ideas

- [ ] **"Dislike" / exclude-artist mechanism** – let users exclude an artist from the
  current session's recommendations without modifying global filters.
- [ ] **Caching headers** – add `ETag` / `Cache-Control` to read-only API responses to
  reduce redundant traffic.
- [ ] **Alternative audio-feature source** – explore AcousticBrainz successor projects
  or self-hosted Essentia pipelines to support new tracks.
- [ ] **Playlist export** – allow users to export their "listened" queue to a Spotify or
  YouTube Music playlist.
- [ ] **Persistent sessions** – store filter preferences and listened history in
  `localStorage` so settings survive a page refresh.

---

## Non-goals

- **User accounts / authentication** – TasteMender is intentionally stateless and
  anonymous; there are no plans to add login, user profiles, or server-side history.
- **Collaborative filtering** – the recommendation model is purely audio-feature-based.
  Social or listening-history signals are outside scope.
- **Real-time audio analysis** – ingesting arbitrary user-supplied audio files for
  feature extraction is not planned.
