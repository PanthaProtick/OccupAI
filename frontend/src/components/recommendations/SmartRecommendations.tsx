import { motion } from "framer-motion";
import { Sparkles, Flame, Coffee } from "lucide-react";
import { RoomCard } from "../rooms/RoomCard";
import type { Room, Occupancy } from "../../api/types";

interface Props {
  data: { room: Room; occupancy: Occupancy }[];
}

export function SmartRecommendations({ data }: Props) {
  // Only consider online rooms with valid data
  const validRooms = data.filter(
    (item) => item.occupancy.status === "online" && item.occupancy.occupancy !== null
  );

  if (validRooms.length < 2) return null;

  // Sort by occupancy percentage
  const sortedRooms = [...validRooms].sort(
    (a, b) => (a.occupancy.occupancy_percentage || 0) - (b.occupancy.occupancy_percentage || 0)
  );

  // Quiet / Available rooms (lowest occupancy)
  const quietRooms = sortedRooms.slice(0, 2);

  // Crowded / High Activity rooms (highest occupancy)
  const crowdedRooms = sortedRooms.slice().reverse().slice(0, 2);

  return (
    <motion.section
      className="recommendations-panel"
      aria-labelledby="recommendations-heading"
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: false, amount: 0.15 }}
      transition={{ duration: 0.7, delay: 0.1, ease: [0.2, 0.8, 0.2, 1] }}
      style={{ marginTop: "4rem" }}
    >
      <div className="section-heading" style={{ marginBottom: "1.5rem" }}>
        <div>
          <p className="eyebrow"><Sparkles size={14} /> Smart Suggestions</p>
          <h2 id="recommendations-heading">Where to go right now</h2>
          <p>Live recommendations based on current campus activity.</p>
        </div>
      </div>

      <div className="recommendations-grid">
        <div className="recommendation-group">
          <h3 className="recommendation-title">
            <Coffee size={18} className="text-accent" /> Available & Quiet
          </h3>
          <p className="recommendation-desc">Plenty of space to focus or hold a meeting.</p>
          <div className="room-grid" style={{ marginTop: "1rem" }}>
            {quietRooms.map(({ room, occupancy }, i) => (
              <RoomCard key={`quiet-${room.room_id}`} room={room} occupancy={occupancy} index={i} />
            ))}
          </div>
        </div>

        <div className="recommendation-group">
          <h3 className="recommendation-title">
            <Flame size={18} className="text-high" /> High Activity
          </h3>
          <p className="recommendation-desc">These spaces are currently very crowded.</p>
          <div className="room-grid" style={{ marginTop: "1rem" }}>
            {crowdedRooms.map(({ room, occupancy }, i) => (
              <RoomCard key={`crowded-${room.room_id}`} room={room} occupancy={occupancy} index={i} />
            ))}
          </div>
        </div>
      </div>
    </motion.section>
  );
}
