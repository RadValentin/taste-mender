# Core ingest

This package owns the required AcousticBrainz build:

- relational track, artist, album, and genre data
- relationship tables
- the recommendation feature matrix

The existing pipeline remains the implementation entry point for now. Future
refactoring can move core-specific code here incrementally.