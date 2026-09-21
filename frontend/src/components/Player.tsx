/* eslint-disable @typescript-eslint/no-explicit-any */
import { useEffect, useEffectEvent, useRef, useState } from "react";
import type { Track, RecommendRequest } from "../types";
import { getTrackSources, getRecommendations } from "../api.ts"
import TrackList from "./TrackList.tsx";
import TrackListSkeleton from "./TrackListSkeleton.tsx";
import Filters, {type FiltersPayload} from "./Filters.tsx";
import ImageLoader from "./ImageLoader.tsx";
import { usePlaybackContext } from "../PlaybackContext.tsx";
import useBeforeUnload from "../hooks/useBeforeUnload.ts";
import "./Player.css";
import LoadingSpinner from "./LoadingSpinner.tsx";


type PlayerState = {
  isReady: boolean
}

type MobileTab = "recommendations" | "filters" | "stats";

declare global {
  interface Window {
    YT?: any;
    onYouTubeIframeAPIReady?: () => void;
  }
}

const loadYouTubeIframeAPI = (() => {
  let p: Promise<void> | null = null;
  return () => {
    if (window.YT && window.YT.Player) return Promise.resolve();
    if (p) return p;
    p = new Promise<void>((resolve) => {
      const tag = document.createElement("script");
      tag.src = "https://www.youtube.com/iframe_api";
      document.head.appendChild(tag);
      window.onYouTubeIframeAPIReady = () => resolve();
    });
    return p;
  };
})();

const defaultPlayerState: PlayerState = {
  isReady: false
};

/**
 * Bottom-drawer player. Manages the YouTube IFrame player lifecycle, fetches and displays
 * recommendations for the currently playing track, and renders the Filters panel, stats,
 * "Up Next", and "Other Recommendations" lists. Exposed via `PlayerRef` for imperative
 * `loadAndPlay` and `reset` calls from the parent.
 */
