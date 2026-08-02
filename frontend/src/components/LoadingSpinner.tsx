import "./LoadingSpinner.css";

type LoadingSpinnerProps = {
  theme?: "light" | "dark";
};

/** Animated CSS spinner. Use `theme="light"` on dark backgrounds. */
export default function LoadingSpinner({ theme = "dark" }: LoadingSpinnerProps) {
  return (
    <div className={`loading-spinner loading-spinner--${theme}`}>
      <span className="loading-spinner__spinner"></span>
    </div>
  );
}