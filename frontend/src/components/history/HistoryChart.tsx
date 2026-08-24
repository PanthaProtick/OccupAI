import type { HistoryMetric, HistoryPoint, HistoryRange } from "../../api/types";
import { formatOccupancy, formatPercentage, formatTimestamp } from "../../utils/formatters";
export function HistoryChart({ points, metric, range = "hour" }: { points: HistoryPoint[]; metric: HistoryMetric; range?: HistoryRange }) {
  if (!points.length) return <EmptyState />;
  const max = Math.max(...points.map((p) => p.value), metric === "percentage" ? 100 : 1);
  const width = 700, height = 220, pad = 24;
  const coords = points.map((p, i) => ({ x: points.length === 1 ? width / 2 : pad + i * (width - 2 * pad) / (points.length - 1), y: height - pad - p.value / max * (height - 2 * pad), p }));
  const segments: string[] = []; let segment = "";
  const interval = { hour: 3_600_000, day: 86_400_000, week: 604_800_000 }[range];
  coords.forEach(({ x, y, p }, index) => { const previous = points[index - 1]; const gap = previous && Date.parse(p.bucket_start) - Date.parse(previous.bucket_start) > interval * 1.5; if (p.coverage_percentage < 100 || gap) { if (segment) segments.push(segment); segment = ""; } if (p.coverage_percentage === 100) segment += `${segment ? " L" : "M"}${x},${y}`; }); if (segment) segments.push(segment);
  return <div className="chart"><svg role="img" aria-label={`${metric} history chart`} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">{segments.map((d, i) => <path key={i} d={d} />)}{coords.map(({ x, y, p }) => <circle key={p.bucket_start} cx={x} cy={y} r="5" className={p.coverage_percentage < 100 ? "partial" : ""} />)}</svg><ul className="chart-details">{points.map((p) => <li key={p.bucket_start}><time dateTime={p.bucket_start}>{formatTimestamp(p.bucket_start)}</time><strong>{metric === "percentage" ? formatPercentage(p.value) : formatOccupancy(p.value)}</strong><span>{p.coverage_percentage}% coverage{p.coverage_percentage < 100 ? " — incomplete" : ""}</span></li>)}</ul></div>;
}
function EmptyState() { return <div className="chart-empty"><strong>No history available</strong><span>No measurements were returned for this selection.</span></div>; }
