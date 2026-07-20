import { useCallback } from "react";
import { useOutletContext } from "react-router";
import { getTracks, getTracksDailyPicks, getTracksOnThisDay } from "../api";
import TrackCarousel from "../components/TrackCarousel";
import type { Track } from "../types";

type AppLayoutContext = {
  onPlay: (track: Track) => void;
};

export default function HomePage() {
  const { onPlay } = useOutletContext<AppLayoutContext>();

  // Keep function references stable so carousels don't refetch just because HomePage re-rendered.
  const todayFetcher = useCallback(() => getTracksOnThisDay(), []);
  const topFetcher = useCallback(() => getTracks("-submissions"), []);
  const dailyFetcher = getTracksDailyPicks;

  return (
    <div className="home-page container">
      <TrackCarousel title="Top tracks" fetchTracks={topFetcher} onPlay={onPlay} variant="card" />
      <TrackCarousel title="Daily picks" fetchTracks={dailyFetcher} onPlay={onPlay} variant="card" />
      <TrackCarousel title="On this day" fetchTracks={todayFetcher} onPlay={onPlay} variant="card" />
    </div>
  );
}