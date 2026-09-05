import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { AuthPage } from "./AuthPage";
import { AuthContext } from "../auth/session";

const auth={user:null,loading:false,login:async()=>{},signup:async()=>{},logout:async()=>{}};

describe("AuthPage",()=>{it("switches between login and AUST-only signup",()=>{render(<AuthContext.Provider value={auth}><MemoryRouter initialEntries={["/login"]}><Routes><Route path="/login" element={<AuthPage/>}/></Routes></MemoryRouter></AuthContext.Provider>);expect(screen.getByRole("heading",{name:"Continue to your campus"})).toBeInTheDocument();fireEvent.click(screen.getByRole("tab",{name:"Sign up"}));expect(screen.getByRole("heading",{name:"Start with OccupAI"})).toBeInTheDocument();expect(screen.getByLabelText("Your name")).toBeInTheDocument();expect(screen.getByLabelText("Email address")).toHaveAttribute("pattern")})});

it("sends the entered login credentials and exposes errors",async()=>{const login=vi.fn().mockRejectedValue(new Error("rejected"));render(<AuthContext.Provider value={{...auth,login}}><MemoryRouter><AuthPage/></MemoryRouter></AuthContext.Provider>);fireEvent.change(screen.getByLabelText("Email address"),{target:{value:"student@aust.edu"}});fireEvent.change(screen.getByLabelText("Password"),{target:{value:"Strong-password-42!"}});fireEvent.click(screen.getByRole("button",{name:/Open dashboard/}));await waitFor(()=>expect(login).toHaveBeenCalledWith("student@aust.edu","Strong-password-42!"));expect(screen.getByRole("alert")).toBeInTheDocument()});

it("sends name, AUST email, and password during signup",async()=>{const signup=vi.fn().mockRejectedValue(new Error("rejected"));render(<AuthContext.Provider value={{...auth,signup}}><MemoryRouter initialEntries={["/login?mode=signup"]}><AuthPage/></MemoryRouter></AuthContext.Provider>);fireEvent.change(screen.getByLabelText("Your name"),{target:{value:"AUST Student"}});fireEvent.change(screen.getByLabelText("Email address"),{target:{value:"student@aust.edu"}});fireEvent.change(screen.getByLabelText("Password"),{target:{value:"Strong-password-42!"}});fireEvent.click(screen.getByRole("button",{name:/Create account/}));await waitFor(()=>expect(signup).toHaveBeenCalledWith("AUST Student","student@aust.edu","Strong-password-42!"))});
