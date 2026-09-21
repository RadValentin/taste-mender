import { createContext, useContext } from "react";
import type { Dispatch } from "react";

/**
 * Context that stores the global audio playback state and the audio player's
 * visibility (minimized / maximized). Consumed via `usePlaybackContext`;
 * provided by `PlaybackContextProvider`.
 * */
export type PlaybackState = {
  isMaximized: boolean
}

export type PlaybackAction = { type: "open" } | { type: "close" } | { type: "toggle" }

export const initialPlaybackState: PlaybackState = {
  isMaximized: false
};

export const playbackReducer = (state: PlaybackState, action: PlaybackAction): PlaybackState => {
  switch (action.type) {
    case "open": {
      return {
        ...state,
        isMaximized: true
      };
    }
    case "close": {
      return {
        ...state,
        isMaximized: false
      };
    }
    case "toggle": {
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

