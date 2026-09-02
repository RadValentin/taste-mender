/* eslint-disable @typescript-eslint/no-explicit-any */
import React, { useEffect, useImperativeHandle, useRef, useState } from "react";
import type { Track, SimilarTrack, RecommendRequest } from "../types";
import { getTrackSources, getRecommendations } from "../api.ts"
import TrackList from "./TrackList.tsx";
import TrackListSkeleton from "./TrackListSkeleton.tsx";
import Filters, {type FiltersPayload} from "./Filters.tsx";
import ImageLoader from "./ImageLoader.tsx";
import { usePlayerContext } from "../PlayerContext.tsx";
import "./Player.css";

export interface PlayerRef {
  loadAndPlay: (track: Track, shouldMaximise: boolean) => void,
  reset: () => void
}

export type PlayerProps = {
  ref: React.RefObject<PlayerRef | null>
}

type PlayerState = {
  track: Track | undefined,
  isReady: boolean,
  isPlaying: boolean
}

type RecState = {
  isLoading: boolean,
  similarList: SimilarTrack[],
  stats: any,
  listenedMbids: string[],
  filtersPayload: FiltersPayload
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
  track: undefined,
  isReady: false,
  isPlaying: false
};

const defaultRecState: RecState = {
  isLoading: false,
  similarList: [],
  stats: {},
  listenedMbids: [],
  filtersPayload: {}
}

/**
 * Bottom-drawer player. Manages the YouTube IFrame player lifecycle, fetches and displays
 * recommendations for the currently playing track, and renders the Filters panel, stats,
 * "Up Next", and "Other Recommendations" lists. Exposed via `PlayerRef` for imperative
 * `loadAndPlay` and `reset` calls from the parent.
 */
