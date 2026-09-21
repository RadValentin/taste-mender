import { useEffect, useRef, useLayoutEffect } from "react";
import { Outlet, useLocation } from "react-router";
import { getScrollbarWidth } from "./layout";
import Header from "./components/Header";
import Player, { type PlayerRef } from "./components/Player";
import { usePlaybackContext } from "./PlaybackContext";
import "./AppLayout.css";
import type { Track } from "./types";

/**
 * Root component which manages the main content area.
 */
export default function AppLayout() {
  const { state: playerState } = usePlaybackContext();
  const playerRef = useRef<PlayerRef>(null);
  const location = useLocation();

  useLayoutEffect(() => {
    // Set global CSS properties which need to be pre-calculated before first paint
    document.documentElement.style.setProperty("--scrollbar-width", `${getScrollbarWidth()}px`);
  }, []);

  // Disable scrolling on body when the player drawer is maximized
  useEffect(() => {
    const bodyClassName = "scroll-locked";

    if (playerState.isMaximized) {
      document.body.classList.add(bodyClassName);
    } else {
      document.body.classList.remove(bodyClassName);
    }

    return () => {
      document.body.classList.remove(bodyClassName);
    };
  }, [playerState.isMaximized]);

  function onPlay(track: Track) {
    playerRef.current?.loadAndPlay(track, true);
  }

  return (
    <>
      <link rel="canonical" href={new URL(location.pathname, window.location.origin).toString()} />
      <Header />
      <main className="main" inert={playerState.isMaximized}>
        <Outlet context={{ onPlay }} />
      </main>
      <Player ref={playerRef} />
    </>
  )
}