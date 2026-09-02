import { Link } from "react-router-dom";
import type { RoomSnapshot } from "../../hooks/useDashboard";
import { getMapRooms, occupancyLevel } from "./mapGeometry";

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

  return (
    <div className="floor-map">
      <div className="floor-map__notice" role="note">
        <strong>{floor === 0 ? "Ground floor" : `Floor ${floor}`} plan</strong>
        <span>Room arrangement follows the supplied university building floor diagrams.</span>
      </div>
      <div className="floor-map__canvas">
        <svg className="floor-map__svg" viewBox={`0 0 980 ${height}`} role="img" aria-labelledby="floor-map-title floor-map-description">
          <title id="floor-map-title">Interactive room occupancy map</title>
          <desc id="floor-map-description">Select a room to view its live occupancy details. Room positions follow the supplied floor plan.</desc>
          <rect className="floor-map__circulation" x="20" y="20" width="940" height={height - 40} rx="24" />
          <text className="floor-map__circulation-label" x="490" y="65" textAnchor="middle">Central circulation / connecting block</text>
          {mapRooms.map((mapRoom) => {
            const level = occupancyLevel(mapRoom);
            return (
              <Link
                key={mapRoom.room.room_id}
                to={`/rooms/${mapRoom.room.room_id}`}
                aria-label={`${mapRoom.room.name}, ${occupancyLabel(mapRoom)}`}
                className={`floor-map__room floor-map__room--${level}`}
              >
                <rect x={mapRoom.x} y={mapRoom.y} width={mapRoom.width} height={mapRoom.height} rx="12" />
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
        {mapRooms.map(({ room, occupancy }) => <Link key={room.room_id} to={`/rooms/${room.room_id}`}><span>{room.name}</span><span>{occupancyLabel({ room, occupancy })}</span></Link>)}
      </div>
    </div>
  );
}
