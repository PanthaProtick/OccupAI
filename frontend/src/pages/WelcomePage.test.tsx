import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { WelcomePage } from "./WelcomePage";

describe("WelcomePage",()=>{it("routes every dashboard entry through authentication",()=>{render(<MemoryRouter><WelcomePage/></MemoryRouter>);expect(screen.getByRole("heading",{name:/Space that understands people/i})).toBeInTheDocument();expect(screen.getAllByRole("link",{name:/Get started/i})).toHaveLength(2);expect(screen.getAllByRole("link",{name:/Get started/i})[0]).toHaveAttribute("href","/login?mode=signup");expect(screen.getByRole("link",{name:"View live dashboard"})).toHaveAttribute("href","/login")})});