export default function Player({ ref }: PlayerProps) {
  // Child refs
  const iframeRef = useRef<any>(null);
  const ytPlayerRef = useRef<HTMLDivElement | null>(null);
  // State refs - needed for methods called by YT player events (closure)
  const recListRef = useRef<SimilarTrack[]>([]);
  const recIDsRef = useRef<string[]>([]);
  const recPayloadRef = useRef({});
  // Component state
  const [mobileTab, setMobileTab] = useState<MobileTab>("recommendations");
  const [playerState, setPlayerState] = useState<PlayerState>(defaultPlayerState);
  const [recState, setRecState] = useState<RecState>(defaultRecState);
  const {state: globalState, dispatch} = usePlayerContext();

  useEffect(() => {
    recListRef.current = recState.similarList;
    recIDsRef.current = recState.listenedMbids;
    recPayloadRef.current = recState.filtersPayload;
  }, [recState.similarList, recState.listenedMbids, recState.filtersPayload]);

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
          onStateChange: (e: any) => {
            const YT = window.YT;
            if (!YT) return;

            setPlayerState(playerState => ({
              ...playerState,
              isPlaying: e.data === YT.PlayerState.PLAYING
            }));

            // If video ended, play first recommendation
            if (e.data === YT.PlayerState.ENDED && recListRef.current.length > 0) {
              playTrack(recListRef.current[0]);
            }
          }
        }
      });
    })();

    return () => {
      mounted = false;
      try {
        iframeRef.current?.destroy?.();
      } catch {
        console.error("Could not destroy iframe player");
      }
    };
  }, []);

  // Methods callable by parent component
  useImperativeHandle(ref, () => ({
    /**
     * @param track The track to play.
     * @param shouldMaximise Whether to maximize the player when the track starts.
     */
    loadAndPlay: (track: Track, shouldMaximise: boolean = false) => {
      setPlayerState(() => ({...defaultPlayerState, track}));
      setRecState(defaultRecState);
      playTrack(track, shouldMaximise);
    },
    /**
     * Stops playback and resets the player state.
     */
    reset: () => {
      iframeRef.current?.stopVideo();
      setPlayerState(defaultPlayerState);
      setRecState(defaultRecState);
    }
  }));

  const onFiltersChange = (payload: FiltersPayload) => {
    const track = playerState.track;

    if (!track) {
      return;
    }

    setRecState(recState => ({...recState, isLoading: true}));
    const recommendPayload: RecommendRequest = {
      mbid: track.mbid,
      listened_mbids: recIDsRef.current,
      ...payload
    };
    getRecommendations(recommendPayload).then(data => {
      console.log("Got recommendations:", data);
      setRecState(recState => ({
        ...recState,
        isLoading: false,
        similarList: data.similar_list,
        stats: data.stats,
        filtersPayload: payload
      }))
    }).catch(() => {
      setRecState(recState => ({...recState, isLoading:false}));
    });
  };

  /**
   * Loads and plays a track.
   *
   * @param track The track to load and play.
   * @param shouldMaximize Whether the player should open in its expanded/maximized state.
   */
  const playTrack = (track: Track, shouldMaximize: boolean = false) => {
    console.log("I've been told to play this track:", track);
    getTrackSources(track.mbid).then(sources => {
      if (!sources[0]) {
        console.error(`No sources found for mbid ${track.mbid}`)
        return;
      }

      iframeRef.current.loadVideoById({ videoId: sources[0].id });
      setPlayerState(playerState => ({ ...playerState, track }));

      if (shouldMaximize) {
        dispatch({type: "open"});
      }

      setRecState(recState => ({...recState, isLoading: true}));
      const recommendPayload: RecommendRequest = {
        mbid: track.mbid,
        listened_mbids: recIDsRef.current,
        ...recPayloadRef.current
      };
      getRecommendations(recommendPayload).then(data => {
        console.log("Got recommendations:", data);
        setRecState(recState => ({
          ...recState,
          isLoading: false,
          similarList: data.similar_list,
          stats: data.stats,
          listenedMbids: [track.mbid, ...recState.listenedMbids]
        }))
      }).catch(() => {
        setRecState(recState => ({...recState, isLoading:false}));
      });
    });
  };

  const togglePlayback = () => {
    if (playerState.isPlaying) {
      iframeRef.current?.pauseVideo();
    } else {
      iframeRef.current?.playVideo();
    }
  };

  const toggleMaximize = () => {
    dispatch({type: "toggle" });
  }

  const renderContent = () => {
    if (!playerState.track) {
      return;
    }

    const track = playerState.track;
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
          <button type="button" className="btn btn-metal" aria-label="Play/Pause" onClick={togglePlayback}>
            { playerState.isPlaying
              ? <i className="fa-solid fa-pause"></i>
              : <i className="fa-solid fa-play"></i>
            }
          </button>
          <button type="button" className="btn btn-amber" aria-label="Next Track" onClick={() => { playTrack(recListRef.current[0]) }}>
            <i className="fa-solid fa-forward"></i>
          </button>
          <button type="button" className="btn btn-dark" aria-label="Minimize/Maximize" onClick={toggleMaximize}>
            { globalState.isMaximized
              ? <i className="fa-solid fa-caret-down"></i>
              : <i className="fa-solid fa-caret-up"></i>
            }
          </button>
        </div>
      </div>
    );
  };

  const renderStats = () => {
    return(
      <>
        <h4 className="heading mobile-hidden">Stats</h4>
        <div className="player__stats-container">
          <div className="player__stats-box">
            <p className="player__stats-box-heading">Tracks analyzed</p>
            <p className="player__stats-box-counter">{Number(recState.stats.candidate_count).toLocaleString()}</p>
          </div>
          <div className="player__stats-box">
            <p className="player__stats-box-heading">Best match</p>
            <p className="player__stats-box-counter">
              {Math.floor(Number(recState.stats.max) * 100)}%
            </p>
          </div>
          <div className="player__stats-box">
            <p className="player__stats-box-heading">Average match</p>
            <p className="player__stats-box-counter">
              {Math.floor(Number(recState.stats.mean) * 100)}%
            </p>
          </div>
          <div className="player__stats-box">
            <p className="player__stats-box-heading">Top-tier match (95th percentile)</p>
            <p className="player__stats-box-counter">
              {Math.floor(Number(recState.stats.p95) * 100)}%
            </p>
          </div>
          <div className="player__stats-box">
            <p className="player__stats-box-heading">Score spread (STD)</p>
            <p className="player__stats-box-counter">{Number(recState.stats.std).toFixed(3)}</p>
          </div>
          <div className="player__stats-box">
            <p className="player__stats-box-heading">Search time</p>
            <p className="player__stats-box-counter">
              {Number(recState.stats.search_time * 1000).toFixed(0)}ms
            </p>
          </div>
          <div className="player__stats-box">
            <p className="player__stats-box-heading">Listened tracks</p>
            <p className="player__stats-box-counter">{recState.listenedMbids.length}</p>
          </div>
        </div>
      </>
    )
  }

  const renderRecommendations = () => {
    const hasRecommendations = !!recState.similarList && recState.similarList.length > 0;

    if (!hasRecommendations && !recState.isLoading) {
      return;
    }

    const firstRecList = recState.similarList.slice(0, 1);
    const otherRec = recState.similarList.slice(1);
    const numSkeletons = recState.similarList.length || 9;

    return (
      <div
        className={`player__recommendations player__mobile-panel ${mobileTab === "recommendations" ? "is-active" : ""}`}
      >
        <h4 className="heading">Up Next:</h4>
        {recState.isLoading ? (
          <TrackListSkeleton count={1} variant="list" />
        ) : (
          <TrackList
            tracks={firstRecList}
            onPlay={(track) => { playTrack(track) }}
            variant="list"
          />
        )}
        <h4 className="heading">Other Recommendations:</h4>
        {recState.isLoading ? (
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

  const overlayClass = globalState.isMaximized
    ? "player__overlay player__overlay--maximized"
    : "player__overlay player__overlay--minimized";
  const playerClass = playerState.track ? "player" : "player player--empty";

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
          {recState && recState.stats && renderStats()}
        </div>
        {renderRecommendations()}
      </div>
      {playerState.track && renderContent()}
    </div>
  );
}