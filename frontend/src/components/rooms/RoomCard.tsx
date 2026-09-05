import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowUpRight, MapPin, Users } from "lucide-react";
import type { Occupancy, Room } from "../../api/types";
import { formatTimestamp } from "../../utils/formatters";
import { OccupancyReading } from "../occupancy/OccupancyReading";
import { StatusBadge } from "../occupancy/StatusBadge";

export function RoomCard({ room, occupancy, index = 0 }: { room: Room; occupancy: Occupancy; index?: number }) {
  return (
    <motion.article
      className="room-card"
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0, scale: 1 }}
      viewport={{ once: false, amount: .18 }}
      transition={{ duration: 0.55, delay: Math.min(index * 0.045, .35), ease: [0.2, 0.8, 0.2, 1] }}
      whileHover={{ y: -7 }}
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
      <div className="room-card__meter" aria-hidden="true"><span style={{ width: `${Math.min(occupancy.occupancy_percentage ?? 0, 100)}%` }} /></div>
      <div className="room-card__footer">
        <span><Users size={14} /> Capacity {room.capacity}</span>
        <Link aria-label={`View ${room.name}`} to={`/rooms/${room.room_id}`} style={{ display: "flex", alignItems: "center", gap: "0.25rem" }}>
          Explore <ArrowUpRight size={16} aria-hidden="true" />
        </Link>
      </div>
      <time className="room-card__updated" dateTime={occupancy.updated_at}>Updated {formatTimestamp(occupancy.updated_at)}</time>
    </motion.article>
  );
}
