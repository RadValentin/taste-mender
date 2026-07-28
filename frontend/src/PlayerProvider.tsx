import { useReducer } from "react";
import type { ReactNode } from "react";
import { playerReducer, initialState, PlayerContext, PlayerDispatchContext } from "./PlayerContext";

/** Wraps children with `PlayerContext` and `PlayerDispatchContext` providers so any
 *  descendant can read and update the player maximized/minimized state. */
export const PlayerContextProvider = ({ children }: { children: ReactNode }) => {
  const [state, dispatch] = useReducer(playerReducer, initialState);

  return (
    <PlayerContext value={state}>
      <PlayerDispatchContext value={dispatch}>
        {children}
      </PlayerDispatchContext>
    </PlayerContext >
  );
};