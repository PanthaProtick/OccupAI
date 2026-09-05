import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AuthContext } from "../auth/session";
import { ProtectedRoute } from "../auth/ProtectedRoute";
import { api, ApiError } from "../api/client";
import { ChangePasswordPage } from "./ChangePasswordPage";
import { ProfilePage } from "./ProfilePage";

vi.mock("../api/client", async () => {
  const actual = await vi.importActual<typeof import("../api/client")>("../api/client");
  return { ...actual, api: {
    ...actual.api,
    getProfile: vi.fn(),
    updateProfile: vi.fn(),
    changePassword: vi.fn(),
  }};
});

const profile = {
  id: "user-1", name: "Real AUST Student", email: "student@aust.edu",
  created_at: "2026-09-05T10:00:00Z", updated_at: "2026-09-05T10:00:00Z",
};
const authenticated = {
  user: { id: "user-1", name: profile.name, email: profile.email, role: "user" },
  loading: false, login: async () => {}, signup: async () => {}, logout: async () => {},
};

beforeEach(() => {
  vi.mocked(api.getProfile).mockReset().mockResolvedValue(profile);
  vi.mocked(api.updateProfile).mockReset();
  vi.mocked(api.changePassword).mockReset();
});

describe("Profile integration", () => {
  it("loads and renders real database profile data without fake fallbacks", async () => {
    render(<MemoryRouter><ProfilePage /></MemoryRouter>);
    expect(screen.getByRole("status")).toHaveTextContent("Loading your profile");
    expect(await screen.findByText("Real AUST Student")).toBeInTheDocument();
    expect(screen.getByText("student@aust.edu")).toBeInTheDocument();
    expect(screen.queryByText("Campus Admin")).not.toBeInTheDocument();
    expect(screen.queryByText("admin@occupai.edu")).not.toBeInTheDocument();
  });

  it("persists a name edit through the API", async () => {
    vi.mocked(api.updateProfile).mockResolvedValue({...profile, name: "Updated Student"});
    render(<MemoryRouter><ProfilePage /></MemoryRouter>);
    await screen.findByText("Real AUST Student");
    fireEvent.click(screen.getByRole("button", { name: "Edit" }));
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "  Updated   Student " } });
    fireEvent.click(screen.getByRole("button", { name: /Save/ }));
    await waitFor(() => expect(api.updateProfile).toHaveBeenCalledWith({ name: "Updated Student" }));
    expect(await screen.findByText("Updated Student")).toBeInTheDocument();
  });

  it("shows a load error and retry action", async () => {
    vi.mocked(api.getProfile).mockRejectedValueOnce(new ApiError("Profile unavailable.", 500, "error"));
    render(<MemoryRouter><ProfilePage /></MemoryRouter>);
    expect(await screen.findByRole("alert")).toHaveTextContent("Profile unavailable");
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByText("Real AUST Student")).toBeInTheDocument();
  });
});

describe("Dedicated password page", () => {
  const renderPassword = () => render(<MemoryRouter initialEntries={["/profile/change-password"]}>
    <Routes>
      <Route path="/profile/change-password" element={<ChangePasswordPage />} />
      <Route path="/profile" element={<ProfilePage />} />
    </Routes>
  </MemoryRouter>);

  it("is linked from the profile page", async () => {
    render(<MemoryRouter><ProfilePage /></MemoryRouter>);
    const link = await screen.findByRole("link", { name: /Change password/ });
    expect(link).toHaveAttribute("href", "/profile/change-password");
  });

  it("prevents mismatched passwords from being submitted", () => {
    renderPassword();
    fireEvent.change(screen.getByLabelText("Current Password"), { target: { value: "Current1!" } });
    fireEvent.change(screen.getByLabelText("New Password"), { target: { value: "NewPassword1!" } });
    fireEvent.change(screen.getByLabelText("Confirm New Password"), { target: { value: "Different1!" } });
    fireEvent.click(screen.getByRole("button", { name: "Update Password" }));
    expect(screen.getByRole("alert")).toHaveTextContent("do not match");
    expect(api.changePassword).not.toHaveBeenCalled();
  });

  it("disables duplicate submission, clears secrets, and confirms success on Profile", async () => {
    let resolve!: () => void;
    vi.mocked(api.changePassword).mockReturnValue(new Promise<void>((done) => { resolve = done; }));
    renderPassword();
    fireEvent.change(screen.getByLabelText("Current Password"), { target: { value: "Current1!" } });
    fireEvent.change(screen.getByLabelText("New Password"), { target: { value: "NewPassword1!" } });
    fireEvent.change(screen.getByLabelText("Confirm New Password"), { target: { value: "NewPassword1!" } });
    fireEvent.click(screen.getByRole("button", { name: "Update Password" }));
    expect(screen.getByRole("button", { name: "Updating…" })).toBeDisabled();
    resolve();
    expect(await screen.findByText("Password updated successfully.")).toBeInTheDocument();
    expect(api.changePassword).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole("link", { name: /Change password/ }));
    expect(screen.getByLabelText("Current Password")).toHaveValue("");
    expect(screen.getByLabelText("New Password")).toHaveValue("");
    expect(screen.getByLabelText("Confirm New Password")).toHaveValue("");
  });

  it("uses the registration policy and never writes passwords to browser storage", () => {
    const localStorageSpy = vi.spyOn(Storage.prototype, "setItem");
    renderPassword();
    expect(screen.getByText(/Use between 6 and 128 characters/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Current Password"), { target: { value: "Current1!" } });
    fireEvent.change(screen.getByLabelText("New Password"), { target: { value: "short" } });
    fireEvent.change(screen.getByLabelText("Confirm New Password"), { target: { value: "short" } });
    fireEvent.click(screen.getByRole("button", { name: "Update Password" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Use between 6 and 128 characters");
    expect(api.changePassword).not.toHaveBeenCalled();
    expect(localStorageSpy).not.toHaveBeenCalled();
  });

  it("presents backend errors safely", async () => {
    vi.mocked(api.changePassword).mockRejectedValue(new ApiError("Password could not be changed.", 400, "invalid_current_password"));
    renderPassword();
    fireEvent.change(screen.getByLabelText("Current Password"), { target: { value: "WrongPass" } });
    fireEvent.change(screen.getByLabelText("New Password"), { target: { value: "NewPassword1!" } });
    fireEvent.change(screen.getByLabelText("Confirm New Password"), { target: { value: "NewPassword1!" } });
    fireEvent.click(screen.getByRole("button", { name: "Update Password" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Password could not be changed");
  });

  it("redirects anonymous users away from the password page", () => {
    const anonymous = {...authenticated, user: null};
    render(<AuthContext.Provider value={anonymous}><MemoryRouter initialEntries={["/profile/change-password"]}>
      <Routes>
        <Route path="/login" element={<p>Login required</p>} />
        <Route element={<ProtectedRoute />}>
          <Route path="/profile/change-password" element={<ChangePasswordPage />} />
        </Route>
      </Routes>
    </MemoryRouter></AuthContext.Provider>);
    expect(screen.getByText("Login required")).toBeInTheDocument();
  });
});
