import type { RoomSnapshot } from "../../hooks/useDashboard";

export type BuildingBlock = "C" | "B" | "A";
export const BUILDING_BLOCKS: BuildingBlock[] = ["C", "B", "A"];

const collator = new Intl.Collator(undefined, { numeric: true, sensitivity: "base" });

export function roomBlock(snapshot: RoomSnapshot): BuildingBlock {
  const name = snapshot.room.name.trim();
  const coded = /^\d+([ABC])\d+$/i.exec(name);
  if (coded) return coded[1].toUpperCase() as BuildingBlock;
  if (snapshot.room.room_id === "room_tt_ground" || snapshot.room.room_id === "room_teachers_canteen" || name === "Study Room") return "C";
  if (snapshot.room.room_id === "room_girls_common" || /^\d+A/i.test(name)) return "A";
  return "B";
}

export function sortRoomsByNumber(a: RoomSnapshot, b: RoomSnapshot) {
  return collator.compare(a.room.name, b.room.name);
}

export function groupRoomsByBlock(snapshots: RoomSnapshot[]) {
  return BUILDING_BLOCKS.map(block => ({
    block,
    rooms: snapshots.filter(snapshot => roomBlock(snapshot) === block).sort(sortRoomsByNumber),
  }));
}
