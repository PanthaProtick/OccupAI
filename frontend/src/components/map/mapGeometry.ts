import type { RoomSnapshot } from "../../hooks/useDashboard";
import { sortRoomsByNumber } from "../rooms/roomBlocks";

export type MapRoom = RoomSnapshot & {
  x: number;
  y: number;
  width: number;
  height: number;
};

type Geometry = Pick<MapRoom, "x" | "y" | "width" | "height">;

const groundFloorLayout: Record<string, Geometry> = {
  room_tt_ground: { x: 36, y: 92, width: 220, height: 270 },
  room_teachers_canteen: { x: 36, y: 376, width: 220, height: 100 },
  room_canteen: { x: 270, y: 376, width: 500, height: 100 },
  room_girls_common: { x: 770, y: 195, width: 170, height: 160 },
};

const firstFloorLayout: Record<string, Geometry> = {
  "Study Room": { x: 36, y: 280, width: 220, height: 196 },
  Library: { x: 270, y: 280, width: 500, height: 196 },
  "1A03": { x: 770, y: 52, width: 170, height: 80 },
  "1A04": { x: 770, y: 132, width: 170, height: 80 },
  "1A05": { x: 770, y: 212, width: 170, height: 80 },
  "1A06": { x: 770, y: 292, width: 170, height: 80 },
  "1A07": { x: 770, y: 372, width: 170, height: 80 },
};

function upperFloorGeometry(name: string): Geometry | undefined {
  const match = /^(\d)([ABC])0([1-8])$/.exec(name);
  if (!match) return undefined;
  const [, , wing, roomText] = match;
  const room = Number(roomText);
  if (wing === "C" && room >= 3 && room <= 7) return { x: 36, y: 52 + (room - 3) * 80, width: 180, height: 80 };
  if (wing === "A" && room >= 3 && room <= 7) return { x: 764, y: 52 + (room - 3) * 80, width: 180, height: 80 };
  if (wing === "B") {
    const sequence = room % 2 === 0 ? [8, 6, 4, 2] : [7, 5, 3, 1];
    const column = sequence.indexOf(room);
    if (column >= 0) return { x: 216 + column * 137, y: room % 2 === 0 ? 372 : 452, width: 137, height: 80 };
  }
  return undefined;
}

export function getMapRooms(snapshots: RoomSnapshot[]): MapRoom[] {
  const fallback = (index: number) => ({ x: 36 + (index % 4) * 190, y: 92 + Math.floor(index / 4) * 100, width: 176, height: 86 });
  return [...snapshots].sort(sortRoomsByNumber).map((snapshot, index) => ({
    ...snapshot,
    ...(groundFloorLayout[snapshot.room.room_id]
      ?? firstFloorLayout[snapshot.room.name]
      ?? upperFloorGeometry(snapshot.room.name)
      ?? fallback(index)),
  }));
}

export function occupancyLevel(snapshot: RoomSnapshot): "unknown" | "low" | "medium" | "high" {
  const value = snapshot.occupancy.occupancy_percentage;
  if (value === null || snapshot.occupancy.status !== "online") return "unknown";
  if (value >= 80) return "high";
  if (value >= 40) return "medium";
  return "low";
}
