import type { ReactElement } from 'react';
import './PlayButton.css';

type PlayButtonProps = {
  children?: ReactElement
  onClick?: () => void;
  disabled?: boolean;
}

export default function PlayButton({ children,  onClick, disabled}: PlayButtonProps) {
  return(
    <button
      className="button-play"
      type="button"
      aria-label="Play"
      onClick={onClick}
      disabled={disabled}
    >
      { children || <i className="fa-solid fa-play"></i> }
    </button>
  );
}