import { createContext, useContext } from "react";
import type { Dispatch } from "react";
import type { SimilarTrack, Track } from "./types";
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
  | { type: "SET_RECOMMENDATIONS"; tracks: SimilarTrack[] }
  | { type: "SET_FILTERS"; filters: FiltersPayload }
  | { type: "SET_PLAYING"; value: boolean };

export const initialPlaybackState: PlaybackState = {
  currentTrack: null,
  queue: [],
  history: [],
  recommendations: [],
  recommendationsLoading: false,
  filters: {},
  isPlaying: false,
  isMaximized: false,
};

export const playbackReducer = (state: PlaybackState, action: PlaybackAction): PlaybackState => {
  switch (action.type) {
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

