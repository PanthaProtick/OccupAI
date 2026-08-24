export type CameraStatus = "online" | "stale" | "offline";
export type HistoryRange = "hour" | "day" | "week";
export type HistoryMetric = "occupancy" | "percentage";

export interface CollectionMeta { count: number; generated_at?: string | null }
export interface Room {
  room_id: string; name: string; capacity: number; building: string; floor: number;
  camera_id: string; behavior_profile: string;
}
export interface Occupancy {
  camera_id: string; room_id: string; occupancy: number | null; raw_occupancy: number | null;
  capacity: number; occupancy_percentage: number | null; status: CameraStatus; updated_at: string;
}
export interface RoomView extends Room, Omit<Occupancy, "camera_id" | "room_id" | "capacity"> {
  intensity: string | null;
}
export interface HistoryPoint { bucket_start: string; value: number; coverage_percentage: number }
export interface HistoryMeta extends CollectionMeta { room_id: string; range: HistoryRange; metric: HistoryMetric }
export interface RoomsResponse { data: Room[]; meta: CollectionMeta }
export interface RoomResponse { data: RoomView }
export interface OccupancyListResponse { data: Occupancy[]; meta: CollectionMeta }
export interface OccupancyResponse { data: Occupancy }
export interface HistoryResponse { data: HistoryPoint[]; meta: HistoryMeta }
export interface ApiErrorBody { code: string; message: string; details?: Record<string, unknown> }
export interface ApiErrorResponse { error: ApiErrorBody }
