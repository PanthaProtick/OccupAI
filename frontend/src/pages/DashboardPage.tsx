import { EmptyState } from "../components/feedback/EmptyState";
import { ErrorState } from "../components/feedback/ErrorState";
import { LoadingState } from "../components/feedback/LoadingState";
import { RoomCard } from "../components/rooms/RoomCard";
import { FloorMap } from "../components/map/FloorMap";
import { useDashboard } from "../hooks/useDashboard";
import { formatTimestamp } from "../utils/formatters";
import { useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { motion, type Variants } from "framer-motion";
import { Activity, Building2, DoorOpen, Gauge, RefreshCw, Sparkles, TrendingUp, Users } from "lucide-react";
import { SmartRecommendations } from "../components/recommendations/SmartRecommendations";

const textVariants: Variants = {
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
  const allData = data ?? [];
  const buildings = useMemo(() => [...new Set(allData.map(({ room }) => room.building))].sort(), [data]);
  const building = selectedBuilding || buildings[0];
  const floors = useMemo(() => [...new Set((data ?? []).filter(({ room }) => room.building === building).map(({ room }) => room.floor))].sort((a, b) => a - b), [data, building]);
  const floor = selectedFloor === "" || !floors.includes(Number(selectedFloor)) ? floors[0] : Number(selectedFloor);
  const mapData = allData.filter(({ room }) => room.building === building && room.floor === floor);
  const liveRooms = mapData.filter(({ occupancy }) => occupancy.status === "online" && occupancy.occupancy !== null);
  const allLiveRooms = allData.filter(({ occupancy }) => occupancy.status === "online" && occupancy.occupancy !== null);
  const people = allLiveRooms.reduce((total, { occupancy }) => total + (occupancy.occupancy ?? 0), 0);
  const capacity = allData.reduce((total, { room }) => total + room.capacity, 0);
  const average = capacity ? Math.round((people / capacity) * 100) : 0;
  const availableRooms = allLiveRooms.filter(({ occupancy }) => (occupancy.occupancy_percentage ?? 100) < 40).length;
  const busiestRoom = [...liveRooms].sort((a, b) => (b.occupancy.occupancy_percentage ?? -1) - (a.occupancy.occupancy_percentage ?? -1))[0];
  const quietestRoom = [...liveRooms].sort((a, b) => (a.occupancy.occupancy_percentage ?? 101) - (b.occupancy.occupancy_percentage ?? 101))[0];
  const summary = [
    { label: "Campus occupancy", value: people.toLocaleString(), detail: `Across ${allLiveRooms.length} live rooms`, icon: Users },
    { label: "Space utilization", value: `${average}%`, detail: `${capacity.toLocaleString()} total capacity`, icon: Gauge },
    { label: "Available now", value: availableRooms.toString(), detail: "Rooms below 40%", icon: DoorOpen },
    { label: "Live coverage", value: `${allLiveRooms.length}/${allData.length}`, detail: `${allData.length - allLiveRooms.length} feeds need attention`, icon: Activity }
  ];

  if (!data && isRefreshing) return <LoadingState label="Loading room occupancy" />;
  if (!data && error) return <ErrorState message={error} onRetry={() => void refresh()} />;
  if (!data?.length) return <EmptyState title="No rooms found" message="The API did not return any configured rooms." />;

  return (
    <>
      <motion.section
        id="overview"
        className="dashboard-heading"
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: false, amount: .2 }}
        transition={{ duration: 0.8 }}
      >
        <div>
          <motion.p custom={0} variants={textVariants} initial="hidden" whileInView="visible" viewport={{once:false}} className="eyebrow"><span className="live-pulse" /> Live campus intelligence</motion.p>
          <motion.h1 custom={1} variants={textVariants} initial="hidden" whileInView="visible" viewport={{once:false}}>
            See how your campus is moving.
          </motion.h1>
          <motion.p custom={2} variants={textVariants} initial="hidden" whileInView="visible" viewport={{once:false}}>
            Live room activity, capacity pressure, and availability in one clear view.
          </motion.p>
        </div>
        <motion.div className="refresh" custom={3} variants={textVariants} initial="hidden" whileInView="visible" viewport={{once:false}}>
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

      <section className="summary-grid" aria-label="Floor summary">
        {summary.map(({ label, value, detail, icon: Icon }, index) => (
          <motion.div className="summary-card" key={label} initial={{ opacity: 0, y: 28 }} whileInView={{ opacity: 1, y: 0 }} viewport={{once:false,amount:.2}} transition={{ delay: index * .07 }}>
            <span className="summary-card__icon"><Icon size={19} /></span>
            <div><p>{label}</p><strong>{value}</strong><span>{detail}</span></div>
          </motion.div>
        ))}
      </section>

      <motion.aside className="insight-banner" initial={{ opacity: 0, y: 18 }} whileInView={{ opacity: 1, y: 0 }} viewport={{once:false,amount:.25}} transition={{ duration:.6 }} aria-label="Live floor insight">
        <span className="insight-banner__mark"><Sparkles size={20} /></span>
        <div><span>Live insight · {floor === 0 ? "Ground floor" : `Floor ${floor}`}</span><strong>{quietestRoom ? `${quietestRoom.room.name} is the best available space right now.` : "Waiting for live room readings."}</strong></div>
        {busiestRoom && <div className="insight-banner__signal"><TrendingUp size={18} /><span><strong>{busiestRoom.room.name}</strong>{busiestRoom.occupancy.occupancy_percentage}% occupied</span></div>}
      </motion.aside>


      <motion.section
        id="floor-map"
        className="map-panel"
        aria-labelledby="map-heading"
        initial={{ opacity: 0, scale: 0.95 }}
        whileInView={{ opacity: 1, scale: 1 }}
        viewport={{ once: false, amount: .12 }}
        transition={{ duration: 0.7, delay: 0.2, ease: [0.2, 0.8, 0.2, 1] }}
      >
        <div className="section-heading">
          <div>
            <p className="eyebrow"><Building2 size={14} /> Building explorer</p>
            <h2 id="map-heading">Floor map</h2>
            <p>Select a room to inspect its latest reading and history.</p>
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


      <div className="room-section-heading" id="rooms"><div><p className="eyebrow">Room directory</p><h2>Spaces on this floor</h2></div><span>{mapData.length} rooms</span></div>
      <section className="room-grid" aria-label="Rooms">
        {mapData.map(({ room, occupancy }, i) => (
          <RoomCard key={room.room_id} room={room} occupancy={occupancy} index={i} />
        ))}
      </section>

      <SmartRecommendations data={mapData} />
    </>
  );
}
