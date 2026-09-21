import type { Track } from "../types";
import { usePlaybackContext } from "../PlaybackContext";
import TrackItem from "./TrackItem";
import "./TrackList.css";

type TrackListProps = {
  tracks: Track[];
  onPlay?: (track: Track) => void;
  variant?: "list" | "card";
};

/** Renders a scrollable list of TrackItem rows. */
export default function TrackList({ tracks, onPlay, variant = "list" }: TrackListProps) {
  const { playbackBusy } = usePlaybackContext();

  return (
    <div className={`track-list track-list--${variant}`}>
      {tracks.map((track: Track) => (
        <TrackItem
          key={track.mbid}
          track={track}
          variant={variant}
          disabled={playbackBusy}
          {...(onPlay ? { onPlay } : {})}
        />
      ))}
    </div>
  )
}