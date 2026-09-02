import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const mockDir = path.join(root, "mock", "generated");
const examplesDir = path.join(root, "contracts", "examples");
const generatedAt = "2026-09-01T13:00:00Z";

const rooms = [
  { room_id: "room_tt_ground", name: "T.T. Ground", capacity: 150, building: "University Building", floor: 0, camera_id: "cam_001", behavior_profile: "study_room" },
  { room_id: "room_teachers_canteen", name: "Teacher's Canteen", capacity: 40, building: "University Building", floor: 0, camera_id: "cam_002", behavior_profile: "canteen" },
  { room_id: "room_canteen", name: "Canteen", capacity: 120, building: "University Building", floor: 0, camera_id: "cam_003", behavior_profile: "canteen" },
  { room_id: "room_girls_common", name: "Girls' Common Room", capacity: 60, building: "University Building", floor: 0, camera_id: "cam_004", behavior_profile: "study_room" },
];

function addRoom(name, floor, capacity = 40, behavior_profile = "classroom") {
  const number = rooms.length + 1;
  rooms.push({
    room_id: `room_${name.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "")}`,
    name, capacity, building: "University Building", floor,
    camera_id: `cam_${String(number).padStart(3, "0")}`, behavior_profile,
  });
}

for (const [name, capacity, profile] of [
  ["Study Room", 80, "study_room"], ["Library", 200, "study_room"],
  ["1A03", 40, "classroom"], ["1A04", 40, "classroom"], ["1A05", 40, "classroom"],
  ["1A06", 40, "classroom"], ["1A07", 40, "classroom"],
]) addRoom(name, 1, capacity, profile);

for (let floor = 2; floor <= 9; floor += 1) {
  for (const wing of ["C", "A"]) for (let room = 3; room <= 7; room += 1) addRoom(`${floor}${wing}0${room}`, floor);
  for (const room of [8, 6, 4, 2, 7, 5, 3, 1]) addRoom(`${floor}B${String(room).padStart(2, "0")}`, floor);
}

if (rooms.length !== 155) throw new Error(`Expected 155 rooms, generated ${rooms.length}`);

const existingLive = [
  { camera_id: "cam_001", occupancy: 48, updated_at: generatedAt, status: "online" },
  { camera_id: "cam_002", occupancy: 28, updated_at: generatedAt, status: "online" },
  { camera_id: "cam_003", occupancy: 96, updated_at: "2026-09-01T12:49:00Z", status: "stale" },
  { camera_id: "cam_004", occupancy: 12, updated_at: generatedAt, status: "online" },
];
const existingByCamera = new Map(existingLive.map((item) => [item.camera_id, item]));
const cameras = rooms.map((room) => existingByCamera.get(room.camera_id) ?? {
  camera_id: room.camera_id, occupancy: 0, updated_at: generatedAt, status: "offline",
});

const historyPath = path.join(mockDir, "historical_api_views.json");
const history = JSON.parse(fs.readFileSync(historyPath, "utf8"));
for (const range of ["hour", "day", "week"]) {
  for (const room of rooms) history.views.range[range][room.room_id] ??= { metric: { occupancy: [], percentage: [] } };
}

const occupancy = rooms.map((room) => {
  const item = existingByCamera.get(room.camera_id);
  const raw = item?.occupancy ?? 0;
  const status = item?.status ?? "offline";
  const value = status === "offline" ? null : raw;
  return {
    camera_id: room.camera_id, room_id: room.room_id, occupancy: value, raw_occupancy: raw,
    capacity: room.capacity, occupancy_percentage: value === null ? null : Math.min(100, Number((value / room.capacity * 100).toFixed(2))),
    status, updated_at: item?.updated_at ?? generatedAt,
  };
});

const write = (target, value) => fs.writeFileSync(target, `${JSON.stringify(value, null, 2)}\n`);
write(path.join(mockDir, "rooms.json"), { generated_at: generatedAt, seed: 42, rooms });
write(path.join(mockDir, "live_occupancy.json"), { cameras });
write(historyPath, history);
write(path.join(examplesDir, "rooms.json"), { data: rooms, meta: { count: rooms.length, generated_at: generatedAt } });
write(path.join(examplesDir, "occupancy.json"), { data: occupancy, meta: { count: occupancy.length, generated_at: generatedAt } });

console.log(`Generated ${rooms.length} room and occupancy records across floors 0-9.`);
