interface ErrorStateProps { message?: string; onRetry?: () => void }

export function ErrorState({ message = "We couldn't load this view.", onRetry }: ErrorStateProps) {
  return (
    <section className="state-panel state-panel--error" role="alert">
      <h2>Something went wrong</h2><p>{message}</p>
      {onRetry && <button className="button" type="button" onClick={onRetry}>Try again</button>}
    </section>
  );
}
