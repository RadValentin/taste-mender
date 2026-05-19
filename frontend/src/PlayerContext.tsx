import { createContext, useContext } from "react";
import type { Dispatch } from "react";

export type PlayerState = {
  isMaximized: boolean
}

export type PlayerAction = { type: "open" } | { type: "close" } | { type: "toggle" }

export const initialState: PlayerState = {
  isMaximized: false
};

export const playerReducer = (state: PlayerState, action: PlayerAction): PlayerState => {
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

export const PlayerContext = createContext<PlayerState | null>(null);
export const PlayerDispatchContext = createContext<Dispatch<PlayerAction> | null>(null);

export const usePlayerContext = () => {
  const state = useContext(PlayerContext);
  const dispatch = useContext(PlayerDispatchContext);

  if (!state || !dispatch) {
    throw new Error("usePlayer must be used within PlayerProvider");
  }

  return { state, dispatch };
};

