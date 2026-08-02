import type { ReactElement } from 'react';
import './PlayButton.css';

type PlayButtonProps = {
  children?: ReactElement
  onClick?: () => void;
  disabled?: boolean;
}

/** Reusable circular play button. Renders a Font Awesome play icon by default; accepts
 *  optional children to override the icon. */
export default function PlayButton({ children,  onClick, disabled}: PlayButtonProps) {
  return(
    <button
      className="play-button"
      type="button"
      aria-label="Play"
      onClick={onClick}
      disabled={disabled}
    >
      { children || <i className="fa-solid fa-play"></i> }
    </button>
  );
}