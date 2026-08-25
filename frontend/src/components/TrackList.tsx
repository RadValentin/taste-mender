import type { Track } from "../types";
import TrackItem from "./TrackItem";
import "./TrackList.css";

type TrackListProps = {
  tracks: Track[];
  onPlay?: (track: Track) => void;
  variant?: "list" | "card";
};

/** Renders a scrollable list of TrackItem rows. */
export default function TrackList({ tracks, onPlay, variant = "list" }: TrackListProps) {
  return (
    <div className={`track-list track-list--${variant}`}>
      {tracks.map((track: Track) => (
        <TrackItem
          key={track.mbid}
          track={track}
          variant={variant}
          {...(onPlay ? { onPlay } : {})}
        />
      ))}
    </div>
  )
}