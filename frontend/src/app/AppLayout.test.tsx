import { fireEvent, render, screen } from "@testing-library/react";
import { Link, MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { AuthContext } from "../auth/session";
import { AppLayout } from "./AppLayout";

vi.mock("../components/NotificationPanel", () => ({
  NotificationPanel: () => <button type="button">Notifications</button>,
}));

describe("AppLayout dashboard navigation", () => {
  it("routes every section control back to its dashboard section", () => {
    const scrollTo = vi.spyOn(window, "scrollTo").mockImplementation(() => {});
    const auth = {
      user: { id: "1", name: "Student", email: "student@aust.edu", role: "user" },
      loading: false,
      login: async () => {}, signup: async () => {}, logout: async () => {},
    };
    render(<AuthContext.Provider value={auth}>
      <MemoryRouter initialEntries={["/profile"]}><AppLayout /></MemoryRouter>
    </AuthContext.Provider>);

    expect(screen.getByRole("link", { name: "Overview" })).toHaveAttribute("href", "/dashboard#overview");
    expect(screen.getByRole("link", { name: "Floor map" })).toHaveAttribute("href", "/dashboard#floor-map");
    expect(screen.getByRole("link", { name: "Rooms" })).toHaveAttribute("href", "/dashboard#rooms");
    fireEvent.click(screen.getByRole("link", { name: "OccupAI dashboard" }));
    expect(scrollTo).toHaveBeenCalledWith({ top: 0, behavior: "smooth" });
  });

  it("preserves the selected building and floor while exploring a room", () => {
    const auth = {
      user: { id: "1", name: "Student", email: "student@aust.edu", role: "user" },
      loading: false,
      login: async () => {}, signup: async () => {}, logout: async () => {},
    };
    render(<AuthContext.Provider value={auth}>
      <MemoryRouter initialEntries={["/dashboard?building=University+Building&floor=5"]}>
        <Routes>
          <Route element={<AppLayout />}>
            <Route path="/dashboard" element={<Link to="/rooms/5A01">Explore room</Link>} />
            <Route path="/rooms/:roomId" element={<p>Room detail</p>} />
          </Route>
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>);

    fireEvent.click(screen.getByRole("link", { name: "Explore room" }));
    expect(screen.getByText("Room detail")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Floor map" })).toHaveAttribute(
      "href", "/dashboard?building=University+Building&floor=5#floor-map",
    );
  });
});
