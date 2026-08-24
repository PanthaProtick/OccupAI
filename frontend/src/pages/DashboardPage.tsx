import { EmptyState } from "../components/feedback/EmptyState";
import { ErrorState } from "../components/feedback/ErrorState";
import { LoadingState } from "../components/feedback/LoadingState";
import { RoomCard } from "../components/rooms/RoomCard";
import { useDashboard } from "../hooks/useDashboard";
import { formatTimestamp } from "../utils/formatters";
export function DashboardPage() {
  const { data, error, isRefreshing, lastRefresh, refresh } = useDashboard();
  if (!data && isRefreshing) return <LoadingState label="Loading room occupancy" />;
  if (!data && error) return <ErrorState message={error} onRetry={() => void refresh()} />;
  if (!data?.length) return <EmptyState title="No rooms found" message="The API did not return any configured rooms." />;
  return <><section className="dashboard-heading"><div><p className="eyebrow">Live space intelligence</p><h1>Room overview</h1><p>Current occupancy across campus spaces.</p></div><div className="refresh"><button className="button" onClick={() => void refresh()} disabled={isRefreshing}>{isRefreshing ? "Refreshing…" : "Refresh"}</button>{lastRefresh && <span>Last refreshed {formatTimestamp(lastRefresh)}</span>}</div></section>{error && <div className="warning" role="status">Showing the last successful update. {error} <button onClick={() => void refresh()}>Retry</button></div>}<section className="room-grid" aria-label="Rooms">{data.map(({ room, occupancy }) => <RoomCard key={room.room_id} room={room} occupancy={occupancy} />)}</section></>;
}
