import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { ProtectedRoute } from "./ProtectedRoute";
import { AuthContext } from "./session";

function TestRoutes() {
  return <Routes>
    <Route path="/login" element={<p>Authentication required</p>} />
    <Route element={<ProtectedRoute />}><Route path="/dashboard" element={<p>Protected dashboard</p>} /></Route>
  </Routes>;
}

describe("ProtectedRoute", () => {
  it("redirects anonymous visitors to login", () => {
    const auth={user:null,loading:false,login:async()=>{},signup:async()=>{},logout:async()=>{}};
    render(<AuthContext.Provider value={auth}><MemoryRouter initialEntries={["/dashboard"]}><TestRoutes /></MemoryRouter></AuthContext.Provider>);
    expect(screen.getByText("Authentication required")).toBeInTheDocument();
  });

  it("shows protected content after authentication", () => {
    const auth={user:{id:"1",name:"Student",email:"student@aust.edu",role:"user"},loading:false,login:async()=>{},signup:async()=>{},logout:async()=>{}};
    render(<AuthContext.Provider value={auth}><MemoryRouter initialEntries={["/dashboard"]}><TestRoutes /></MemoryRouter></AuthContext.Provider>);
    expect(screen.getByText("Protected dashboard")).toBeInTheDocument();
  });
});
