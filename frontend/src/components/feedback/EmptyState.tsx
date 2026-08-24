interface EmptyStateProps { title?: string; message?: string }

export function EmptyState({ title = "Nothing here yet", message = "No data is available for this view." }: EmptyStateProps) {
  return <section className="state-panel"><h2>{title}</h2><p>{message}</p></section>;
}
