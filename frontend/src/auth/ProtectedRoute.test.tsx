import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";
import { ProtectedRoute } from "./ProtectedRoute";
import { startSession } from "./session";

function TestRoutes() {
  return <Routes>
    <Route path="/login" element={<p>Authentication required</p>} />
    <Route element={<ProtectedRoute />}><Route path="/dashboard" element={<p>Protected dashboard</p>} /></Route>
  </Routes>;
}

describe("ProtectedRoute", () => {
  beforeEach(() => sessionStorage.clear());

  it("redirects anonymous visitors to login", () => {
    render(<MemoryRouter initialEntries={["/dashboard"]}><TestRoutes /></MemoryRouter>);
    expect(screen.getByText("Authentication required")).toBeInTheDocument();
  });

  it("shows protected content after authentication", () => {
    startSession();
    render(<MemoryRouter initialEntries={["/dashboard"]}><TestRoutes /></MemoryRouter>);
    expect(screen.getByText("Protected dashboard")).toBeInTheDocument();
  });
});
