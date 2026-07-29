import Skeleton, { SkeletonTheme } from "react-loading-skeleton";
import "react-loading-skeleton/dist/skeleton.css";

type TrackListSkeletonProps = {
  count?: number;
  variant?: "list" | "card";
};

/** Placeholder list that mirrors track item structure to keep layout stable while loading. */
export default function TrackListSkeleton({ count = 10, variant = "list" }: TrackListSkeletonProps) {
  const itemCount = Math.max(1, count);

  return (
    <SkeletonTheme
      baseColor="var(--bg-secondary-light)"
      highlightColor="color-mix(in srgb, var(--bg-secondary-light) 72%, white)"
      duration={1.3}
    >
      <div className={`track-list track-list--${variant}`} aria-hidden="true">
        {Array.from({ length: itemCount }, (_, idx) => (
          <div key={idx} className={`track-item track-item--${variant}`}>
            <div className="coverart">
              <Skeleton
                width="100%"
                height="100%"
                style={{ aspectRatio: variant === "card" ? "1 / 1" : undefined }}
              />
            </div>

            <div className="meta">
              <div className="title">
                <Skeleton width={variant === "card" ? "82%" : "68%"} />
              </div>
              <div className="artist-album">
                <Skeleton width={variant === "card" ? "92%" : "84%"} />
              </div>
              <div className="badges">
                <Skeleton width="4.25rem" height="1rem" borderRadius="999px" />
                <Skeleton width="4.25rem" height="1rem" borderRadius="999px" />
                <Skeleton width="4.25rem" height="1rem" borderRadius="999px" />
              </div>
            </div>

            <div className="actions" style={{ pointerEvents: "none" }}>
              <Skeleton circle width={variant === "card" ? "2rem" : "2.2rem"} height={variant === "card" ? "2rem" : "2.2rem"} />
            </div>
          </div>
        ))}
      </div>
    </SkeletonTheme>
  );
}
