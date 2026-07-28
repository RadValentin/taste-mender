# TasteMender – Roadmap

This roadmap provides a high-level view of TasteMender’s current constraints, near-term priorities, and long-term direction. It is intended to guide product and engineering decisions without locking the project into a rigid plan.

Work is prioritized by GitHub issues. Issues labelled ["future work"](https://github.com/RadValentin/taste-mender/issues?q=is%3Aissue%20state%3Aopen%20label%3A%22future%20work%22) represent long-term goals, while the rest are mid-term.

---

## Known Limitations

- **Frozen dataset.** The AcousticBrainz project is no longer actively maintained; the
  dataset is frozen at the June 2022 dump. New tracks cannot be added without an
  alternative feature-extraction source.
- **No rate limiting.** CORS is configured but the API has no rate limiting.
- **No caching headers.** `ETag` and `Cache-Control` headers for static API resources are
  not yet implemented.
- **Stateless by design.** The API is deliberately kept stateless, which limits richer
  front-end interactions such as preserving state across page refreshes, moving listening
  sessions between devices, or keeping playback history.
- **Messy / unverified data.** The project merges duplicates and relies on crowdsourced
  data, so correctness cannot be guaranteed. An artist may be matched to the wrong song.

---

## Near-term Priorities

- [ ] **Expand the UI** – grow the front-end to match the complexity of other music services by adding richer views and routes for artists, albums, similar artists, and related content.
- [ ] **Improve mobile responsiveness** – make the app work well across screen sizes, including exploring compact ways to present the large set of filters without overwhelming the interface.
- [ ] **Develop a social strategy** – explore lightweight distribution channels such as an automated account that posts daily picks or other recurring recommendations.
- [ ] **Caching headers** – add `ETag` / `Cache-Control` to read-only API responses to
  reduce redundant traffic.

---

## Medium-term Ideas

- [ ] **"Dislike" / exclude-artist mechanism** – let users exclude an artist from the
  current session's recommendations without modifying global filters.
- [ ] **Alternative audio-feature source** – explore ways to match tracks to other audio services, e.g. Spotify, Deezer.
- [ ] **Playlist export** – allow users to export their "listened" queue to a Spotify or
  YouTube Music playlist.
- [ ] **Persistent sessions** – store filter preferences and listened history in
  `localStorage` so settings survive a page refresh.
- [ ] **Stateful companion API** – add a separate API for persisted user state such as
  preferences, listening sessions, and playback history while keeping the core
  recommendation API stateless.
- [ ] **Official metadata source** – improve correctness by sourcing track and artist data
  from MusicBrainz via MBID matching instead of the current approach.

## Long-term Ideas

- [ ] **Rich metadata relationships** – explore ways of representing richer relationships between entities so recommendations can reflect cultural or contextual associations, such as a song appearing on a video game soundtrack. This could support requests like early 2000s racing game soundtracks or symphonic music from 70s sci-fi.

---

## Non-goals

- **User data influencing recommendations** – the recommendation model is purely audio-feature-based. Social or listening-history signals are outside scope. The core API is purposefully kept stateless.
- **Real-time audio analysis** – ingesting arbitrary user-supplied audio files for feature extraction is not planned. This project does not aim to become AcousticBrainz 2.0 .
