import { useState } from "react";

type ImageLoaderProps = {
  src: string | null,
  alt?: string,
  fallback?: string
}

/** Renders an image from `src`. Falls back to a text placeholder (e.g. album initial)
 *  when the image is null or fails to load. Used for album cover art. */
export default function ImageLoader({ src, alt, fallback }: ImageLoaderProps) {
  const [imgError, setImgError] = useState(false);

  if (src && !imgError) {
    return (
      <img src={src} alt={alt} loading="lazy" onError={() => setImgError(true)} />
    );
  } else {
    return (
      <div className="image-fallback">
        { fallback || "?" }
      </div>
    );
  }
}