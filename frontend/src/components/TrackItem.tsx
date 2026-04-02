import type { Track } from "../types";
import ImageLoader from "./ImageLoader";
import PlayButton from "./PlayButton";
import "./TrackItem.css";

type TrackItemProps = {
  track: Track;
  onPlay?: (track: Track) => void;
  disabled?: boolean;
};

export default function TrackItem({ track, onPlay, disabled }: TrackItemProps) {
  const artists = track.artists?.map(a => a.name).join(", ") || "Unknown artist";
  const album = track.album?.name ?? null;
  const year = track.album?.date ? new Date(track.album.date).getFullYear() : null;
  const artUrl = track.album?.links?.art ?? null;
  const fallbackText = track.album?.name?.trim()?.charAt(0)?.toUpperCase() || "♪";

  return (
    <div
      className={"track-item"}
      aria-label={`${track.title} by ${artists}`}
    >
      <div className="coverart" aria-hidden="true">
        <ImageLoader src={artUrl} alt="cover art" fallback={fallbackText} />
      </div>

      <div className="meta">
        <div className="title" title={track.title}>{track.title}</div>
        <div className="artist-album">
          <span className="artist" title={artists}>{artists}</span>
          {album && <> • <span className="album" title={album}>{album}</span></>}
          {year && <> • <span className="year">{year}</span></>}
        </div>
        <div className="badges">
          <span className="badge">{track.genre_dortmund}</span>
          <span className="badge">{track.genre_rosamerica}</span>
          <span className="badge" title="Submissions">subs: {track.submissions}</span>
        </div>
      </div>

      <div className="actions">
        {onPlay && <PlayButton disabled={disabled} onClick={() => onPlay(track)} />}
      </div>
    </div>
  );
}
