import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import rooms from "../../../contracts/examples/rooms.json";
import occupancy from "../../../contracts/examples/occupancy.json";
import { api } from "../api/client";
import { DashboardPage } from "./DashboardPage";
describe("DashboardPage", () => {
  afterEach(() => vi.restoreAllMocks());
  it("joins and renders all four ground-floor rooms", async () => {
    vi.spyOn(api, "getRooms").mockResolvedValue(rooms as never); vi.spyOn(api, "getOccupancy").mockResolvedValue(occupancy as never);
    render(<MemoryRouter><DashboardPage /></MemoryRouter>);
    expect(await screen.findAllByRole("article")).toHaveLength(4); expect(screen.getByRole("link", { name: "View T.T. Ground" })).toHaveAttribute("href", "/rooms/room_tt_ground");
  });
  it("retains loaded cards when refresh fails", async () => {
    const getRooms = vi.spyOn(api, "getRooms").mockResolvedValueOnce(rooms as never).mockRejectedValueOnce(new Error("Temporary failure"));
    vi.spyOn(api, "getOccupancy").mockResolvedValue(occupancy as never);
    render(<MemoryRouter><DashboardPage /></MemoryRouter>); await screen.findAllByRole("article"); fireEvent.click(screen.getByRole("button", { name: "Refresh" }));
    await screen.findByText(/Showing the last successful update/); expect(screen.getAllByRole("article")).toHaveLength(4); expect(getRooms).toHaveBeenCalledTimes(2);
  });
  it("prevents overlapping manual refreshes", async () => {
    let resolve!: (value: typeof rooms) => void; const pending = new Promise<typeof rooms>((done) => { resolve = done; });
    const getRooms = vi.spyOn(api, "getRooms").mockReturnValue(pending as never); vi.spyOn(api, "getOccupancy").mockResolvedValue(occupancy as never);
    render(<MemoryRouter><DashboardPage /></MemoryRouter>); expect(screen.getByText("Loading room occupancy")).toBeInTheDocument(); expect(getRooms).toHaveBeenCalledTimes(1); resolve(rooms); await waitFor(() => expect(screen.getAllByRole("article")).toHaveLength(4));
  });
  it("filters the schematic map by building and floor", async () => {
    vi.spyOn(api, "getRooms").mockResolvedValue(rooms as never); vi.spyOn(api, "getOccupancy").mockResolvedValue(occupancy as never);
    render(<MemoryRouter><DashboardPage /></MemoryRouter>);
    await screen.findByRole("heading", { name: "Floor map" });
    expect(screen.getByRole("link", { name: /T.T. Ground, 32% occupied/ })).toBeInTheDocument();
    expect(screen.getByLabelText("Building")).toHaveValue("University Building");
    expect(screen.getByLabelText("Floor")).toHaveValue("0");
    expect(screen.getByRole("link", { name: "Girls' Common Room, 20% occupied" })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Floor"), { target: { value: "1" } });
    expect(screen.getByRole("link", { name: /Study Room, Occupancy unavailable/ })).toBeInTheDocument();
    expect(screen.getAllByRole("article")).toHaveLength(7);
    fireEvent.change(screen.getByLabelText("Floor"), { target: { value: "2" } });
    expect(screen.getByRole("link", { name: /2A03, Occupancy unavailable/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /2B01, Occupancy unavailable/ })).toBeInTheDocument();
    expect(screen.getAllByRole("article")).toHaveLength(18);
  });
  it("restores the selected floor from the dashboard URL", async () => {
    vi.spyOn(api, "getRooms").mockResolvedValue(rooms as never); vi.spyOn(api, "getOccupancy").mockResolvedValue(occupancy as never);
    render(<MemoryRouter initialEntries={["/?building=University+Building&floor=6"]}><DashboardPage /></MemoryRouter>);
    await screen.findByRole("heading", { name: "Floor map" });
    expect(screen.getByLabelText("Floor")).toHaveValue("6");
    expect(screen.getByRole("link", { name: /6A03, Occupancy unavailable/ })).toBeInTheDocument();
    expect(screen.getAllByRole("article")).toHaveLength(18);
  });
});
