# Benchmark for skipping merge logic for tracks with 1 submission

## Notes

The pipeline prints missing data logs in the console, this should be fixed
`Missing data in JSON string (missing musicbrainz_recordingid), path: 'acousticbrainz-highlevel-json-20220623\highlevel\3f\4\3f4adb1a-bd28-4b25-bff3-72ca7ce638db-1.json'`

Let's find a way to make the logging strategy of the app more consistent.
- In general the app should log with `simple` formatter, `console` handler and `recommend_api` logger. This works ok.
- For startup it should only show the message, not line or file, also works ok

The problem I have is in the ingest area:
- The core pipeline should not show logs in the console but can still emit them in the log file
- The enrichments should show logs in the console but the should include levelname and the message

What can I do?

## Results

All runs used `python manage.py build_db --parts 1`.

| Timing (seconds) | Old, uncached | Old, cached | New, cached |
| --- | ---: | ---: | ---: |
| Load track data | 133.65 | 0.01 | 0.00 |
| Merge tracks | 82.46 | 85.51 | 38.17 |
| Build track models | 21.04 | 21.26 | 21.02 |
| Insert artists and albums | 4.08 | 4.04 | 3.77 |
| Insert tracks, including search vectors | 125.57 | 124.23 | 123.07 |
| Insert relationships | 31.94 | 32.98 | 32.79 |
| Export feature matrix | 6.22 | 6.25 | 6.19 |

The cached merge time decreased by 47.34 seconds (55%, or 2.24x faster).
Each result represents one run.

All runs processed 700,528 track IDs, dropped 31,920 without artists, and
inserted 668,608 tracks, including 27,791 with year 0. Each created 681,403
track-artist and 134,433 album-artist links.

The uncached run reported 298,870 duplicate submissions, 33,131 invalid dates,
and 602 submissions with missing data (601 invalid MBIDs and one missing title).
Cached runs reported zero for these counters because they did not reprocess the
source files.