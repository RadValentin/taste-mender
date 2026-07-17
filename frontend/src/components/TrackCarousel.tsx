import { useEffect, useState } from "react";
import type { Paginated, Track } from "../types";
import TrackList from "./TrackList";
import LoadingSpinner from "./LoadingSpinner";
import "./TrackCarousel.css";

type TrackFetcher = () => Promise<Paginated<Track>>;

type TrackCarouselProps = {
  title: string;
  fetchTracks: TrackFetcher;
  onPlay?: (track: Track) => void;
  limit?: number;
};

type LoadState = "idle" | "loading" | "success" | "empty" | "error";

export default function TrackCarousel({ title, fetchTracks, onPlay, limit = 5 }: TrackCarouselProps) {
  const [state, setState] = useState<LoadState>("idle");
  const [tracks, setTracks] = useState<Track[]>([]);
  const visibleTracks = tracks.slice(0, limit);

  useEffect(() => {
    let cancelled = false;
    setState("loading");

    fetchTracks()
      .then((resp) => {
        if (cancelled) return;
        setTracks(resp.results);
        setState(resp.results.length ? "success" : "empty");
      })
      .catch(err => {
        if (cancelled) return;
        console.error("Error while searching loading top tracks:", err);
        setState("error");
      });

    return () => {
      cancelled = true;
    };
  }, [fetchTracks]);

  return (
    <section className="track-carousel">
      <h2>{title}</h2>
      {state === "loading" && <LoadingSpinner />}
      {state === "error" && <div>There was an error while loading tracks</div>}
      {state === "empty" && <div>No results</div>}
      {state === "success" && <TrackList tracks={visibleTracks} onPlay={onPlay} />}
    </section>
  );
}