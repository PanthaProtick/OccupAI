import { afterEach, describe, expect, it, vi } from "vitest";
import rooms from "../../../contracts/examples/rooms.json";
import notFound from "../../../contracts/examples/not-found-error.json";
import validationError from "../../../contracts/examples/validation-error.json";
import { api, ApiError } from "./client";

afterEach(() => vi.unstubAllGlobals());
const response = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
describe("API client", () => {
  it("parses a successful response", async () => { vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(rooms))); expect((await api.getRooms()).data).toHaveLength(4); });
  it.each([[400, validationError], [404, notFound]])("normalizes HTTP %s", async (status, body) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(body, status)));
    await expect(api.getRooms()).rejects.toMatchObject({ status, code: body.error.code, message: body.error.message });
  });
  it("normalizes network failures", async () => { vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("offline"))); await expect(api.getRooms()).rejects.toMatchObject({ code: "network_error" }); });
  it("rejects malformed responses", async () => { vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response({ data: [] }))); await expect(api.getRooms()).rejects.toThrow("Malformed rooms response"); });
  it("serializes history queries", async () => {
    const fetchMock = vi.fn().mockResolvedValue(response({ data: [], meta: { room_id: "room_a", range: "day", metric: "occupancy", count: 0 } })); vi.stubGlobal("fetch", fetchMock);
    await api.getHistory({ roomId: "room_a", range: "day", metric: "occupancy" });
    expect(fetchMock.mock.calls[0][0]).toContain("room_id=room_a&range=day&metric=occupancy");
  });
  it("exports structured errors", () => expect(new ApiError("x", 400, "bad")).toMatchObject({ status: 400, code: "bad" }));
});
