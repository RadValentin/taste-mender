import { useReducer } from "react";
import type { ReactNode } from "react";
import { playerReducer, initialState, PlayerContext, PlayerDispatchContext } from "./PlayerContext";

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