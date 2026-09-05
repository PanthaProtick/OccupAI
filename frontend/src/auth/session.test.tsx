import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../api/client";
import { AuthProvider, useAuth } from "./session";

function Probe(){
  const auth=useAuth();
  if(auth.loading)return <p>Loading</p>;
  return <><p>{auth.user?.email ?? "Anonymous"}</p><button onClick={()=>void auth.logout()}>Logout</button></>;
}

describe("AuthProvider",()=>{
  const localSet=vi.fn();const sessionSet=vi.fn();
  beforeEach(()=>{vi.restoreAllMocks();localSet.mockClear();sessionSet.mockClear();
    Object.defineProperty(window,"localStorage",{configurable:true,value:{length:0,clear:vi.fn(),getItem:vi.fn(),key:vi.fn(),removeItem:vi.fn(),setItem:localSet}});
    Object.defineProperty(window,"sessionStorage",{configurable:true,value:{length:0,clear:vi.fn(),getItem:vi.fn(),key:vi.fn(),removeItem:vi.fn(),setItem:sessionSet}})});

  it("restores a backend session without browser storage",async()=>{
    vi.spyOn(api,"me").mockResolvedValue({data:{id:"1",name:"یسک",email:"student@aust.edu",role:"user"}});
    render(<AuthProvider><Probe/></AuthProvider>);
    expect(await screen.findByText("student@aust.edu")).toBeInTheDocument();
    expect(localSet).not.toHaveBeenCalled();expect(sessionSet).not.toHaveBeenCalled();
  });

  it("treats a failed current-user request as anonymous",async()=>{
    vi.spyOn(api,"me").mockRejectedValue(new Error("unauthenticated"));
    render(<AuthProvider><Probe/></AuthProvider>);
    expect(await screen.findByText("Anonymous")).toBeInTheDocument();
  });

  it("calls backend logout before clearing the user",async()=>{
    vi.spyOn(api,"me").mockResolvedValue({data:{id:"1",name:"Student",email:"student@aust.edu",role:"user"}});
    const logout=vi.spyOn(api,"logout").mockResolvedValue(undefined);
    render(<AuthProvider><Probe/></AuthProvider>);
    await screen.findByText("student@aust.edu");fireEvent.click(screen.getByRole("button",{name:"Logout"}));
    await waitFor(()=>expect(logout).toHaveBeenCalledOnce());
    expect(await screen.findByText("Anonymous")).toBeInTheDocument();
  });
});
