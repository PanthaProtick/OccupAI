import { afterEach, describe, expect, it, vi } from "vitest";
import rooms from "../../../contracts/examples/rooms.json";
import notFound from "../../../contracts/examples/not-found-error.json";
import validationError from "../../../contracts/examples/validation-error.json";
import { api, ApiError } from "./client";

afterEach(() => vi.unstubAllGlobals());
const response = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
describe("API client", () => {
  it("parses a successful response", async () => { vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(rooms))); expect((await api.getRooms()).data).toHaveLength(155); });
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
  it("uses the profile and password endpoints with the correct methods", async () => {
    const profile = {id:"1",name:"Student",email:"student@aust.edu",created_at:"2026-09-05T10:00:00Z",updated_at:"2026-09-05T10:00:00Z"};
    const fetchMock = vi.fn().mockResolvedValueOnce(response(profile)).mockResolvedValueOnce(new Response(null,{status:204}));
    vi.stubGlobal("fetch", fetchMock);
    await api.updateProfile({name:"Student"});
    await api.changePassword({current_password:"Current1",new_password:"Changed1"});
    expect(fetchMock.mock.calls[0][1]).toMatchObject({method:"PATCH",body:JSON.stringify({name:"Student"})});
    expect(fetchMock.mock.calls[1][1]).toMatchObject({method:"POST"});
  });
  it("parses notification responses and calls notification mutations", async () => {
    const notification = {id:"n1",type:"high_occupancy",category:"occupancy",title:"High occupancy",message:"Crowded",room_id:"room_1",suggested_room_id:null,occupancy_percentage:85,created_at:"2026-09-05T10:00:00Z",read_at:null,dismissed_at:null};
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response({items:[notification],unread_count:1,next_cursor:null}))
      .mockResolvedValueOnce(response({...notification,read_at:"2026-09-05T10:01:00Z"}))
      .mockResolvedValueOnce(new Response(null,{status:204}))
      .mockResolvedValueOnce(new Response(null,{status:204}));
    vi.stubGlobal("fetch", fetchMock);
    expect((await api.getNotifications()).unread_count).toBe(1);
    await api.markNotificationRead("n1");
    await api.markAllNotificationsRead();
    await api.dismissNotification("n1");
    expect(fetchMock.mock.calls.map((call) => call[0])).toEqual(expect.arrayContaining([
      expect.stringContaining("/notifications/n1/read"),
      expect.stringContaining("/notifications/read-all"),
      expect.stringContaining("/notifications/n1/dismiss"),
    ]));
  });
});
