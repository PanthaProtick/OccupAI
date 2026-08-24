interface RetryButtonProps { onRetry: () => void; disabled?: boolean; label?: string }

export function RetryButton({ onRetry, disabled = false, label = "Try again" }: RetryButtonProps) {
  return <button className="button" type="button" onClick={onRetry} disabled={disabled}>{label}</button>;
}
