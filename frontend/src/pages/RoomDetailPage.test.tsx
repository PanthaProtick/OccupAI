import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import stale from "../../../contracts/examples/stale-room.json";
import history from "../../../contracts/examples/history.json";
import { api, ApiError } from "../api/client";
import { RoomDetailPage } from "./RoomDetailPage";
const view = () => render(<MemoryRouter initialEntries={["/rooms/room_library_01"]}><Routes><Route path="rooms/:roomId" element={<RoomDetailPage />} /></Routes></MemoryRouter>);
describe("RoomDetailPage", () => {
  afterEach(() => vi.restoreAllMocks());
  it("loads directly from the route id", async () => { const getRoom = vi.spyOn(api, "getRoom").mockResolvedValue(stale as never); vi.spyOn(api, "getHistory").mockResolvedValue(history as never); view(); expect(await screen.findByRole("heading", { name: "Library Reading Room" })).toBeInTheDocument(); expect(getRoom).toHaveBeenCalledWith("room_library_01", expect.anything()); expect(screen.getByText("Stale")).toBeInTheDocument(); });
  it("shows not found for an unknown room", async () => { vi.spyOn(api, "getRoom").mockRejectedValue(new ApiError("Unknown room", 404, "room_not_found")); view(); expect(await screen.findByRole("heading", { name: "Page not found" })).toBeInTheDocument(); });
});
