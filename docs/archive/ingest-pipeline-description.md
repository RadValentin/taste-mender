### Dataset Ingest

Track data is loaded from the [DB dumps](https://acousticbrainz.org/download) of the AcousticBrainz dataset. The build pipeline does the following:

1. Stream JSON data from `.tar.zst` archives, processing the archives in parallel
1. Extract relevant information from each file (title, audio features, metadata), discarding those that have missing or invalid data
1. Build a hashmap (`track_index`) of duplicate tracks indexed by their MusicBrainz ID (`musicbrainz_recordingid`)
1. Merge duplicates into a single entry by selecting the most common value for each field (title, audio features, metadata)
1. Build the DB models:
  1. `Track` from `track_index`
  1. `Artist`, `Album` and M2M pairings (`AlbumArtist`, `TrackArtist`) from the track metadata
1. Extract audio features to a separate file (`features_and_index.npz`), this will be loaded into memory by the Django app to allow for fast searching

Because many popular tracks are duplicated in the dataset, the final number of tracks that the app will be working with is considerably lower than what was ingested.

$$finalSize = datasetSize - duplicateCount - tracksMissingData - tracksMissingArtist$$

For the sample dataset (100k tracks), 85732 unique entries will be loaded:
$$85732 = 100000 - 11182 - 4 - 3082$$