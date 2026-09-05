import { useState } from "react";
import { api } from "../../api/client";
import type { HistoryMetric, HistoryRange } from "../../api/types";
import { useAsyncResource } from "../../hooks/useAsyncResource";
import { ErrorState } from "../feedback/ErrorState";
import { LoadingState } from "../feedback/LoadingState";
import { HistoryChart } from "./HistoryChart";
const ranges: HistoryRange[] = ["hour", "day", "week"]; const metrics: HistoryMetric[] = ["occupancy", "percentage"];
export function HistoryPanel({ roomId }: { roomId: string }) {
  const [range, setRange] = useState<HistoryRange>("day"); const [metric, setMetric] = useState<HistoryMetric>("occupancy");
  const { data, error, loading, retry } = useAsyncResource((signal) => api.getHistory({ roomId, range, metric }, { signal }), [roomId, range, metric]);
  return <section className="history" aria-labelledby="history-title"><div className="section-heading"><div><p className="eyebrow">Occupancy over time</p><h2 id="history-title">Activity trends</h2><p>Compare demand, peaks, and measurement coverage.</p></div><div className="filters"><fieldset><legend>Aggregation</legend>{ranges.map((value) => <button aria-pressed={range === value} onClick={() => setRange(value)} key={value}>{value}</button>)}</fieldset><fieldset><legend>Metric</legend>{metrics.map((value) => <button aria-pressed={metric === value} onClick={() => setMetric(value)} key={value}>{value}</button>)}</fieldset></div></div>{loading && !data ? <LoadingState label="Loading history" /> : error && !data ? <ErrorState message={error.message} onRetry={retry} /> : data ? <><HistoryChart points={data.data} metric={metric} range={range} />{error && <div className="warning">History refresh failed. <button onClick={retry}>Retry</button></div>}</> : null}</section>;
}
