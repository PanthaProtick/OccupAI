import { describe, expect, it } from "vitest";
import roomsPayload from "../../../../contracts/examples/rooms.json";
import occupancyPayload from "../../../../contracts/examples/occupancy.json";
import type { RoomSnapshot } from "../../hooks/useDashboard";
import { getMapRooms } from "./mapGeometry";

const occupancyByCamera = new Map(occupancyPayload.data.map((item) => [item.camera_id, item]));
const snapshots = roomsPayload.data.map((room) => ({
  room,
  occupancy: occupancyByCamera.get(room.camera_id),
})) as RoomSnapshot[];

describe("floor-plan geometry", () => {
  it.each([
    [0, 4], [1, 7], [2, 18], [3, 18], [4, 18],
    [5, 18], [6, 18], [7, 18], [8, 18], [9, 18],
  ])("maps every room on floor %i to a unique plan position", (floor, expectedCount) => {
    const mapped = getMapRooms(snapshots.filter((snapshot) => snapshot.room.floor === floor));
    expect(mapped).toHaveLength(expectedCount);
    expect(new Set(mapped.map(({ x, y }) => `${x},${y}`)).size).toBe(expectedCount);
  });

  it("uses the supplied A, B, and C wing arrangement", () => {
    const floor = getMapRooms(snapshots.filter((snapshot) => snapshot.room.floor === 9));
    const byName = new Map(floor.map((room) => [room.room.name, room]));
    expect(byName.get("9C03")).toMatchObject({ x: 36, y: 52 });
    expect(byName.get("9A07")).toMatchObject({ x: 764, y: 372 });
    expect(byName.get("9B08")).toMatchObject({ x: 216, y: 372 });
    expect(byName.get("9B01")).toMatchObject({ x: 627, y: 452 });
  });
});
