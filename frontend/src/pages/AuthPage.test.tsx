import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { AuthPage } from "./AuthPage";

describe("AuthPage",()=>{it("switches between login and signup",()=>{render(<MemoryRouter initialEntries={["/login"]}><Routes><Route path="/login" element={<AuthPage/>}/></Routes></MemoryRouter>);expect(screen.getByRole("heading",{name:"Continue to your campus"})).toBeInTheDocument();fireEvent.click(screen.getByRole("tab",{name:"Sign up"}));expect(screen.getByRole("heading",{name:"Start with OccupAI"})).toBeInTheDocument();expect(screen.getByLabelText("Your name")).toBeInTheDocument()})});
