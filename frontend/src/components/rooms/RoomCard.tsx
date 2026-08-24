import { Link } from "react-router-dom";
import type { Occupancy, Room } from "../../api/types";
import { formatTimestamp } from "../../utils/formatters";
import { OccupancyReading } from "../occupancy/OccupancyReading";
import { StatusBadge } from "../occupancy/StatusBadge";
export function RoomCard({ room, occupancy }: { room: Room; occupancy: Occupancy }) {
  return <article className="room-card"><div className="room-card__top"><div><p className="room-card__place">{room.building} · Floor {room.floor}</p><h2>{room.name}</h2></div><StatusBadge status={occupancy.status} /></div><OccupancyReading data={occupancy} /><div className="room-card__footer"><span>Updated {formatTimestamp(occupancy.updated_at)}</span><Link aria-label={`View ${room.name}`} to={`/rooms/${room.room_id}`}>View room <span aria-hidden="true">→</span></Link></div></article>;
}
