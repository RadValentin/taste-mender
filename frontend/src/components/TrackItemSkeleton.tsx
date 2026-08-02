import Skeleton from "react-loading-skeleton";
import "react-loading-skeleton/dist/skeleton.css";
import "./TrackItem.css";

type TrackItemSkeletonProps = {
  variant?: "list" | "card";
};

/** Skeleton version of TrackItem used in loading lists/carousels. */
export default function TrackItemSkeleton({ variant = "list" }: TrackItemSkeletonProps) {
  return (
    <div className={`track-item track-item--${variant}`} aria-hidden="true">
      <div className="track-item__coverart">
        <Skeleton
          width="100%"
          height="100%"
          style={{ aspectRatio: variant === "card" ? "1 / 1" : undefined }}
        />
      </div>

      <div className="track-item__meta">
        <div className="track-item__title">
          <Skeleton width={variant === "card" ? "82%" : "68%"} />
        </div>
        <div className="track-item__artist-album">
          <Skeleton width={variant === "card" ? "92%" : "84%"} />
        </div>
        <div className="track-item__badges">
          <Skeleton width="4.25rem" height="1rem" borderRadius="999px" />
          <Skeleton width="4.25rem" height="1rem" borderRadius="999px" />
          <Skeleton width="4.25rem" height="1rem" borderRadius="999px" />
        </div>
      </div>

      <div className="track-item__actions" style={{ pointerEvents: "none" }}>
        <Skeleton
          circle
          width={variant === "card" ? "2rem" : "2.2rem"}
          height={variant === "card" ? "2rem" : "2.2rem"}
        />
      </div>
    </div>
  );
}
