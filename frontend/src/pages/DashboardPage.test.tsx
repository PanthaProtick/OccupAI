import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import rooms from "../../../contracts/examples/rooms.json";
import occupancy from "../../../contracts/examples/occupancy.json";
import { api } from "../api/client";
import { DashboardPage } from "./DashboardPage";
describe("DashboardPage", () => {
  afterEach(() => vi.restoreAllMocks());
  it("joins and renders all seven API rooms", async () => {
    vi.spyOn(api, "getRooms").mockResolvedValue(rooms as never); vi.spyOn(api, "getOccupancy").mockResolvedValue(occupancy as never);
    render(<MemoryRouter><DashboardPage /></MemoryRouter>);
    expect(await screen.findAllByRole("article")).toHaveLength(7); expect(screen.getByRole("link", { name: "View CSE 201" })).toHaveAttribute("href", "/rooms/room_cse_201");
  });
  it("retains loaded cards when refresh fails", async () => {
    const getRooms = vi.spyOn(api, "getRooms").mockResolvedValueOnce(rooms as never).mockRejectedValueOnce(new Error("Temporary failure"));
    vi.spyOn(api, "getOccupancy").mockResolvedValue(occupancy as never);
    render(<MemoryRouter><DashboardPage /></MemoryRouter>); await screen.findAllByRole("article"); fireEvent.click(screen.getByRole("button", { name: "Refresh" }));
    await screen.findByText(/Showing the last successful update/); expect(screen.getAllByRole("article")).toHaveLength(7); expect(getRooms).toHaveBeenCalledTimes(2);
  });
  it("prevents overlapping manual refreshes", async () => {
    let resolve!: (value: typeof rooms) => void; const pending = new Promise<typeof rooms>((done) => { resolve = done; });
    const getRooms = vi.spyOn(api, "getRooms").mockReturnValue(pending as never); vi.spyOn(api, "getOccupancy").mockResolvedValue(occupancy as never);
    render(<MemoryRouter><DashboardPage /></MemoryRouter>); expect(screen.getByText("Loading room occupancy")).toBeInTheDocument(); expect(getRooms).toHaveBeenCalledTimes(1); resolve(rooms); await waitFor(() => expect(screen.getAllByRole("article")).toHaveLength(7));
  });
});
