export type CameraStatus = "online" | "stale" | "offline";
export type HistoryRange = "hour" | "day" | "week";
export type HistoryMetric = "occupancy" | "percentage";

export interface Profile { id:string; name:string; email:string; created_at:string; updated_at:string }
export interface AppNotification {
  id:string; type:string; category:string; title:string; message:string;
  room_id:string|null; suggested_room_id:string|null; occupancy_percentage:number|null;
  created_at:string; read_at:string|null; dismissed_at:string|null;
}
export interface NotificationsResponse { items:AppNotification[]; unread_count:number; next_cursor:string|null }
export interface NotificationPreferences {
  in_app_enabled:boolean; high_occupancy_enabled:boolean;
  high_occupancy_threshold:number; cooldown_minutes:number; favorite_floors:number[];
}

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
export interface AssistantResult {
  room_id:string; name:string; building:string; floor:number; block:string; capacity:number;
  occupancy:number; occupancy_percentage:number; available_capacity:number;
  status:CameraStatus; observed_at:string; reason:string;
}
export interface AssistantAppliedFilters {
  buildings:string[]; floors:number[]; blocks:string[];
  maximum_occupancy_percentage:number|null; minimum_available_capacity:number|null; limit:number;
}
export interface AssistantQueryResponse {
  conversation_id:string; answer:string; results:AssistantResult[];
  applied_filters:AssistantAppliedFilters; data_timestamp:string; warnings:string[];
}
export interface AssistantConversationSummary {
  id:string; title:string|null; created_at:string; updated_at:string; message_count:number;
}
export interface AssistantConversationListResponse {
  items:AssistantConversationSummary[]; page:number; limit:number; next_page:number|null;
}
export interface AssistantMessage {
  id:string; role:"user"|"assistant"; content:string;
  structured_results:{results?:AssistantResult[];data_timestamp?:string;warnings?:string[]}|null;
  created_at:string;
}
export interface AssistantConversation {
  id:string; title:string|null; created_at:string; updated_at:string; messages:AssistantMessage[];
}
export interface ApiErrorBody { code: string; message: string; details?: Record<string, unknown> }
export interface ApiErrorResponse { error: ApiErrorBody }
