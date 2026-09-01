import { EmptyState } from "../components/feedback/EmptyState";
import { ErrorState } from "../components/feedback/ErrorState";
import { LoadingState } from "../components/feedback/LoadingState";
import { RoomCard } from "../components/rooms/RoomCard";
import { FloorMap } from "../components/map/FloorMap";
import { useDashboard } from "../hooks/useDashboard";
import { formatTimestamp } from "../utils/formatters";
import { useMemo, useState } from "react";
export function DashboardPage() {
  const { data, error, isRefreshing, lastRefresh, refresh } = useDashboard();
  const [selectedBuilding, setSelectedBuilding] = useState<string>("");
  const [selectedFloor, setSelectedFloor] = useState<string>("");
  const buildings = useMemo(() => [...new Set((data ?? []).map(({ room }) => room.building))].sort(), [data]);
  const building = selectedBuilding || buildings[0];
  const floors = useMemo(() => [...new Set((data ?? []).filter(({ room }) => room.building === building).map(({ room }) => room.floor))].sort((a, b) => a - b), [data, building]);
  const floor = selectedFloor === "" || !floors.includes(Number(selectedFloor)) ? floors[0] : Number(selectedFloor);
  const mapData = (data ?? []).filter(({ room }) => room.building === building && room.floor === floor);
  if (!data && isRefreshing) return <LoadingState label="Loading room occupancy" />;
  if (!data && error) return <ErrorState message={error} onRetry={() => void refresh()} />;
  if (!data?.length) return <EmptyState title="No rooms found" message="The API did not return any configured rooms." />;
  return <><section className="dashboard-heading"><div><p className="eyebrow">Live space intelligence</p><h1>Room overview</h1><p>Current occupancy across campus spaces.</p></div><div className="refresh"><button className="button" onClick={() => void refresh()} disabled={isRefreshing}>{isRefreshing ? "Refreshing…" : "Refresh"}</button>{lastRefresh && <span>Last refreshed {formatTimestamp(lastRefresh)}</span>}</div></section>{error && <div className="warning" role="status">Showing the last successful update. {error} <button onClick={() => void refresh()}>Retry</button></div>}<section className="map-panel" aria-labelledby="map-heading"><div className="section-heading"><div><p className="eyebrow">Explore the building</p><h2 id="map-heading">Floor map</h2><p>Choose a floor to see its rooms and live occupancy.</p></div><div className="map-filters"><label>Building<select value={building} onChange={(event) => { setSelectedBuilding(event.target.value); setSelectedFloor(""); }}>{buildings.map((name) => <option key={name} value={name}>{name}</option>)}</select></label><label>Floor<select value={floor} onChange={(event) => setSelectedFloor(event.target.value)}>{floors.map((value) => <option key={value} value={value}>{value === 0 ? "Ground floor" : `Floor ${value}`}</option>)}</select></label></div></div><FloorMap snapshots={mapData} /></section><section className="room-grid" aria-label="Rooms">{data.map(({ room, occupancy }) => <RoomCard key={room.room_id} room={room} occupancy={occupancy} />)}</section></>;
}
