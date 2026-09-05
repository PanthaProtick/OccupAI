import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { WelcomePage } from "./WelcomePage";

describe("WelcomePage",()=>{it("routes every dashboard entry through authentication",()=>{render(<MemoryRouter><WelcomePage/></MemoryRouter>);expect(screen.getByRole("heading",{name:/Space that understands people/i})).toBeInTheDocument();expect(screen.getAllByRole("link",{name:/Get started/i})).toHaveLength(2);expect(screen.getAllByRole("link",{name:/Get started/i})[0]).toHaveAttribute("href","/login?mode=signup");expect(screen.getByRole("link",{name:"View live dashboard"})).toHaveAttribute("href","/login")});it("returns to the top from the header OccupAI control",()=>{const scrollTo=vi.spyOn(window,"scrollTo").mockImplementation(()=>{});render(<MemoryRouter><WelcomePage/></MemoryRouter>);fireEvent.click(screen.getByRole("link",{name:"OccupAI home"}));expect(scrollTo).toHaveBeenCalledWith({top:0,behavior:"smooth"})})});
