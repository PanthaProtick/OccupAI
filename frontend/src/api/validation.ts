import type { AppNotification, CameraStatus, HistoryMetric, HistoryRange, HistoryResponse, NotificationPreferences, NotificationsResponse, Occupancy, OccupancyListResponse, OccupancyResponse, Profile, Room, RoomResponse, RoomsResponse } from "./types";

type Json = Record<string, unknown>;
const object = (v: unknown): v is Json => typeof v === "object" && v !== null && !Array.isArray(v);
const text = (v: unknown): v is string => typeof v === "string";
const finite = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);
const integer = (v: unknown): v is number => Number.isInteger(v) && (v as number) >= 0;
const nullableNumber = (v: unknown): v is number | null => v === null || finite(v);
const status = (v: unknown): v is CameraStatus => v === "online" || v === "stale" || v === "offline";
const range = (v: unknown): v is HistoryRange => v === "hour" || v === "day" || v === "week";
const metric = (v: unknown): v is HistoryMetric => v === "occupancy" || v === "percentage";
const timestamp = (v: unknown): v is string => text(v) && !Number.isNaN(Date.parse(v));

function room(v: unknown): v is Room {
  return object(v) && text(v.room_id) && text(v.name) && integer(v.capacity) && v.capacity > 0 &&
    text(v.building) && integer(v.floor) && text(v.camera_id) && /^cam_\d{3}$/.test(v.camera_id) && text(v.behavior_profile);
}
function occupancy(v: unknown): v is Occupancy {
  return object(v) && text(v.camera_id) && /^cam_\d{3}$/.test(v.camera_id) && text(v.room_id) &&
    nullableNumber(v.occupancy) && nullableNumber(v.raw_occupancy) && integer(v.capacity) && v.capacity > 0 &&
    nullableNumber(v.occupancy_percentage) && (v.occupancy_percentage === null || (v.occupancy_percentage >= 0 && v.occupancy_percentage <= 100)) &&
    status(v.status) && timestamp(v.updated_at);
}
const meta = (v: unknown): v is { count: number; generated_at?: string | null } => object(v) && integer(v.count) &&
  (v.generated_at === undefined || v.generated_at === null || timestamp(v.generated_at));

export function parseRooms(v: unknown): RoomsResponse {
  if (!object(v) || !Array.isArray(v.data) || !v.data.every(room) || !meta(v.meta) || v.meta.count !== v.data.length) throw new Error("Malformed rooms response");
  return v as unknown as RoomsResponse;
}
export function parseRoom(v: unknown): RoomResponse {
  if (!object(v) || !object(v.data) || !room(v.data) || !occupancy(v.data) || !(v.data.intensity === null || text(v.data.intensity))) throw new Error("Malformed room response");
  return v as unknown as RoomResponse;
}
export function parseOccupancyList(v: unknown): OccupancyListResponse {
  if (!object(v) || !Array.isArray(v.data) || !v.data.every(occupancy) || !meta(v.meta) || v.meta.count !== v.data.length) throw new Error("Malformed occupancy response");
  return v as unknown as OccupancyListResponse;
}
export function parseOccupancy(v: unknown): OccupancyResponse {
  if (!object(v) || !occupancy(v.data)) throw new Error("Malformed occupancy response");
  return v as unknown as OccupancyResponse;
}
export function parseHistory(v: unknown): HistoryResponse {
  if (!object(v) || !Array.isArray(v.data) || !v.data.every((p) => object(p) && timestamp(p.bucket_start) && finite(p.value) && p.value >= 0 && finite(p.coverage_percentage) && p.coverage_percentage >= 0 && p.coverage_percentage <= 100) ||
      !object(v.meta) || !text(v.meta.room_id) || !range(v.meta.range) || !metric(v.meta.metric) || !meta(v.meta) || v.meta.count !== v.data.length) throw new Error("Malformed history response");
  return v as unknown as HistoryResponse;
}
export function parseProfile(v: unknown): Profile {
  if (!object(v) || !text(v.id) || !text(v.name) || !text(v.email) ||
      !timestamp(v.created_at) || !timestamp(v.updated_at)) throw new Error("Malformed profile response");
  return v as unknown as Profile;
}
function notification(v: unknown): v is AppNotification {
  return object(v) && text(v.id) && text(v.type) && text(v.category) && text(v.title) &&
    text(v.message) && (v.room_id === null || text(v.room_id)) &&
    (v.suggested_room_id === null || text(v.suggested_room_id)) && nullableNumber(v.occupancy_percentage) &&
    timestamp(v.created_at) && (v.read_at === null || timestamp(v.read_at)) &&
    (v.dismissed_at === null || timestamp(v.dismissed_at));
}
export function parseNotifications(v: unknown): NotificationsResponse {
  if (!object(v) || !Array.isArray(v.items) || !v.items.every(notification) ||
      !integer(v.unread_count) || !(v.next_cursor === null || text(v.next_cursor))) {
    throw new Error("Malformed notifications response");
  }
  return v as unknown as NotificationsResponse;
}
export function parseNotification(v: unknown): AppNotification {
  if (!notification(v)) throw new Error("Malformed notification response");
  return v;
}
export function parseNotificationPreferences(v: unknown): NotificationPreferences {
  if (!object(v) || typeof v.in_app_enabled !== "boolean" ||
      typeof v.high_occupancy_enabled !== "boolean" || !integer(v.high_occupancy_threshold) ||
      v.high_occupancy_threshold < 50 || v.high_occupancy_threshold > 100 ||
      !integer(v.cooldown_minutes) || v.cooldown_minutes < 1) {
    throw new Error("Malformed notification preferences response");
  }
  return v as unknown as NotificationPreferences;
}
