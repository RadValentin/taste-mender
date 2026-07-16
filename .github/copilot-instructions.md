# TasteMender – Copilot Agent Instructions

## Project Summary

TasteMender is a music recommendation web app with two parts:
- (`backend/`) A stateless Django REST API backed by PostgreSQL database
- (`frontend/`) A React + TypeScript SPA bundled with Vite and served statically by the backend via WhiteNoise.

All track/artist/album identifiers are [MusicBrainz UUIDs](https://musicbrainz.org/doc/MusicBrainz_Identifier) (referred to as "MBIDs" throughout the codebase).

The database is generally stable as it's derived from the [AcousticBrainz dataset](https://acousticbrainz.org/) which crowdsourced acoustic information about music recordings between 2015-2022. For the most part it can be considered read-only outside of analytics.


## Project Scope and Goals

### Big picture

- TasteMender started out as a final project for university the got spun out into a web app.
- All development is done by a single person, the original creator.
- The goal is to create a novel music discovery application that is of good enough quality to be useful and enjoyable for real-world users and that showcases the developer's skill set.


### Development mantra

- Keep things lean and prioritise iteration
  - Development should prioritise iteration speed while adhering to basic industry standards: unit tests and coverage, PRs and code reviews (AI) for major changes, decent architecture design, etc.
  - The code doesn't need to be perfect, it doesn't need to follow every best practice, no need to get overly concerned about minor detail, there needs to be as little scaffolding as possible, minimal dependencies
- Deliver a great experience for the user
  - Any polish that's to be done should benefit the user experience. Some measure of leanness can be sacrificed if it greatly benefits the end user.


## Review Guidelines

### Skip Low-Value Feedback

In general do NOT comment or suggest fixes for low-priority or low-value issues.

Do not comment on these unless they cause an error:
- Import order, unused imports
- Style or formatting


### Testing

When reviewing make sure to keep an eye on the following aspects:
- Missing tests for changed behavior
- Potential regressions
- Edge-case handling
- Migration/data-risk when backend logic changes