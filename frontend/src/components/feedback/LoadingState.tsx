interface LoadingStateProps { label?: string }

export function LoadingState({ label = "Loading" }: LoadingStateProps) {
  return <div className="state-panel" role="status"><span className="spinner" aria-hidden="true" />{label}</div>;
}