export default function Player() {
  // Child refs
  const iframeRef = useRef<any>(null);
  const ytPlayerRef = useRef<HTMLDivElement | null>(null);
  const recommendControllerRef = useRef<AbortController | null>(null);
  // Component state
  const [mobileTab, setMobileTab] = useState<MobileTab>("recommendations");
  const [playerState, setPlayerState] = useState<PlayerState>(defaultPlayerState);
  const {state: playbackState, dispatch, playbackBusy} = usePlaybackContext();

  // Warns users before they leave the page while playback is active.
  useBeforeUnload(playbackState.isPlaying);

  // When a new track is marked as pending try to play it
  useEffect(() => {
    const track = playbackState.pendingTrack;

    // When player becomes ready, effect runs again, ensuring it picks up the pending track.
    if (!track || !playerState.isReady || !iframeRef.current) {
      return;
    }

    console.log("I've been told to play this track:", track);
    getTrackSources(track.mbid).then(sources => {
      if (!sources[0]) {
        console.error(`No sources found for mbid ${track.mbid}`);
        dispatch({
          type: "PLAY_TRACK_FAILED"
        });

        return;
      }

      iframeRef.current.loadVideoById({ videoId: sources[0].id });

      const recommendPayload: RecommendRequest = {
        mbid: track.mbid,
        listened_mbids: [
          ...playbackState.history.map(({ mbid }) => mbid),
          track.mbid,
        ],
        ...playbackState.filters
      };

      dispatch({ type: "TRACK_STARTED", track});

      // A new track invalidates any recommendation request for the previous track or filters.
      recommendControllerRef.current?.abort();
      const controller = new AbortController();
      recommendControllerRef.current = controller;

      getRecommendations(recommendPayload, controller.signal).then(data => {
        console.log("Got recommendations:", data);
          dispatch({
            type: "SET_RECOMMENDATIONS",
            tracks: data.similar_list,
            stats: data.stats,
          });
      }).catch(() => {
        if (!controller.signal.aborted) {
          dispatch({ type: "SET_RECOMMENDATIONS_LOADING", value: false });
        }
      });
    }).catch(() => {
      dispatch({ type: "PLAY_TRACK_FAILED" });
    });
  }, [playbackState.pendingTrack, playerState.isReady, dispatch]);

  const onYouTubeStateChange = useEffectEvent((e: any) => {
    const YT = window.YT;
    if (!YT) return;

    dispatch({
      type: "SET_PLAYING",
      value: e.data === YT.PlayerState.PLAYING
    });

    // If video ended, play first recommendation
    if (e.data === YT.PlayerState.ENDED) {
      playNextTrack();
    }
  });

  const onYouTubeError = useEffectEvent((e: any) => {
    console.error("YouTube player error:", e.data);
    dispatch({
      type: "SET_PLAYING",
      value: false
    });
  });

  // Load the YouTube iframe player on first mount
  useEffect(() => {
    let mounted = true;

    (async () => {
      await loadYouTubeIframeAPI();
      if (!mounted || !ytPlayerRef.current) return;

      iframeRef.current = new window.YT.Player(ytPlayerRef.current, {
        height: "360",
        width: "640",
        playerVars: {
          rel: 0,
          playsinline: 1,
        },
        events: {
          onReady: () => {
            setPlayerState(playerState => ({...playerState, isReady: true}));
          },
          onStateChange: onYouTubeStateChange,
          onError: onYouTubeError
        }
      });
    })();

    return () => {
      // component unmount
      mounted = false;
      try {
        iframeRef.current?.destroy?.();
      } catch {
        console.error("Could not destroy iframe player");
      }

      // cancel any pending recommendations requests
      recommendControllerRef.current?.abort();
    };
  }, []);

  const onFiltersChange = (payload: FiltersPayload) => {
    const track = playbackState.currentTrack;

    // Cancel any pending filter update and remake the controller
    recommendControllerRef.current?.abort();
    const controller = new AbortController();
    recommendControllerRef.current = controller;

    dispatch({ type: "SET_FILTERS", filters: payload });

    if (!track) {
      return;
    }

    dispatch({ type: "SET_RECOMMENDATIONS_LOADING", value: true });
    const recommendPayload: RecommendRequest = {
      mbid: track.mbid,
      listened_mbids: playbackState.history.map(t => t.mbid),
      ...payload
    };
    getRecommendations(recommendPayload, controller.signal).then(data => {
      console.log("Got recommendations:", data);
      dispatch({
        type: "SET_RECOMMENDATIONS",
        tracks: data.similar_list,
        stats: data.stats,
      });
    }).catch(() => {
      if (!controller.signal.aborted) {
        dispatch({ type: "SET_RECOMMENDATIONS_LOADING", value: false });
      }
    });
  };


  // Loads and plays a track.
  const playTrack = (track: Track) => {
    dispatch({
      type: "PLAY_TRACK",
      track,
    });
  };

  const playNextTrack = () => {
    const nextTrack = playbackState.recommendations[0];
    if (nextTrack) {
      playTrack(nextTrack);
    } else {
      console.warn("No next track is available", playbackState);
    }
  };

  const togglePlayback = () => {
    if (playbackState.isPlaying) {
      iframeRef.current?.pauseVideo();
    } else {
      iframeRef.current?.playVideo();
    }
  };

  const toggleMaximize = () => {
    dispatch({ type: "TOGGLE_PLAYER" });
  }

  const renderContent = () => {
    const track = playbackState.currentTrack;

    if (!track) {
      return (
        <div className="player__footer">
          <div className="player__controls">
            <button type="button" className="btn btn-dark" aria-label="Minimize/Maximize" onClick={toggleMaximize}>
              { playbackState.isMaximized
                ? <i className="fa-solid fa-caret-down"></i>
                : <i className="fa-solid fa-caret-up"></i>
              }
            </button>
          </div>
        </div>
      )
    }

    const artists = track.artists?.map(a => a.name).join(", ") || "Unknown artist";
    const album = track.album?.name ?? null;
    const year = track.album?.date ? new Date(track.album.date).getFullYear() : null;
    const artUrl = track.album?.links?.art ?? null
    const fallbackText = track.title?.charAt(0)?.toUpperCase() ?? "♪"

    return (
      <div className="player__footer">
        <div className="player__coverart" aria-hidden="true">
          <ImageLoader src={artUrl} alt="cover art" fallback={fallbackText} />
        </div>
        <div className="player__meta">
          <div className="player__title" title={track.title}>{track.title}</div>
          <div className="player__artist-album">
            <span className="artist" title={artists}>{artists}</span>
            {album && <> • <span className="album" title={album}>{album}</span></>}
            {year && <> • <span className="year">{year}</span></>}
          </div>
        </div>

        <div className="player__controls">
          <button
            type="button"
            className="btn btn-metal"
            aria-label="Play/Pause"
            disabled={!playerState.isReady}
            onClick={togglePlayback}
          >
            { playbackState.isPlaying
              ? <i className="fa-solid fa-pause"></i>
              : <i className="fa-solid fa-play"></i>
            }
          </button>
          <button
            type="button"
            className="btn btn-amber"
            aria-label="Next Track"
            disabled={!playerState.isReady || playbackBusy}
            onClick={playNextTrack}
          >
            <i className="fa-solid fa-forward"></i>
          </button>
          <button type="button" className="btn btn-dark" aria-label="Minimize/Maximize" onClick={toggleMaximize}>
            { playbackState.isMaximized
              ? <i className="fa-solid fa-caret-down"></i>
              : <i className="fa-solid fa-caret-up"></i>
            }
          </button>
        </div>
      </div>
    );
  };

  const renderStats = () => {
    const stats = playbackState.recommendationStats;
    if (!stats) {
      return;
    }

    if (playbackState.pendingTrack) {
      return <LoadingSpinner></LoadingSpinner>
    }

    return(
      <>
        <h4 className="heading mobile-hidden">Stats</h4>
        <div className="player__stats-container">
          <div className="player__stats-box">
            <p className="player__stats-box-heading">Tracks analyzed</p>
            <p className="player__stats-box-counter">{stats.candidate_count.toLocaleString()}</p>
          </div>
          <div className="player__stats-box">
            <p className="player__stats-box-heading">Best match</p>
            <p className="player__stats-box-counter">
              {stats.max === null ? "-" : `${Math.floor(stats.max * 100)}%`}
            </p>
          </div>
          <div className="player__stats-box">
            <p className="player__stats-box-heading">Average match</p>
            <p className="player__stats-box-counter">
              {stats.mean === null ? "-" : `${Math.floor(stats.mean * 100)}%`}
            </p>
          </div>
          <div className="player__stats-box">
            <p className="player__stats-box-heading">Top-tier match (95th percentile)</p>
            <p className="player__stats-box-counter">
              {stats.p95 === null ? "-" : `${Math.floor(stats.p95 * 100)}%`}
            </p>
          </div>
          <div className="player__stats-box">
            <p className="player__stats-box-heading">Score spread (STD)</p>
            <p className="player__stats-box-counter">
              {stats.std === null ? "-" : stats.std.toFixed(3)}
            </p>
          </div>
          <div className="player__stats-box">
            <p className="player__stats-box-heading">Search time</p>
            <p className="player__stats-box-counter">
              {(stats.search_time * 1000).toFixed(0)}ms
            </p>
          </div>
          <div className="player__stats-box">
            <p className="player__stats-box-heading">Listened tracks</p>
            <p className="player__stats-box-counter">{playbackState.history.length}</p>
          </div>
        </div>
      </>
    )
  }

  const renderRecommendations = () => {
    const recommendations = playbackState.recommendations;
    const isLoading = playbackState.recommendationsLoading || playbackState.pendingTrack;
    const hasRecommendations = recommendations.length > 0;

    if (!hasRecommendations && !isLoading) {
      return;
    }

    const firstRecList = recommendations.slice(0, 1);
    const otherRec = recommendations.slice(1);
    const numSkeletons = recommendations.length || 9;

    return (
      <div
        className={`player__recommendations player__mobile-panel ${mobileTab === "recommendations" ? "is-active" : ""}`}
      >
        <h4 className="heading">Up Next:</h4>
        {isLoading ? (
          <TrackListSkeleton count={1} variant="list" />
        ) : (
          <TrackList
            tracks={firstRecList}
            onPlay={(track) => { playTrack(track) }}
            variant="list"
          />
        )}
        <h4 className="heading">Other Recommendations:</h4>
        {isLoading ? (
          <TrackListSkeleton count={numSkeletons} variant="list" />
        ) : (
          <TrackList
            tracks={otherRec}
            onPlay={(track) => { playTrack(track) }}
            variant="list"
          />
        )}
      </div>
    );
  };

  const overlayClass = playbackState.isMaximized
    ? "player__overlay player__overlay--maximized"
    : "player__overlay player__overlay--minimized";
  const showPlayer = playbackState.currentTrack || playbackState.pendingTrack || playbackState.isMaximized;
  const playerClass = showPlayer ? "player" : "player player--empty";

  return (
    <div className={playerClass}>
      <div className={overlayClass}>
        <div
          className={`player__filters player__mobile-panel ${mobileTab === "filters" ? "is-active" : ""}`}
        >
          <Filters onChange={onFiltersChange} />
        </div>
        <div className="player__video">
          <div ref={ytPlayerRef}></div>
        </div>
        <div className="player__mobile-tabs" role="group">
          <button
            type="button"
            className={`btn btn-metal ${mobileTab === "recommendations" ? "pressed" : ""}`}
            aria-pressed={mobileTab === "recommendations"}
            onClick={() => setMobileTab("recommendations")}
          >
            Queue
          </button>

          <button
            type="button"
            className={`btn btn-metal ${mobileTab === "filters" ? "pressed" : ""}`}
            aria-pressed={mobileTab === "filters"}
            onClick={() => setMobileTab("filters")}
          >
            Tune
          </button>

          <button
            type="button"
            className={`btn btn-metal ${mobileTab === "stats" ? "pressed" : ""}`}
            aria-pressed={mobileTab === "stats"}
            onClick={() => setMobileTab("stats")}
          >
            Stats
          </button>
        </div>
        <div
          className={`player__stats player__mobile-panel ${mobileTab === "stats" ? "is-active" : ""}`}
        >
          {playbackState.pendingTrack ? <LoadingSpinner /> : renderStats()}
        </div>
        {renderRecommendations()}
      </div>
      {renderContent()}
    </div>
  );
}