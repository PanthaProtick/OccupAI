import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api, ApiError } from "../api/client";
import { AuthContext } from "../auth/session";
import { ProtectedRoute } from "../auth/ProtectedRoute";
import type { AssistantQueryResponse } from "../api/types";
import { AssistantPage } from "./AssistantPage";

vi.mock("../api/client", async (load) => {
  const actual = await load<typeof import("../api/client")>();
  return { ...actual, api: {
    ...actual.api,
    getAssistantConversations: vi.fn(), getAssistantConversation: vi.fn(), queryAssistant: vi.fn(),
  }};
});

const auth = {user:{id:"user-1",name:"Student",email:"student@aust.edu",role:"user"},loading:false,
  login:async()=>{},signup:async()=>{},logout:async()=>{}};
const response:AssistantQueryResponse = {
  conversation_id:"34d8e859-af14-45f5-a4df-ee71345e213d",
  answer:"Here are the best currently available rooms.",
  results:[
    {room_id:"room_1a02",name:"1A02",building:"University Building",floor:1,block:"A",capacity:40,occupancy:6,occupancy_percentage:15,available_capacity:34,status:"online",observed_at:"2026-08-12T08:00:00Z",reason:"Lowest reliable occupancy."},
    {room_id:"room_1b03",name:"1B03",building:"University Building",floor:1,block:"B",capacity:40,occupancy:11,occupancy_percentage:27.5,available_capacity:29,status:"online",observed_at:"2026-08-12T08:00:00Z",reason:"Second-lowest reliable occupancy."},
  ],
  applied_filters:{buildings:[],floors:[1],blocks:[],maximum_occupancy_percentage:null,minimum_available_capacity:null,limit:3},
  data_timestamp:"2026-08-12T08:00:00Z",warnings:["Fewer than three reliable matches were available."],
};
const view = () => render(<AuthContext.Provider value={auth}><MemoryRouter><AssistantPage/></MemoryRouter></AuthContext.Provider>);
let localStorageWrite:ReturnType<typeof vi.fn>;
let sessionStorageWrite:ReturnType<typeof vi.fn>;
const storageDouble=(write:ReturnType<typeof vi.fn>):Storage=>({
  getItem:vi.fn(()=>null),setItem:write as Storage["setItem"],removeItem:vi.fn(),clear:vi.fn(),key:vi.fn(()=>null),length:0,
});

beforeEach(()=>{
  vi.mocked(api.getAssistantConversations).mockReset().mockResolvedValue({items:[],page:1,limit:20,next_page:null});
  vi.mocked(api.getAssistantConversation).mockReset();
  vi.mocked(api.queryAssistant).mockReset().mockResolvedValue(response);
  localStorageWrite=vi.fn();sessionStorageWrite=vi.fn();
  Object.defineProperty(window,"localStorage",{configurable:true,value:storageDouble(localStorageWrite)});
  Object.defineProperty(window,"sessionStorage",{configurable:true,value:storageDouble(sessionStorageWrite)});
});
afterEach(()=>{
  vi.restoreAllMocks();
  Object.defineProperty(window,"innerWidth",{configurable:true,value:1024,writable:true});
});

