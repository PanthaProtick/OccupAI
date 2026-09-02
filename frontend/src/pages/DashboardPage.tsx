import { EmptyState } from "../components/feedback/EmptyState";
import { ErrorState } from "../components/feedback/ErrorState";
import { LoadingState } from "../components/feedback/LoadingState";
import { RoomCard } from "../components/rooms/RoomCard";
import { FloorMap } from "../components/map/FloorMap";
import { useDashboard } from "../hooks/useDashboard";
import { formatTimestamp } from "../utils/formatters";
import { useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { motion } from "framer-motion";
import { RefreshCw } from "lucide-react";

const textVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.1, duration: 0.8, ease: [0.2, 0.6, 0.2, 1] }
  })
};

export function DashboardPage() {
  const { data, error, isRefreshing, lastRefresh, refresh } = useDashboard();
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedBuilding = searchParams.get("building") ?? "";
  const selectedFloor = searchParams.get("floor") ?? "";
  const buildings = useMemo(() => [...new Set((data ?? []).map(({ room }) => room.building))].sort(), [data]);
  const building = selectedBuilding || buildings[0];
  const floors = useMemo(() => [...new Set((data ?? []).filter(({ room }) => room.building === building).map(({ room }) => room.floor))].sort((a, b) => a - b), [data, building]);
  const floor = selectedFloor === "" || !floors.includes(Number(selectedFloor)) ? floors[0] : Number(selectedFloor);
  const mapData = (data ?? []).filter(({ room }) => room.building === building && room.floor === floor);

  if (!data && isRefreshing) return <LoadingState label="Loading room occupancy" />;
  if (!data && error) return <ErrorState message={error} onRetry={() => void refresh()} />;
  if (!data?.length) return <EmptyState title="No rooms found" message="The API did not return any configured rooms." />;

  return (
    <>
      <motion.section
        className="dashboard-heading"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.8 }}
      >
        <div>
          <motion.p custom={0} variants={textVariants} initial="hidden" animate="visible" className="eyebrow">
            Live space intelligence
          </motion.p>
          <motion.h1 custom={1} variants={textVariants} initial="hidden" animate="visible">
            Room overview
          </motion.h1>
          <motion.p custom={2} variants={textVariants} initial="hidden" animate="visible">
            Current occupancy across campus spaces.
          </motion.p>
        </div>
        <motion.div className="refresh" custom={3} variants={textVariants} initial="hidden" animate="visible">
          <motion.button
            whileHover={{ scale: 1.05, boxShadow: "0 10px 30px rgba(217, 70, 239, 0.5)" }}
            whileTap={{ scale: 0.95 }}
            className="button"
            onClick={() => void refresh()}
            disabled={isRefreshing}
            style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}
          >
            <RefreshCw size={16} className={isRefreshing ? "spin" : ""} /> {isRefreshing ? "Refreshing…" : "Refresh"}
          </motion.button>
          {lastRefresh && <span>Last refreshed {formatTimestamp(lastRefresh)}</span>}
        </motion.div>
      </motion.section>

      {error && (
        <div className="warning" role="status">
          Showing the last successful update. {error} <button onClick={() => void refresh()}>Retry</button>
        </div>
      )}

      <motion.section
        className="map-panel"
        aria-labelledby="map-heading"
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.7, delay: 0.2, ease: [0.2, 0.8, 0.2, 1] }}
      >
        <div className="section-heading">
          <div>
            <p className="eyebrow">Explore the building</p>
            <h2 id="map-heading">Floor map</h2>
            <p>Choose a floor to see its rooms and live occupancy.</p>
          </div>
          <div className="map-filters">
            <label>
              Building
              <select value={building} onChange={(event) => setSearchParams({ building: event.target.value, floor: "0" })}>
                {buildings.map((name) => (
                  <option key={name} value={name}>
                    {name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Floor
              <select value={floor} onChange={(event) => setSearchParams({ building, floor: event.target.value })}>
                {floors.map((value) => (
                  <option key={value} value={value}>
                    {value === 0 ? "Ground floor" : `Floor ${value}`}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </div>
        <FloorMap snapshots={mapData} />
      </motion.section>

      <section className="room-grid" aria-label="Rooms">
        {mapData.map(({ room, occupancy }, i) => (
          <RoomCard key={room.room_id} room={room} occupancy={occupancy} index={i} />
        ))}
      </section>
    </>
  );
}
