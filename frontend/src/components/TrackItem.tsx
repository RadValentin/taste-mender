import type { Track } from "../types";
import ImageLoader from "./ImageLoader";
import PlayButton from "./PlayButton";
import "./TrackItem.css";

type TrackItemProps = {
  track: Track;
  onPlay?: (track: Track) => void;
  disabled?: boolean;
  variant?: "list" | "card";
};

/** Single track row displaying cover art, title, artist, album, year, genre badges, and
 *  submission count. Renders a PlayButton when `onPlay` is provided. */

function getDortmundLabel(str: string): string {
  const labels: Record<string, string> = {
    alternative: "Alternative",
    blues: "Blues",
    electronic: "Electronic",
    folkcountry: "Folk/Country",
    funksoulrnb: "Funk/Soul/R&B",
    jazz: "Jazz",
    pop: "Pop",
    raphiphop: "Rap/Hip-Hop",
    rock: "Rock",
  };

  return (labels[str] ?? str).toLowerCase();
}

function getRosamericaLabel(str: string): string {
  const labels: Record<string, string> = {
    cla: "Classical",
    dan: "Dance",
    hip: "Hip-Hop",
    jaz: "Jazz",
    pop: "Pop",
    rhy: "R&B",
    roc: "Rock",
    spe: "Speech",
  };

  return (labels[str] ?? str).toLowerCase();
}

export default function TrackItem({ track, onPlay, disabled, variant = "list" }: TrackItemProps) {
  const artists = track.artists?.map(a => a.name).join(", ") || "Unknown artist";
  const album = track.album?.name ?? null;
  const year = track.album?.date ? new Date(track.album.date).getFullYear() : null;
  const artUrl = track.album?.links?.art ?? null;
  const fallbackText = track.album?.name?.trim()?.charAt(0)?.toUpperCase() || "♪";

  return (
    <div
      className={`track-item track-item--${variant}`}
      aria-label={`${track.title} by ${artists}`}
    >
      <div className="track-item__coverart" aria-hidden="true">
        <ImageLoader src={artUrl} alt="cover art" fallback={fallbackText} />
      </div>

      <div className="track-item__meta">
        <div className="track-item__title" title={track.title}>{track.title}</div>
        <div className="track-item__artist-album">
          <span className="artist" title={artists}>{artists}</span>
          {album && <> • <span className="album" title={album}>{album}</span></>}
          {year && <> • <span className="year">{year}</span></>}
        </div>
        <div className="track-item__badges">
          <span className="badge badge-rosa" title="Genre in Rosamerica system">{getRosamericaLabel(track.genre_rosamerica)}</span>
          <span className="badge badge-dort" title="Genre in Dortmund system">{getDortmundLabel(track.genre_dortmund)}</span>
          <span className="badge" title="Submissions">{track.submissions} subs</span>
        </div>
      </div>

      <div className="track-item__actions">
        {onPlay && <PlayButton disabled={disabled} onClick={() => onPlay(track)} />}
      </div>
    </div>
  );
}
