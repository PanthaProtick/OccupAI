import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowRight, MapPin } from "lucide-react";
import type { Occupancy, Room } from "../../api/types";
import { formatTimestamp } from "../../utils/formatters";
import { OccupancyReading } from "../occupancy/OccupancyReading";
import { StatusBadge } from "../occupancy/StatusBadge";

export function RoomCard({ room, occupancy, index = 0 }: { room: Room; occupancy: Occupancy; index?: number }) {
  return (
    <motion.article 
      className="room-card"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: index * 0.1, ease: [0.2, 0.8, 0.2, 1] }}
      whileHover={{ y: -8, scale: 1.02 }}
    >
      <div className="room-card__top">
        <div>
          <p className="room-card__place" style={{ display: "flex", alignItems: "center", gap: "0.25rem" }}>
            <MapPin size={14} /> {room.building} · Floor {room.floor}
          </p>
          <h2>{room.name}</h2>
        </div>
        <StatusBadge status={occupancy.status} />
      </div>
      <OccupancyReading data={occupancy} />
      <div className="room-card__footer">
        <span>Updated {formatTimestamp(occupancy.updated_at)}</span>
        <Link aria-label={`View ${room.name}`} to={`/rooms/${room.room_id}`} style={{ display: "flex", alignItems: "center", gap: "0.25rem" }}>
          View room <ArrowRight size={16} aria-hidden="true" />
        </Link>
      </div>
    </motion.article>
  );
}
