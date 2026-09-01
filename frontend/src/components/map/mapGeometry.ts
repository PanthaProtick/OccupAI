import type { RoomSnapshot } from "../../hooks/useDashboard";

export type MapRoom = RoomSnapshot & {
  x: number;
  y: number;
  width: number;
  height: number;
};

export function getMapRooms(snapshots: RoomSnapshot[]): MapRoom[] {
  const groundFloorLayout: Record<string, Pick<MapRoom, "x" | "y" | "width" | "height">> = {
    room_tt_ground: { x: 36, y: 92, width: 220, height: 270 },
    room_teachers_canteen: { x: 36, y: 376, width: 220, height: 100 },
    room_canteen: { x: 270, y: 376, width: 500, height: 100 },
    room_girls_common: { x: 770, y: 195, width: 170, height: 160 },
  };
  const fallback = (index: number) => ({ x: 36 + (index % 4) * 190, y: 92 + Math.floor(index / 4) * 100, width: 176, height: 86 });
  return snapshots.map((snapshot, index) => ({ ...snapshot, ...(groundFloorLayout[snapshot.room.room_id] ?? fallback(index)) }));
}

export function occupancyLevel(snapshot: RoomSnapshot): "unknown" | "low" | "medium" | "high" {
  const value = snapshot.occupancy.occupancy_percentage;
  if (value === null || snapshot.occupancy.status !== "online") return "unknown";
  if (value >= 80) return "high";
  if (value >= 40) return "medium";
  return "low";
}
