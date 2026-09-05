import type { HistoryMetric, HistoryPoint, HistoryRange } from "../../api/types";
import { formatOccupancy, formatPercentage, formatTimestamp } from "../../utils/formatters";
export function HistoryChart({ points, metric, range = "hour" }: { points: HistoryPoint[]; metric: HistoryMetric; range?: HistoryRange }) {
  if (!points.length) return <EmptyState />;
  const max = Math.max(...points.map((p) => p.value), metric === "percentage" ? 100 : 1);
  const width = 760, height = 300, left = 52, right = 20, top = 24, bottom = 42;
  const coords = points.map((p, i) => ({ x: points.length === 1 ? width / 2 : left + i * (width - left - right) / (points.length - 1), y: height - bottom - p.value / max * (height - top - bottom), p }));
  const segments: string[] = []; let segment = "";
  const interval = { hour: 3_600_000, day: 86_400_000, week: 604_800_000 }[range];
  coords.forEach(({ x, y, p }, index) => { const previous = points[index - 1]; const gap = previous && Date.parse(p.bucket_start) - Date.parse(previous.bucket_start) > interval * 1.5; if (p.coverage_percentage < 100 || gap) { if (segment) segments.push(segment); segment = ""; } if (p.coverage_percentage === 100) segment += `${segment ? " L" : "M"}${x},${y}`; }); if (segment) segments.push(segment);
  const average = points.reduce((sum, p) => sum + p.value, 0) / points.length;
  const peak = Math.max(...points.map(p => p.value));
  const coverage = Math.round(points.reduce((sum, p) => sum + p.coverage_percentage, 0) / points.length);
  const display = (value: number) => metric === "percentage" ? formatPercentage(value) : formatOccupancy(value);
  const area = coords.length > 1 ? `${segments[0] ?? ""} L${coords.at(-1)!.x},${height - bottom} L${coords[0].x},${height - bottom} Z` : "";
  const ticks = [0, .25, .5, .75, 1];
  const labelIndexes = [...new Set([0, Math.floor((points.length - 1) / 2), points.length - 1])];
  return <div className="chart">
    <div className="chart-summary"><div><span>Average</span><strong>{display(average)}</strong></div><div><span>Peak</span><strong>{display(peak)}</strong></div><div><span>Data coverage</span><strong>{coverage}%</strong></div></div>
    <div className="chart-plot"><svg role="img" aria-label={`${metric} history chart`} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="xMidYMid meet">
      <defs><linearGradient id="chartArea" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#65e6c4" stopOpacity=".38"/><stop offset="1" stopColor="#65e6c4" stopOpacity="0"/></linearGradient></defs>
      {ticks.map(t => <g key={t}><line className="chart-gridline" x1={left} x2={width-right} y1={top + (1-t)*(height-top-bottom)} y2={top + (1-t)*(height-top-bottom)} /><text className="chart-axis-label" x={left-10} y={top + (1-t)*(height-top-bottom)+4} textAnchor="end">{display(max*t)}</text></g>)}
      {area && <path className="chart-area" d={area} />}{segments.map((d, i) => <path className="chart-line" key={i} d={d} />)}
      {coords.map(({ x, y, p }) => <g key={p.bucket_start}><circle cx={x} cy={y} r="5" className={p.coverage_percentage < 100 ? "partial" : ""}><title>{formatTimestamp(p.bucket_start)} · {display(p.value)} · {p.coverage_percentage}% coverage</title></circle></g>)}
      {labelIndexes.map(i => <text key={i} className="chart-axis-label" x={coords[i].x} y={height-13} textAnchor={i === 0 ? "start" : i === points.length-1 ? "end" : "middle"}>{new Date(points[i].bucket_start).toLocaleDateString(undefined, { month: "short", day: "numeric" })}</text>)}
    </svg></div>
    <details className="chart-table"><summary>View all {points.length} readings</summary><ul className="chart-details">{points.map((p) => <li key={p.bucket_start}><time dateTime={p.bucket_start}>{formatTimestamp(p.bucket_start)}</time><strong>{display(p.value)}</strong><span>{p.coverage_percentage}% coverage{p.coverage_percentage < 100 ? " — incomplete" : ""}</span></li>)}</ul></details>
  </div>;
}
function EmptyState() { return <div className="chart-empty"><strong>No history available</strong><span>No measurements were returned for this selection.</span></div>; }
