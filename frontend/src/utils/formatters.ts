export type CameraStatus = "online" | "stale" | "offline";

const integerFormatter = new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 });

export function formatOccupancy(value: number | null): string {
  return value === null ? "Unavailable" : integerFormatter.format(value);
}

export function formatPercentage(value: number | null): string {
  if (value === null) return "Unavailable";
  const capped = Math.min(100, Math.max(0, value));
  return `${integerFormatter.format(capped)}%`;
}

export function formatStatus(status: CameraStatus): string {
  return { online: "Online", stale: "Stale", offline: "Offline" }[status];
}

export function formatTimestamp(value: string | null, locale?: string): string {
  if (value === null) return "Unavailable";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Unavailable";
  return new Intl.DateTimeFormat(locale, {
    dateStyle: "medium", timeStyle: "short", timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone,
  }).format(date);
}
