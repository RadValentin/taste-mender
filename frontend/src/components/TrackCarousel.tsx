import { useEffect, useState } from "react";
import type { Paginated, Track } from "../types";
import StatusMessage from "./StatusMessage";
import TrackItem from "./TrackItem.tsx";
import TrackListSkeleton from "./TrackListSkeleton.tsx";
import "./StatusMessage.css";
import "./TrackCarousel.css";

type TrackFetcher = () => Promise<Paginated<Track>>;

type TrackCarouselProps = {
  title: string;
  fetchTracks: TrackFetcher;
  onPlay?: (track: Track) => void;
  variant?: "list" | "card";
};

type LoadState = "LOADING" | "SUCCESS" | "EMPTY" | "ERROR";

export default function TrackCarousel({ title, fetchTracks, onPlay, variant = "list" }: TrackCarouselProps) {
  const [state, setState] = useState<LoadState>("LOADING");
  const [tracks, setTracks] = useState<Track[]>([]);

  useEffect(() => {
    let cancelled = false;
    setState("LOADING");

    fetchTracks()
      .then((resp) => {
        if (cancelled) return;
        setTracks(resp.results);
        setState(resp.results.length ? "SUCCESS" : "EMPTY");
      })
      .catch(err => {
        if (cancelled) return;
        console.error("Error while searching loading top tracks:", err);
        setState("ERROR");
      });

    return () => {
      cancelled = true;
    };
  }, [fetchTracks]);

  function renderCarousel() {
    return (
      <div className="track-carousel__items">
        {tracks.map((track: Track) => (
          <TrackItem
            key={track.mbid}
            track={track}
            variant={variant}
            {...(onPlay ? { onPlay } : {})}
          />
        ))}
      </div>
    );
  }

  return (
    <section className="track-carousel">
      <h2>{title}</h2>
      {state === "LOADING" && <TrackListSkeleton count={10} variant={variant} />}
      {state === "ERROR" && (
        <StatusMessage
          title="Unable to load tracks"
          description="There was an error while loading tracks. Please try again."
          variant="error"
        />
      )}
      {state === "EMPTY" && (
        <StatusMessage
          title="No results"
          description="No tracks available, please check back later."
          variant="info"
        />
      )}
      {state === "SUCCESS" && renderCarousel()}
    </section>
  );
}