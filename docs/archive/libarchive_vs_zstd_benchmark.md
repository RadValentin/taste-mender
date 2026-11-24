# Archive access benchmark

Compare archive loading with the original Zstandard + `tarfile` reader and the
new `libarchive` reader. The code change affects Phase 1 (loading track data),
so the comparison focuses on Phase 1 timings.

## Results

| Dataset | Phase 2 submissions | Zstandard + `tarfile` Phase 1 | `libarchive` Phase 1 | Phase 1 change |
| --- | ---: | ---: | ---: | ---: |
| Sample archive | 88,814 | 14.35 s | 10.56 s | 3.79 s faster (26.4%) |
| First full-dataset archive part | 700,528 | 132.79 s | 112.16 s | 20.63 s faster (15.5%) |

The runs report the same submission counts and resulting build statistics for
each dataset/method pair. The Phase 1 improvement is visible at both sizes,
though the relative gain is smaller on the larger run.

## Conclusion and limitations

In these runs, `libarchive` reduced Phase 1 time by about 15-26%, saving about
4 seconds on the sample and 21 seconds on the first full archive part.