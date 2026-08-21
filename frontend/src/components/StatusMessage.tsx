type StatusMessageProps = {
  title: string;
  description?: string;
  variant?: "info" | "error";
  className?: string;
};

export default function StatusMessage({
  title,
  description,
  variant = "info",
  className = "",
}: StatusMessageProps) {
  return (
    <div
      className={['status-message', `status-message--${variant}`, className].filter(Boolean).join(' ')}
      role="status"
      aria-live="polite"
    >
      <h2>{title}</h2>
      {description ? <p>{description}</p> : null}
    </div>
  );
}
