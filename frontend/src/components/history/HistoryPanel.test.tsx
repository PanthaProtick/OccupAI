import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import history from "../../../../contracts/examples/history.json";
import { api } from "../../api/client";
import { HistoryPanel } from "./HistoryPanel";
describe("HistoryPanel", () => {
  afterEach(() => vi.restoreAllMocks());
  it("requests new filters and shows their response", async () => {
    const mock = vi.spyOn(api, "getHistory").mockResolvedValue(history as never);
    render(<HistoryPanel roomId="room_cse_201" />); await screen.findByRole("img");
    fireEvent.click(screen.getByRole("button", { name: "hour" })); fireEvent.click(screen.getByRole("button", { name: "percentage" }));
    await waitFor(() => expect(mock).toHaveBeenLastCalledWith({ roomId: "room_cse_201", range: "hour", metric: "percentage" }, expect.objectContaining({ signal: expect.any(AbortSignal) })));
  });
});
