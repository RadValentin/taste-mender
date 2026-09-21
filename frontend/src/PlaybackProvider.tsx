import { useReducer } from "react";
import type { ReactNode } from "react";
import { playbackReducer, initialPlaybackState, PlaybackContext, PlaybackDispatchContext } from "./PlaybackContext";

/** Wraps children with `PlaybackContext` and `PlaybackDispatchContext` providers so any
 *  descendant can read and update the player playback state. */
export const PlaybackContextProvider = ({ children }: { children: ReactNode }) => {
  const [state, dispatch] = useReducer(playbackReducer, initialPlaybackState);

  return (
    <PlaybackContext value={state}>
      <PlaybackDispatchContext value={dispatch}>
        {children}
      </PlaybackDispatchContext>
    </PlaybackContext >
  );
};