describe("Campus Assistant interface",()=>{
  it("shows the empty state and lets a suggested question populate the composer",async()=>{
    view(); expect(await screen.findByRole("heading",{name:"Find your best campus space"})).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button",{name:"Show rooms below 40% occupancy."}));
    expect(screen.getByLabelText("Ask Campus Assistant")).toHaveValue("Show rooms below 40% occupancy.");
  });

  it("sends once, renders ranked results in order, links by room ID, and shows freshness warnings",async()=>{
    view(); await screen.findByRole("heading",{name:"Find your best campus space"});
    fireEvent.change(screen.getByLabelText("Ask Campus Assistant"),{target:{value:"quiet rooms"}});
    fireEvent.click(screen.getByRole("button",{name:"Send"}));
    await waitFor(()=>expect(api.queryAssistant).toHaveBeenCalledWith({message:"quiet rooms"}));
    const results=await screen.findByRole("region",{name:"Recommended rooms"});
    expect(within(results).getAllByRole("heading").map(node=>node.textContent)).toEqual(["1A02","1B03"]);
    expect(within(results).getByRole("link",{name:"View room 1A02"})).toHaveAttribute("href","/rooms/room_1a02");
    expect(screen.getByText("Fewer than three reliable matches were available.")).toBeInTheDocument();
    expect(screen.getByText("Live data")).toBeInTheDocument();
  });

  it("disables duplicate submission while pending",async()=>{
    let resolve!:(value:AssistantQueryResponse)=>void;
    vi.mocked(api.queryAssistant).mockReturnValue(new Promise(done=>{resolve=done;}));
    view(); await screen.findByRole("heading",{name:"Find your best campus space"});
    fireEvent.change(screen.getByLabelText("Ask Campus Assistant"),{target:{value:"available rooms"}});
    fireEvent.submit(screen.getByLabelText("Ask Campus Assistant").closest("form")!);
    expect(screen.getByRole("button",{name:"Sending"})).toBeDisabled();
    fireEvent.submit(screen.getByLabelText("Ask Campus Assistant").closest("form")!);
    expect(api.queryAssistant).toHaveBeenCalledTimes(1); resolve(response);
  });

  it("restores the newest persisted conversation",async()=>{
    vi.mocked(api.getAssistantConversations).mockResolvedValue({items:[{id:"conversation-1",title:"Quiet rooms",created_at:"2026-08-12T08:00:00Z",updated_at:"2026-08-12T08:01:00Z",message_count:2}],page:1,limit:20,next_page:null});
    vi.mocked(api.getAssistantConversation).mockResolvedValue({id:"conversation-1",title:"Quiet rooms",created_at:"2026-08-12T08:00:00Z",updated_at:"2026-08-12T08:01:00Z",messages:[
      {id:"m1",role:"user",content:"quiet rooms",structured_results:null,created_at:"2026-08-12T08:00:00Z"},
      {id:"m2",role:"assistant",content:response.answer,structured_results:{results:response.results,data_timestamp:response.data_timestamp,warnings:response.warnings},created_at:"2026-08-12T08:01:00Z"},
    ]});
    view(); expect(await screen.findByText(response.answer)).toBeInTheDocument();
    expect(api.getAssistantConversation).toHaveBeenCalledWith("conversation-1",expect.anything());
  });

  it("shows a safe error and retries the last question",async()=>{
    vi.mocked(api.queryAssistant).mockRejectedValueOnce(new ApiError("Assistant is temporarily unavailable.",503,"unavailable")).mockResolvedValueOnce(response);
    view(); await screen.findByRole("heading",{name:"Find your best campus space"});
    fireEvent.change(screen.getByLabelText("Ask Campus Assistant"),{target:{value:"free rooms"}});fireEvent.click(screen.getByRole("button",{name:"Send"}));
    expect(await screen.findByRole("alert")).toHaveTextContent("Assistant is temporarily unavailable.");
    fireEvent.click(screen.getByRole("button",{name:"Retry"}));await waitFor(()=>expect(api.queryAssistant).toHaveBeenCalledTimes(2));
  });

  it("shows explicit stale and offline warnings",async()=>{
    vi.mocked(api.queryAssistant).mockResolvedValue({...response,results:[],answer:"No reliable rooms are currently available.",warnings:[
      "Offline and stale rooms were excluded from recommendations.",
    ]});
    view(); await screen.findByRole("heading",{name:"Find your best campus space"});
    fireEvent.change(screen.getByLabelText("Ask Campus Assistant"),{target:{value:"available rooms"}});
    fireEvent.click(screen.getByRole("button",{name:"Send"}));
    expect(await screen.findByText("Offline and stale rooms were excluded from recommendations.")).toBeInTheDocument();
  });

  it("renders a helpful empty-results state",async()=>{
    vi.mocked(api.queryAssistant).mockResolvedValue({...response,results:[],answer:"No reliable matches.",warnings:[]});
    view(); await screen.findByRole("heading",{name:"Find your best campus space"});
    fireEvent.change(screen.getByLabelText("Ask Campus Assistant"),{target:{value:"room for 200 people"}});
    fireEvent.click(screen.getByRole("button",{name:"Send"}));
    expect(await screen.findByText("No reliable matches.")).toBeInTheDocument();
  });

  it("renders user-provided markup as inert text",async()=>{
    const unsafe='<img src=x onerror="window.hacked=true"><script>window.hacked=true</script>';
    view(); await screen.findByRole("heading",{name:"Find your best campus space"});
    fireEvent.change(screen.getByLabelText("Ask Campus Assistant"),{target:{value:unsafe}});
    fireEvent.click(screen.getByRole("button",{name:"Send"}));
    expect(await screen.findByText(unsafe)).toBeInTheDocument();
    expect(document.querySelector("script")).toBeNull();
    expect(document.querySelector('img[src="x"]')).toBeNull();
    expect((window as typeof window & {hacked?:boolean}).hacked).not.toBe(true);
  });

  it("keeps the composer and suggestions usable at a mobile viewport",async()=>{
    Object.defineProperty(window,"innerWidth",{configurable:true,value:375,writable:true});
    window.dispatchEvent(new Event("resize"));
    view(); await screen.findByRole("heading",{name:"Find your best campus space"});
    const composer=screen.getByLabelText("Ask Campus Assistant");
    expect(composer).toBeEnabled(); expect(composer).toHaveAttribute("maxlength","1000");
    expect(screen.getByLabelText("Suggested questions")).toBeInTheDocument();
    fireEvent.change(composer,{target:{value:"free rooms"}});
    expect(screen.getByRole("button",{name:"Send"})).toBeEnabled();
  });

  it("never writes password or provider-key text to browser storage",async()=>{
    const sensitive="password: student-secret provider_api_key: provider-secret";
    view(); await screen.findByRole("heading",{name:"Find your best campus space"});
    fireEvent.change(screen.getByLabelText("Ask Campus Assistant"),{target:{value:sensitive}});
    fireEvent.click(screen.getByRole("button",{name:"Send"}));
    await waitFor(()=>expect(api.queryAssistant).toHaveBeenCalledWith({message:sensitive}));
    expect(localStorageWrite).not.toHaveBeenCalled();expect(sessionStorageWrite).not.toHaveBeenCalled();
    expect(localStorage.length).toBe(0); expect(sessionStorage.length).toBe(0);
  });

  it("is protected from unauthenticated access",()=>{
    const anonymous={...auth,user:null};
    render(<AuthContext.Provider value={anonymous}><MemoryRouter initialEntries={["/assistant"]}><Routes><Route path="/login" element={<p>Login required</p>}/><Route element={<ProtectedRoute/>}><Route path="/assistant" element={<AssistantPage/>}/></Route></Routes></MemoryRouter></AuthContext.Provider>);
    expect(screen.getByText("Login required")).toBeInTheDocument();
  });
});
