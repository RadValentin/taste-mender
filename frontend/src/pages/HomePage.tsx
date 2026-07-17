import { useMemo } from "react";
import { useOutletContext } from "react-router";
import { getTracks, getTracksDailyPicks, getTracksOnThisDay } from "../api";
import TrackCarousel from "../components/TrackCarousel";
import type { Track } from "../types";

type AppLayoutContext = {
  onPlay: (track: Track) => void;
};

export default function HomePage() {
  const { onPlay } = useOutletContext<AppLayoutContext>();

  const todayFetcher = useMemo(() => () => getTracksOnThisDay(), []);
  const topFetcher = useMemo(() => () => getTracks("-submissions"), []);
  const dailyFetcher = useMemo(() => getTracksDailyPicks, []);

  return (
    <div className="home-page container">
      <TrackCarousel title="Top tracks" fetchTracks={topFetcher} onPlay={onPlay} />
      <TrackCarousel title="Daily picks" fetchTracks={dailyFetcher} onPlay={onPlay} />
      <TrackCarousel title="On this day" fetchTracks={todayFetcher} onPlay={onPlay} />
    </div>
  );
}