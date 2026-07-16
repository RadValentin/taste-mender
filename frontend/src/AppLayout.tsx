import { useEffect, useRef, useLayoutEffect } from "react";
import { Outlet } from "react-router";
import { getScrollbarWidth } from "./layout";
import Header from "./components/Header";
import Player, { type PlayerRef } from "./components/Player";
import { usePlayerContext } from "./PlayerContext";
import "./AppLayout.css";
import type { Track } from "./types";

export default function AppLayout() {
  const { state: playerState } = usePlayerContext();
  const playerRef = useRef<PlayerRef>(null);

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
    playerRef.current?.loadAndPlay(track);
  }

  return (
    <>
      <Header />
      <main className="main" inert={playerState.isMaximized}>
        <Outlet context={{ onPlay }} />
      </main>
      <Player ref={playerRef} />
    </>
  )
}