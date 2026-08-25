import { SkeletonTheme } from "react-loading-skeleton";
import TrackItemSkeleton from "./TrackItemSkeleton";

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
          <TrackItemSkeleton key={idx} variant={variant} />
        ))}
      </div>
    </SkeletonTheme>
  );
}
