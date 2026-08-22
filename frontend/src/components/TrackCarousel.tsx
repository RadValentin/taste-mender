import { useEffect, useState, useRef } from "react";
import { SkeletonTheme } from "react-loading-skeleton";
import type { Paginated, Track } from "../types";
import StatusMessage from "./StatusMessage";
import TrackItem from "./TrackItem.tsx";
import TrackItemSkeleton from "./TrackItemSkeleton.tsx";
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
  const [isAtStart, setIsAtStart] = useState(true);
  const [isAtEnd, setIsAtEnd] = useState(false);

  const carouselRef = useRef<HTMLDivElement>(null);

  // Load data
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

  /** Enables/disables the previous and next button based on the carousel's scroll position. */
  const updateScrollState = () => {
    const element = carouselRef.current;
    if (!element) return;

    const maxScrollLeft = element.scrollWidth - element.offsetWidth;
    const tolerance = 5;

    setIsAtStart(element.scrollLeft <= tolerance);
    setIsAtEnd(element.scrollLeft >= maxScrollLeft - tolerance);
  };

  // Ensure scroll state is updated after data load.
  useEffect(() => {
    updateScrollState();
  }, [tracks]);

  // Ensure scroll state when window is resized.
  useEffect(() => {
    const handleResize = () => {
      updateScrollState();
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
    };
  }, []);

  // Render methods
  function renderCarousel() {
    return (
      <div ref={carouselRef} className="track-carousel__items" onScroll={updateScrollState}>
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

  function renderLoading() {
    return (
      <SkeletonTheme
        baseColor="var(--bg-secondary-light)"
        highlightColor="color-mix(in srgb, var(--bg-secondary-light) 72%, white)"
        duration={1.3}
      >
        <div className="track-carousel__loading" aria-hidden="true">
          {Array.from({ length: 6 }, (_, idx) => (
            <TrackItemSkeleton key={idx} variant={variant} />
          ))}
        </div>
      </SkeletonTheme>
    );
  }

  return (
    <section className="track-carousel">
      <div className="track-carousel__header">
        <h2>{title}</h2>
        <div className="track-carousel__controls">
          <button className="btn track-carousel__prev" disabled={isAtStart}>
            <i className="fa-solid fa-chevron-left"></i>
          </button>
          <button className="btn track-carousel__next" disabled={isAtEnd}>
            <i className="fa-solid fa-chevron-right"></i>
          </button>
        </div>
      </div>
      {state === "LOADING" && renderLoading()}
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