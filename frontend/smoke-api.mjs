const baseUrl = (process.argv[2] ?? "http://127.0.0.1:8000").replace(/\/$/, "");

async function get(path) {
  const response = await fetch(`${baseUrl}${path}`, {
    headers: { Accept: "application/json", "X-Request-ID": "frontend-smoke" },
  });
  if (!response.ok) throw new Error(`${path} returned ${response.status}`);
  if (response.headers.get("x-request-id") !== "frontend-smoke") {
    throw new Error(`${path} did not preserve the request ID`);
  }
  return response.json();
}

const [rooms, occupancy, history] = await Promise.all([
  get("/api/rooms"),
  get("/api/occupancy"),
  get("/api/history?room_id=room_cse_201&range=day&metric=percentage"),
]);

const roomIds = new Set(rooms.data.map((room) => room.room_id));
const cameraIds = new Set(rooms.data.map((room) => room.camera_id));
if (rooms.meta.count !== 7 || roomIds.size !== 7 || cameraIds.size !== 7) {
  throw new Error("rooms response does not contain seven canonical mappings");
}
if (occupancy.meta.count !== 7 || occupancy.data.length !== 7) {
  throw new Error("occupancy response does not contain seven camera states");
}
for (const item of occupancy.data) {
  if (!cameraIds.has(item.camera_id) || !roomIds.has(item.room_id)) {
    throw new Error("occupancy response contains an unknown mapping");
  }
  if (!["online", "stale", "offline"].includes(item.status)) {
    throw new Error("occupancy response contains an unknown status");
  }
  if (item.occupancy_percentage != null && item.occupancy_percentage > 100) {
    throw new Error("occupancy percentage is not capped");
  }
}
if (history.meta.room_id !== "room_cse_201" || history.meta.metric !== "percentage") {
  throw new Error("history metadata does not match the query");
}
if (!history.data.every((point, index, values) =>
  point.coverage_percentage >= 0 && point.coverage_percentage <= 100 &&
  (index === 0 || values[index - 1].bucket_start < point.bucket_start))) {
  throw new Error("history points are invalid or unordered");
}

console.log(`Frontend smoke passed: rooms=${rooms.meta.count} occupancy=${occupancy.meta.count} history=${history.meta.count}`);
