import { env } from "../config/env";
import type { ApiErrorResponse, HistoryMetric, HistoryRange, NotificationPreferences } from "./types";
import { parseHistory, parseNotification, parseNotificationPreferences, parseNotifications, parseOccupancy, parseOccupancyList, parseProfile, parseRoom, parseRooms } from "./validation";

export class ApiError extends Error {
  constructor(message: string, public readonly status: number | null, public readonly code: string, public readonly details?: Record<string, unknown>) { super(message); this.name = "ApiError"; }
}
export interface RequestOptions { signal?: AbortSignal; timeoutMs?: number; method?: "GET"|"POST"|"PATCH"; body?: unknown }

async function request(path: string, { signal, timeoutMs = 10_000, method = "GET", body: requestBody }: RequestOptions = {}): Promise<unknown> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort("timeout"), timeoutMs);
  const abort = () => controller.abort(signal?.reason);
  signal?.addEventListener("abort", abort, { once: true });
  try {
    const response = await fetch(`${env.apiBaseUrl}${path}`, { method, credentials: "include", signal: controller.signal,
      headers: { Accept: "application/json", ...(requestBody === undefined ? {} : { "Content-Type": "application/json" }) },
      body: requestBody === undefined ? undefined : JSON.stringify(requestBody) });
    if (response.status === 204) return undefined;
    let body: unknown;
    try { body = await response.json(); } catch { throw new ApiError("The server returned invalid JSON.", response.status, "invalid_json"); }
    if (!response.ok) {
      const candidate = body as Partial<ApiErrorResponse>;
      throw new ApiError(candidate.error?.message ?? `Request failed (${response.status}).`, response.status, candidate.error?.code ?? "request_failed", candidate.error?.details);
    }
    return body;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (controller.signal.aborted) throw new ApiError(signal?.aborted ? "Request cancelled." : "Request timed out.", null, signal?.aborted ? "cancelled" : "timeout");
    throw new ApiError("Unable to reach the OccupAI API.", null, "network_error");
  } finally {
    window.clearTimeout(timeout); signal?.removeEventListener("abort", abort);
  }
}
const segment = (value: string) => encodeURIComponent(value);
export const api = {
  signup: (value: {name:string;email:string;password:string}) => request("/auth/signup", {method:"POST",body:value}) as Promise<{data:AuthUser}>,
  login: (value: {email:string;password:string}) => request("/auth/login", {method:"POST",body:value}) as Promise<{data:AuthUser}>,
  logout: () => request("/auth/logout", {method:"POST"}),
  me: () => request("/auth/me") as Promise<{data:AuthUser}>,
  getProfile: (options?: RequestOptions) => request("/profile", options).then(parseProfile),
  updateProfile: (value: {name:string}) => request("/profile", {method:"PATCH",body:value}).then(parseProfile),
  changePassword: (value: {current_password:string;new_password:string}) => request("/profile/change-password", {method:"POST",body:value}),
  getNotifications: (options?: RequestOptions) => request("/notifications", options).then(parseNotifications),
  markNotificationRead: (id:string) => request(`/notifications/${segment(id)}/read`, {method:"POST"}).then(parseNotification),
  markAllNotificationsRead: () => request("/notifications/read-all", {method:"POST"}),
  dismissNotification: (id:string) => request(`/notifications/${segment(id)}/dismiss`, {method:"POST"}),
  getNotificationPreferences: (options?: RequestOptions) => request("/notification-preferences", options).then(parseNotificationPreferences),
  updateNotificationPreferences: (value: Partial<NotificationPreferences>) => request("/notification-preferences", {method:"PATCH",body:value}).then(parseNotificationPreferences),
  getRooms: (options?: RequestOptions) => request("/rooms", options).then(parseRooms),
  getRoom: (roomId: string, options?: RequestOptions) => request(`/rooms/${segment(roomId)}`, options).then(parseRoom),
  getOccupancy: (options?: RequestOptions) => request("/occupancy", options).then(parseOccupancyList),
  getOccupancyByCamera: (cameraId: string, options?: RequestOptions) => request(`/occupancy/${segment(cameraId)}`, options).then(parseOccupancy),
  getHistory: ({ roomId, range, metric }: { roomId: string; range: HistoryRange; metric: HistoryMetric }, options?: RequestOptions) => {
    const query = new URLSearchParams({ room_id: roomId, range, metric });
    return request(`/history?${query}`, options).then(parseHistory);
  },
};
export interface AuthUser { id:string; name:string; email:string; role:string }
