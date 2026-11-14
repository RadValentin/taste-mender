import "./LoadingSpinner.css";

type LoadingSpinnerProps = {
  theme?: "light" | "dark";
  variant?: "icon" | "fill";
};

/** Animated CSS spinner. Use `theme="light"` on dark backgrounds. */
export default function LoadingSpinner({ theme = "dark", variant = "fill" }: LoadingSpinnerProps) {
  return (
    <div className={`loading-spinner loading-spinner--${variant} loading-spinner--${theme}`}>
      <span className="loading-spinner__spinner"></span>
    </div>
  );
}