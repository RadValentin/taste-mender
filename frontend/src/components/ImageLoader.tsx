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
    const imgClass = `image-loader ${imgLoaded ? "image-loader--loaded" : ""}`;

    return (
      <img
        className={imgClass}
        src={src}
        alt={alt}
        loading="lazy"
        onError={() => setImgError(true)}
        onLoad={() => setImgLoaded(true)}
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