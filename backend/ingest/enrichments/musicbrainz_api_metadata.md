# Match Tracks to playable videos
We have a database with `Track` data and we need a way to match the tracks to playable YouTube videos (`TrackSource`). Right now this is done lazily, when users try to play a track in the app. However, we're limited by the YT Data API to only 100 searches per day so it's highly likely we'll be rate-limited with any real traffic.

We need to implement a way of decreasing the likeliness of hitting YT API daily quotas. Our `Tracks` are the subset/counterpart of MusicBrains' `Recording`, both identified by MBIDs. Recordings can have one or more ISRC codes, multiple recordings can have the same ISRC, only one ISRC needs be matched to a source. Searching for a song by ISRC on Youtube will return the official playable video, this is more accurate than searching by title + artist. The plan is to gather the data in multiple phases:
- Match tracks to their ISRCs (if available) and ingest into the DB as an enrichment
- Match tracks to sources by searching YT by ISRC with fallback to title + artist and ingest into the DB as an enrichment

## Phase 1 - Enrich Track model with MusicBrainz metadata
Define a JSON schema for enriching Track model, should include:
  - Date when enrichment was first ran
  - Date when enrichment was last ran
  - A dictionary of track data indexed by MBID
    - Each object should contain metadata retrieved from MusicBrainz
    - Objects can be null if MB returned no data (but not on error), so we know which tracks were already checked
    - Store a timestamp with the objects for when the data was retrieved

A JSON file matching the schema will be produced by the following implementation:
- Filter tracks in the DB to ones that: haven't been checked, have no MB metadata fields populated (ISRC)
- Sort tracks by number of submissions, we'll check only the most popular ones, limit to 1000 tracks
- Retrieve metadata from MusicBrainz by each track MBID, with a sensible timeout to not overload the API (1s)
  - On API outage/rate limit errors, retry 5 times with progressively increasing timeouts before giving up
  - Include `User-Agent` header
  - Empty responses don't count as errors
- Update JSON with each track's new metadata
- Ensure that if script is ran again, it will continue checking only tracks that weren't checked previously
- Script should produce a log with: how many tracks had ISRCs in this run / in all runs

Lastly, define a method for loading the JSON into the database.

## Phase 2 - Search YouTube for videos based on MBID
Define a JSON schema for enriching the `TrackSource` model, should include:
  - Date when enrichment was first ran
  - Date when enrichment was last ran
  - A dictionary of source data
    - keys are in 2 forms `isrc:<code>` when source was searched by ISRC, `track:<mbid>` when source was searched by MBID.
    - Objects can be null if MB returned no data (but not on error), so we know which tracks were already checked
    - Store YT metadata (incl. video ID), query, timestamp, error state

- Sort tracks by number of submissions, we'll check only the most popular ones, limit to 100 tracks according to YT API daily quota
- For each track
  - if it's ISRC is already matched to a video, skip. Otherwise, search YT by ISRC
  - if ISRC isn't present, search by title + artist
- Update JSON with the new source
- Ensure that if script is ran again, it will continue checking only tracks that weren't checked previously
- Define a method for loading the JSON into the database

> [!NOTE]
> Assume some `Tracks` have ISRC codes now but not all

## Links

- https://musicbrainz.org/doc/MusicBrainz_API
- https://musicbrainz.org/doc/MusicBrainz_API/Rate_Limiting
