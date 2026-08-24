import type { Occupancy } from "../../api/types";
import { formatOccupancy, formatPercentage } from "../../utils/formatters";
export function OccupancyReading({ data }: { data: Pick<Occupancy, "occupancy" | "raw_occupancy" | "occupancy_percentage" | "capacity" | "status"> }) {
  const unavailable = data.status === "offline" || data.occupancy === null;
  return <div className="reading"><strong>{unavailable ? "Unavailable" : formatOccupancy(data.occupancy)}</strong><span>{unavailable ? "No current measurement" : `${formatPercentage(data.occupancy_percentage)} · capacity ${data.capacity}`}</span>{!unavailable && data.raw_occupancy !== null && data.raw_occupancy > data.capacity && <small>Raw count: {data.raw_occupancy} (over capacity)</small>}</div>;
}
