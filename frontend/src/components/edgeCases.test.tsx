import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import occupancyResponse from "../../../contracts/examples/occupancy.json";
import offline from "../../../contracts/examples/offline-camera.json";
import overCapacity from "../../../contracts/examples/over-capacity.json";
import stale from "../../../contracts/examples/stale-room.json";
import zero from "../../../contracts/examples/zero-occupancy.json";
import emptyHistory from "../../../contracts/examples/empty-history.json";
import partialHistory from "../../../contracts/examples/partial-coverage-history.json";
import notFound from "../../../contracts/examples/not-found-error.json";
import validationError from "../../../contracts/examples/validation-error.json";
import rooms from "../../../contracts/examples/rooms.json";
import { ErrorState } from "./feedback/ErrorState";
import { HistoryChart } from "./history/HistoryChart";
import { OccupancyReading } from "./occupancy/OccupancyReading";
import { RoomCard } from "./rooms/RoomCard";
import type { Occupancy, Room, RoomView } from "../api/types";

describe("provided UI edge cases", () => {
  it("renders normal online data", () => { render(<MemoryRouter><RoomCard room={rooms.data[0] as Room} occupancy={occupancyResponse.data[0] as Occupancy} /></MemoryRouter>); expect(screen.getByText("Online")).toBeInTheDocument(); expect(screen.getByText("32% · capacity 150")).toBeInTheDocument(); });
  it("renders stale last-known occupancy", () => { render(<MemoryRouter><RoomCard room={stale.data as RoomView} occupancy={stale.data as RoomView} /></MemoryRouter>); expect(screen.getByText("Stale")).toBeInTheDocument(); expect(screen.getByText("96")).toBeInTheDocument(); });
  it("renders offline as unavailable, not zero", () => { render(<OccupancyReading data={offline.data as Occupancy} />); expect(screen.getByText("Unavailable")).toBeInTheDocument(); expect(screen.queryByText("0")).not.toBeInTheDocument(); });
  it("renders a measured zero", () => { render(<OccupancyReading data={zero.data as Occupancy} />); expect(screen.getByText("0")).toBeInTheDocument(); expect(screen.getByText("0% · capacity 80")).toBeInTheDocument(); });
  it("caps display and retains over-capacity raw count", () => { render(<OccupancyReading data={overCapacity.data as Occupancy} />); expect(screen.getByText("100% · capacity 120")).toBeInTheDocument(); expect(screen.getByText(/Raw count: 126/)).toBeInTheDocument(); });
  it("renders empty history without artificial points", () => { render(<HistoryChart points={emptyHistory.data} metric="occupancy" />); expect(screen.getByText("No history available")).toBeInTheDocument(); expect(screen.queryByRole("img")).not.toBeInTheDocument(); });
  it("communicates partial coverage", () => { render(<HistoryChart points={partialHistory.data} metric="occupancy" />); expect(screen.getByText(/62.5% coverage — incomplete/)).toBeInTheDocument(); });
  it.each([notFound, validationError])("renders supplied API errors", (payload) => { const retry = vi.fn(); render(<ErrorState message={payload.error.message} onRetry={retry} />); expect(screen.getByText(payload.error.message)).toBeInTheDocument(); fireEvent.click(screen.getByRole("button", { name: "Try again" })); expect(retry).toHaveBeenCalled(); });
});
