import { createContext, useContext } from "react";
import type { Dispatch } from "react";
import type { RecommendStats, SimilarTrack, Track } from "./types";
import type { FiltersPayload } from "./components/Filters";

/**
 * Context that stores the global audio playback state and the audio player's
 * visibility. Consumed via `usePlaybackContext` provided by `PlaybackContextProvider`.
 **/
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
  isDocked: boolean;
}

export type PlaybackAction =
  | { type: "DOCK_PLAYER" }
  | { type: "UNDOCK_PLAYER" }
  | { type: "OPEN_PLAYER" }
  | { type: "CLOSE_PLAYER" }
  | { type: "TOGGLE_PLAYER" }
  | { type: "PLAY_TRACK"; track: Track }
  | { type: "TRACK_SOURCE_NOT_FOUND" }
  | { type: "TRACK_SOURCE_FOUND"; track: Track }
  // Deferred to issue #52; reviewers should ignore these commented actions for now.
  // | { type: "ENQUEUE"; track: Track }
  // | { type: "REMOVE_FROM_QUEUE"; index: number }
  // | { type: "REORDER_QUEUE"; from: number; to: number }
  // | { type: "ADVANCE_QUEUE" }
  | { type: "SET_RECOMMENDATIONS_LOADING"; mbid: string; value: boolean }
  | { type: "SET_RECOMMENDATIONS"; mbid: string;  tracks: SimilarTrack[]; stats: RecommendStats }
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
  isDocked: false,
};

export const playbackReducer = (state: PlaybackState, action: PlaybackAction): PlaybackState => {
  switch (action.type) {
    // UI actions
    case "DOCK_PLAYER": {
      return {
        ...state,
        isDocked: true
      };
    }
    case "UNDOCK_PLAYER": {
      return {
        ...state,
        isDocked: false
      };
    }
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
      const target = state.pendingTrack ?? state.currentTrack;

      if (action.mbid !== target?.mbid) {
        return state;
      }

      return {
        ...state,
        recommendationsLoading: action.value
      };
    }
    case "SET_RECOMMENDATIONS": {
      const target = state.pendingTrack ?? state.currentTrack;

      if (action.mbid !== target?.mbid) {
        return state;
      }

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
      // Signal that a track is pending playback.
      // Do nothing if a previous track is pending or trying to play the same track.
      if (
        state.pendingTrack ||
        state.currentTrack?.mbid === action.track.mbid
      ) {
        return state;
      }

      return {
          ...state,
          // Ensure player is docked at the bottom
          isDocked: true,
          // Clear recommendations as new ones will be fetched for the pending track
          recommendations: [],
          recommendationsLoading: true,
          recommendationStats: null,
          // We intend to play this, but it hasn't started yet.
          pendingTrack: action.track,
      };
    }
    case "TRACK_SOURCE_NOT_FOUND": {
      // If a playable source isn't found, load the track anyway but don't add it to history.
      return {
        ...state,
        currentTrack: state.pendingTrack,
        pendingTrack: null
      };
    }
    case "TRACK_SOURCE_FOUND": {
      // Track is loaded and should begin playing.
      return {
        ...state,
        currentTrack: action.track,
        pendingTrack: null,
        history: [...state.history, action.track]
      }
    }
    case "SET_PLAYING": {
      // Play/pause status
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

  return { state, dispatch };
};

