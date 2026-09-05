import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import type { ContextType } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api, ApiError } from "../api/client";
import { AuthContext } from "../auth/session";
import type { AppNotification } from "../api/types";
import { NotificationPanel } from "./NotificationPanel";

vi.mock("../api/client", async () => {
  const actual = await vi.importActual<typeof import("../api/client")>("../api/client");
  return { ...actual, api: {
    ...actual.api,
    getNotifications: vi.fn(),
    markNotificationRead: vi.fn(),
    markAllNotificationsRead: vi.fn(),
    dismissNotification: vi.fn(),
  }};
});

const user = { id: "user-1", name: "Student", email: "student@aust.edu", role: "user" };
const auth = { user, loading: false, login: async () => {}, signup: async () => {}, logout: async () => {} };
const notification: AppNotification = {
  id: "notification-1", type: "high_occupancy", category: "occupancy",
  title: "Crowded room", message: "Room 201 is 85% occupied.", room_id: "room_201",
  suggested_room_id: "room_202", occupancy_percentage: 85,
  created_at: "2026-09-05T10:00:00Z", read_at: null, dismissed_at: null,
};

function view(context: ContextType<typeof AuthContext> = auth) {
  return <AuthContext.Provider value={context}><MemoryRouter>
    <Routes>
      <Route path="*" element={<><NotificationPanel/><p>Current page</p></>} />
      <Route path="/rooms/:roomId" element={<p>Suggested room page</p>} />
    </Routes>
  </MemoryRouter></AuthContext.Provider>;
}

beforeEach(() => {
  vi.mocked(api.getNotifications).mockReset().mockResolvedValue({
    items: [notification], unread_count: 1, next_cursor: null,
  });
  vi.mocked(api.markNotificationRead).mockReset().mockResolvedValue({
    ...notification, read_at: "2026-09-05T10:01:00Z",
  });
  vi.mocked(api.markAllNotificationsRead).mockReset().mockResolvedValue(undefined);
  vi.mocked(api.dismissNotification).mockReset().mockResolvedValue(undefined);
});

describe("NotificationPanel integration", () => {
  it("loads backend notifications and displays backend unread count", async () => {
    render(view());
    await waitFor(() => expect(api.getNotifications).toHaveBeenCalledTimes(1));
    expect(screen.getByText("1")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Notifications" }));
    expect(await screen.findByText("Crowded room")).toBeInTheDocument();
    expect(screen.queryByText(/HVAC/)).not.toBeInTheDocument();
    expect(screen.queryByText(/calibration/)).not.toBeInTheDocument();
  });

  it("marks a notification read and navigates to its suggested room", async () => {
    render(view());
    await waitFor(() => expect(api.getNotifications).toHaveBeenCalled());
    fireEvent.click(screen.getByRole("button", { name: "Notifications" }));
    fireEvent.click(screen.getByText("Crowded room").closest("button")!);
    await waitFor(() => expect(api.markNotificationRead).toHaveBeenCalledWith("notification-1"));
    expect(await screen.findByText("Suggested room page")).toBeInTheDocument();
  });

  it("marks all notifications read through the backend", async () => {
    render(view());
    await waitFor(() => expect(api.getNotifications).toHaveBeenCalled());
    fireEvent.click(screen.getByRole("button", { name: "Notifications" }));
    fireEvent.click(screen.getByRole("button", { name: "Mark all read" }));
    await waitFor(() => expect(api.markAllNotificationsRead).toHaveBeenCalledTimes(1));
    expect(screen.queryByText("1")).not.toBeInTheDocument();
  });

  it("dismisses through the backend and renders the empty state", async () => {
    render(view());
    await waitFor(() => expect(api.getNotifications).toHaveBeenCalled());
    fireEvent.click(screen.getByRole("button", { name: "Notifications" }));
    fireEvent.click(screen.getByRole("button", { name: "Dismiss Crowded room" }));
    await waitFor(() => expect(api.dismissNotification).toHaveBeenCalledWith("notification-1"));
    expect(screen.getByText("No notifications yet")).toBeInTheDocument();
  });

  it("shows loading and API error states with retry", async () => {
    let reject!: (error: unknown) => void;
    vi.mocked(api.getNotifications).mockReturnValueOnce(new Promise((_, fail) => { reject = fail; }));
    render(view());
    fireEvent.click(screen.getByRole("button", { name: "Notifications" }));
    expect(screen.getByRole("status")).toHaveTextContent("Loading notifications");
    reject(new ApiError("Notifications unavailable.", 500, "error"));
    expect(await screen.findByRole("alert")).toHaveTextContent("Notifications unavailable");
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByText("Crowded room")).toBeInTheDocument();
  });

  it("clears temporary data on logout and reloads it after login", async () => {
    const rendered = render(view());
    await waitFor(() => expect(api.getNotifications).toHaveBeenCalledTimes(1));
    const anonymous: ContextType<typeof AuthContext> = {...auth, user: null};
    rendered.rerender(view(anonymous));
    rendered.rerender(view(auth));
    await waitFor(() => expect(api.getNotifications).toHaveBeenCalledTimes(2));
  });
});
