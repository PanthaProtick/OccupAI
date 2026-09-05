import { Link } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowUpRight, Radio, Users } from "lucide-react";
import { useState } from "react";
import { formatTimestamp } from "../../utils/formatters";
import type { RoomSnapshot } from "../../hooks/useDashboard";
import { getMapRooms, occupancyLevel } from "./mapGeometry";
import { groupRoomsByBlock } from "../rooms/roomBlocks";

function occupancyLabel(snapshot: RoomSnapshot) {
  const { occupancy } = snapshot;
  if (occupancy.occupancy_percentage === null) return "Occupancy unavailable";
  return `${occupancy.occupancy_percentage}% occupied`;
}

function compactMapLabel(snapshot: RoomSnapshot) {
  return snapshot.occupancy.occupancy_percentage === null
    ? "Unavailable"
    : `${snapshot.occupancy.occupancy_percentage}% occupied`;
}

export function FloorMap({ snapshots }: { snapshots: RoomSnapshot[] }) {
  const mapRooms = getMapRooms(snapshots);
  const floor = snapshots[0]?.room.floor;
  const height = 600;
  const [activeRoomId, setActiveRoomId] = useState<string | null>(null);
  const activeRoom = mapRooms.find(({ room }) => room.room_id === activeRoomId);
  const roomBlocks = groupRoomsByBlock(mapRooms);

  return (
    <div className="floor-map">
      <div className="floor-map__notice" role="note">
        <span className="floor-map__notice-icon"><Radio size={17} /></span>
        <span><strong>{floor === 0 ? "Ground floor" : `Floor ${floor}`} live view</strong><small>Readings update from the latest available camera data.</small></span>
      </div>
      <div className="floor-map__canvas">
        <AnimatePresence>
        {activeRoom && <motion.div key={activeRoom.room.room_id} className="map-preview" initial={{ opacity: 0, y: -8, scale: .96 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: -6, scale: .97 }} transition={{ duration: .2 }}>
          <div className="map-preview__top"><span className={`map-preview__status map-preview__status--${activeRoom.occupancy.status}`} />{activeRoom.occupancy.status} · live preview</div>
          <strong>{activeRoom.room.name}</strong>
          <div className="map-preview__reading"><Users size={18}/><b>{activeRoom.occupancy.occupancy ?? "—"}</b><span>of {activeRoom.room.capacity}<small>{compactMapLabel(activeRoom)}</small></span></div>
          <div className="map-preview__bar"><span style={{ width: `${Math.min(activeRoom.occupancy.occupancy_percentage ?? 0, 100)}%` }}/></div>
          <time dateTime={activeRoom.occupancy.updated_at}>Updated {formatTimestamp(activeRoom.occupancy.updated_at)}</time>
          <span className="map-preview__hint">Click the highlighted room for analytics <ArrowUpRight size={15}/></span>
        </motion.div>}
        </AnimatePresence>
        <svg className="floor-map__svg" viewBox={`0 0 980 ${height}`} role="img" aria-labelledby="floor-map-title floor-map-description">
          <title id="floor-map-title">Interactive room occupancy map</title>
          <desc id="floor-map-description">Select a room to view its live occupancy details. Room positions follow the supplied floor plan.</desc>
          <rect className="floor-map__circulation" x="20" y="20" width="940" height={height - 40} rx="24" />
          <text className="floor-map__circulation-label" x="490" y="65" textAnchor="middle">Central circulation / connecting block</text>
          <text className="floor-map__circulation-metric" x="490" y="105" textAnchor="middle">{mapRooms.length} monitored spaces</text>
          <text className="floor-map__block-label" x="126" y="42" textAnchor="middle">C BLOCK</text>
          <text className="floor-map__block-label" x="490" y="145" textAnchor="middle">B BLOCK</text>
          <text className="floor-map__block-label" x="854" y="42" textAnchor="middle">A BLOCK</text>
          {mapRooms.map((mapRoom) => {
            const level = occupancyLevel(mapRoom);
            return (
              <Link
                key={mapRoom.room.room_id}
                to={`/rooms/${mapRoom.room.room_id}`}
                aria-label={`${mapRoom.room.name}, ${occupancyLabel(mapRoom)}`}
                className={`floor-map__room floor-map__room--${level}${activeRoomId === mapRoom.room.room_id ? " floor-map__room--active" : ""}`}
                onMouseEnter={() => setActiveRoomId(mapRoom.room.room_id)}
                onMouseLeave={() => setActiveRoomId(null)}
                onFocus={() => setActiveRoomId(mapRoom.room.room_id)}
                onBlur={() => setActiveRoomId(null)}
              >
                <rect x={mapRoom.x} y={mapRoom.y} width={mapRoom.width} height={mapRoom.height} rx="12" />
                {mapRoom.occupancy.status === "online" && <circle className="floor-map__room-live" cx={mapRoom.x + 16} cy={mapRoom.y + 16} r="5" />}
                <text className="floor-map__room-name" x={mapRoom.x + mapRoom.width / 2} y={mapRoom.y + 34} textAnchor="middle">{mapRoom.room.name}</text>
                <text className="floor-map__room-value" x={mapRoom.x + mapRoom.width / 2} y={mapRoom.y + 59} textAnchor="middle">{compactMapLabel(mapRoom)}</text>
              </Link>
            );
          })}
        </svg>
      </div>
      <div className="floor-map__legend" aria-label="Map legend">
        <span><i className="legend-swatch legend-swatch--low" /> Low occupancy</span>
        <span><i className="legend-swatch legend-swatch--medium" /> Moderate occupancy</span>
        <span><i className="legend-swatch legend-swatch--high" /> High occupancy</span>
        <span><i className="legend-swatch legend-swatch--unknown" /> Unavailable or offline</span>
      </div>
      <div className="floor-map__list" aria-label="Rooms on this floor">
        {roomBlocks.map(({block,rooms})=><section className="floor-map__list-block" aria-labelledby={`map-list-${block}`} key={block}><h3 id={`map-list-${block}`}>{block} Block <span>{rooms.length}</span></h3>{rooms.map(({ room, occupancy }, index) => <motion.div key={room.room_id} initial={{ opacity: 0, y: 18 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: false, amount: .2 }} transition={{ delay: Math.min(index * .035, .3) }}><Link to={`/rooms/${room.room_id}`}><span>{room.name}<small>Capacity {room.capacity}</small></span><span>{occupancyLabel({ room, occupancy })}<ArrowUpRight size={15} /></span></Link></motion.div>)}</section>)}
      </div>
    </div>
  );
}
