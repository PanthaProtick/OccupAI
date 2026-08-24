import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import type { Occupancy, Room } from "../api/types";

export interface RoomSnapshot { room: Room; occupancy: Occupancy }
export function useDashboard(refreshIntervalMs = 30_000) {
  const [data, setData] = useState<RoomSnapshot[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isRefreshing, setRefreshing] = useState(false);
  const [lastRefresh, setLastRefresh] = useState<string | null>(null);
  const active = useRef<Promise<void> | null>(null);
  const refresh = useCallback(() => {
    if (active.current) return active.current;
    setRefreshing(true); setError(null);
    const run = Promise.all([api.getRooms(), api.getOccupancy()]).then(([rooms, states]) => {
      const byCamera = new Map(states.data.map((item) => [item.camera_id, item]));
      const joined = rooms.data.map((room) => ({ room, occupancy: byCamera.get(room.camera_id) })).filter((item): item is RoomSnapshot => Boolean(item.occupancy));
      if (joined.length !== rooms.data.length) throw new Error("Some rooms are missing occupancy data.");
      setData(joined); setLastRefresh(new Date().toISOString());
    }).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Unable to load rooms.")).finally(() => { active.current = null; setRefreshing(false); });
    active.current = run; return run;
  }, []);
  useEffect(() => { void refresh(); }, [refresh]);
  useEffect(() => {
    const timer = window.setInterval(() => { if (!document.hidden) void refresh(); }, refreshIntervalMs);
    return () => window.clearInterval(timer);
  }, [refresh, refreshIntervalMs]);
  return { data, error, isRefreshing, lastRefresh, refresh };
}
