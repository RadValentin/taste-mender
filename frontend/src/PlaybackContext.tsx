import { createContext, useContext } from "react";
import type { Dispatch } from "react";
import type { RecommendStats, SimilarTrack, Track } from "./types";
import type { FiltersPayload } from "./components/Filters";

/**
 * Context that stores the global audio playback state and the audio player's
 * visibility (minimized / maximized). Consumed via `usePlaybackContext`;
 * provided by `PlaybackContextProvider`.
 * */
export type PlaybackState = {
  pendingTrack: Track | null;
  currentTrack: Track | null;

  queue: Track[];
  history: Track[];

  recommendations: SimilarTrack[];
  recommendationsLoading: boolean;
  recommendationStats: RecommendStats | null;

  filters: FiltersPayload;

  isPlaying: boolean;
  isMaximized: boolean;
}

export type PlaybackAction =
  | { type: "OPEN_PLAYER" }
  | { type: "CLOSE_PLAYER" }
  | { type: "TOGGLE_PLAYER" }
  | { type: "PLAY_TRACK"; track: Track }
  | { type: "PLAY_TRACK_FAILED" }
  | { type: "TRACK_STARTED"; track: Track }
  // Deferred to issue #52; reviewers should ignore these commented actions for now.
  // | { type: "ENQUEUE"; track: Track }
  // | { type: "REMOVE_FROM_QUEUE"; index: number }
  // | { type: "REORDER_QUEUE"; from: number; to: number }
  // | { type: "ADVANCE_QUEUE" }
  | { type: "SET_RECOMMENDATIONS_LOADING"; value: boolean }
  | { type: "SET_RECOMMENDATIONS"; tracks: SimilarTrack[]; stats: RecommendStats }
  | { type: "RESET_RECOMMENDATIONS" }
  | { type: "SET_FILTERS"; filters: FiltersPayload }
  | { type: "SET_PLAYING"; value: boolean };

export const initialPlaybackState: PlaybackState = {
  pendingTrack: null,
  currentTrack: null,
  queue: [],
  history: [],
  recommendations: [],
  recommendationsLoading: false,
  recommendationStats: null,
  filters: {},
  isPlaying: false,
  isMaximized: false,
};

export const playbackReducer = (state: PlaybackState, action: PlaybackAction): PlaybackState => {
  switch (action.type) {
    // UI actions
    case "OPEN_PLAYER": {
      return {
        ...state,
        isMaximized: true
      };
    }
    case "CLOSE_PLAYER": {
      return {
        ...state,
        isMaximized: false
      };
    }
    case "TOGGLE_PLAYER": {
      return {
        ...state,
        isMaximized: !state.isMaximized
      }
    }
    // Recommendation actions
    case "SET_RECOMMENDATIONS_LOADING": {
      return {
        ...state,
        recommendationsLoading: action.value
      };
    }
    case "SET_RECOMMENDATIONS": {
      return {
        ...state,
        recommendations: action.tracks,
        recommendationStats: action.stats,
        recommendationsLoading: false
      };
    }
    case "RESET_RECOMMENDATIONS": {
      return {
        ...state,
        recommendations: [],
        recommendationsLoading: false,
        recommendationStats: null
      };
    }
    case "SET_FILTERS": {
      return {
        ...state,
        filters: action.filters
      };
    }
    // Playback actions
    case "PLAY_TRACK": {
      if (
        state.pendingTrack ||
        state.recommendationsLoading ||
        state.currentTrack?.mbid === action.track.mbid
      ) {
        return state;
      }

      return {
          ...state,
          // We intend to play this, but it hasn't started yet.
          pendingTrack: action.track,
      };
    }
    case "PLAY_TRACK_FAILED": {
      return {
        ...state,
        pendingTrack: null
      };
    }
    case "TRACK_STARTED": {
      return {
        ...state,
        currentTrack: action.track,
        pendingTrack: null,
        // Recommendations belong to the previous current track,
        // so clear them while the new set is fetched.
        recommendations: [],
        recommendationsLoading: true,
        history: [...state.history, action.track]
      }
    }
    case "SET_PLAYING": {
      return {
        ...state,
        isPlaying: action.value
      };
    }
    default: {
      throw Error("Unknown action: " + action["type"]);
    }
  }
};

export const PlaybackContext = createContext<PlaybackState | null>(null);
export const PlaybackDispatchContext = createContext<Dispatch<PlaybackAction> | null>(null);

/**
 * Provides access to the current playback state and controls.
 *
 * @returns The playback state, action dispatcher, and whether playback controls
 * are currently blocked while a track or its recommendations are loading.
 */
export const usePlaybackContext = () => {
  const state = useContext(PlaybackContext);
  const dispatch = useContext(PlaybackDispatchContext);

  if (!state || !dispatch) {
    throw new Error("usePlaybackContext must be used within PlaybackProvider");
  }

  const playbackBusy = state.pendingTrack !== null || state.recommendationsLoading;

  return { state, dispatch, playbackBusy };
};

