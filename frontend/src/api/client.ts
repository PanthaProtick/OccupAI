import { env } from "../config/env";
import type { ApiErrorResponse, HistoryMetric, HistoryRange } from "./types";
import { parseHistory, parseOccupancy, parseOccupancyList, parseRoom, parseRooms } from "./validation";

export class ApiError extends Error {
  constructor(message: string, public readonly status: number | null, public readonly code: string, public readonly details?: Record<string, unknown>) { super(message); this.name = "ApiError"; }
}
export interface RequestOptions { signal?: AbortSignal; timeoutMs?: number }

async function request(path: string, { signal, timeoutMs = 10_000 }: RequestOptions = {}): Promise<unknown> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort("timeout"), timeoutMs);
  const abort = () => controller.abort(signal?.reason);
  signal?.addEventListener("abort", abort, { once: true });
  try {
    const response = await fetch(`${env.apiBaseUrl}${path}`, { headers: { Accept: "application/json" }, signal: controller.signal });
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
  getRooms: (options?: RequestOptions) => request("/rooms", options).then(parseRooms),
  getRoom: (roomId: string, options?: RequestOptions) => request(`/rooms/${segment(roomId)}`, options).then(parseRoom),
  getOccupancy: (options?: RequestOptions) => request("/occupancy", options).then(parseOccupancyList),
  getOccupancyByCamera: (cameraId: string, options?: RequestOptions) => request(`/occupancy/${segment(cameraId)}`, options).then(parseOccupancy),
  getHistory: ({ roomId, range, metric }: { roomId: string; range: HistoryRange; metric: HistoryMetric }, options?: RequestOptions) => {
    const query = new URLSearchParams({ room_id: roomId, range, metric });
    return request(`/history?${query}`, options).then(parseHistory);
  },
};
