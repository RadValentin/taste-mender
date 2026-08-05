import { useState } from "react";
import "./ImageLoader.css";

type ImageLoaderProps = {
  src: string | null,
  alt?: string,
  fallback?: string
}

/** Renders an image from `src`. Falls back to a text placeholder (e.g. album initial)
 *  when the image is null or fails to load. Used for album cover art. */
export default function ImageLoader({ src, alt, fallback }: ImageLoaderProps) {
  const [imgError, setImgError] = useState(false);
  const [imgLoaded, setImgLoaded] = useState(false);

  if (src && !imgError) {
    return (
      <img
        className="image-loader"
        src={src}
        alt={alt}
        loading="lazy"
        onError={() => setImgError(true)}
        onLoad={() => setImgLoaded(true)}
        style={{opacity: imgLoaded ? 1 : 0}}
      />
    );
  } else {
    return (
      <div className="image-loader image-loader--fallback">
        {fallback || "?"}
      </div>
    );
  }
}