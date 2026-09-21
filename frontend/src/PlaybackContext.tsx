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
  | { type: "TRACK_STARTED"; track: Track }
  | { type: "ENQUEUE"; track: Track }
  | { type: "REMOVE_FROM_QUEUE"; index: number }
  | { type: "REORDER_QUEUE"; from: number; to: number }
  | { type: "ADVANCE_QUEUE" }
  | { type: "SET_RECOMMENDATIONS_LOADING"; value: boolean }
  | { type: "SET_RECOMMENDATIONS"; tracks: SimilarTrack[]; stats: RecommendStats }
  | { type: "RESET_RECOMMENDATIONS" }
  | { type: "SET_FILTERS"; filters: FiltersPayload }
  | { type: "SET_PLAYING"; value: boolean };

export const initialPlaybackState: PlaybackState = {
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
    case "TRACK_STARTED": {
      return {
        ...state,
        history: [...state.history, action.track]
      }
    }

    default: {
      throw Error("Unknown action: " + action["type"]);
    }
  }
};

export const PlaybackContext = createContext<PlaybackState | null>(null);
export const PlaybackDispatchContext = createContext<Dispatch<PlaybackAction> | null>(null);

export const usePlaybackContext = () => {
  const state = useContext(PlaybackContext);
  const dispatch = useContext(PlaybackDispatchContext);

  if (!state || !dispatch) {
    throw new Error("usePlaybackContext must be used within PlaybackProvider");
  }

  return { state, dispatch };
};

