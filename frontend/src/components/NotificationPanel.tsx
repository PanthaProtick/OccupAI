import { AlertTriangle, Bell, CheckCircle2, Info, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { AppNotification } from "../api/types";
import { useAuth } from "../auth/session";

function relativeTime(timestamp: string): string {
  const seconds = Math.max(0, Math.round((Date.now() - Date.parse(timestamp)) / 1000));
  if (seconds < 60) return "Just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} hr ago`;
  return new Date(timestamp).toLocaleDateString();
}

export function NotificationPanel() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [isOpen, setIsOpen] = useState(false);
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [pendingAll, setPendingAll] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);

  const load = useCallback(async (signal?: AbortSignal) => {
    if (!user) return;
    setLoading(true);
    setError("");
    try {
      const response = await api.getNotifications({ signal });
      setNotifications(response.items);
      setUnreadCount(response.unread_count);
    } catch (value) {
      if (!(value instanceof ApiError && value.code === "cancelled")) {
        setError(value instanceof ApiError ? value.message : "Unable to load notifications.");
      }
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, [user]);

  useEffect(() => {
    setNotifications([]);
    setUnreadCount(0);
    setError("");
    if (!user) return;
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [user, load]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(event.target as Node)) setIsOpen(false);
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const markRead = async (notification: AppNotification) => {
    if (notification.read_at) return;
    try {
      const updated = await api.markNotificationRead(notification.id);
      setNotifications((items) => items.map((item) => item.id === updated.id ? updated : item));
      setUnreadCount((count) => Math.max(0, count - 1));
    } catch (value) {
      setError(value instanceof ApiError ? value.message : "Unable to update the notification.");
    }
  };

  const markAllRead = async () => {
    if (pendingAll) return;
    setPendingAll(true);
    setError("");
    try {
      await api.markAllNotificationsRead();
      const readAt = new Date().toISOString();
      setNotifications((items) => items.map((item) => item.read_at ? item : {...item, read_at: readAt}));
      setUnreadCount(0);
    } catch (value) {
      setError(value instanceof ApiError ? value.message : "Unable to mark notifications as read.");
    } finally {
      setPendingAll(false);
    }
  };

  const dismiss = async (notification: AppNotification) => {
    try {
      await api.dismissNotification(notification.id);
      setNotifications((items) => items.filter((item) => item.id !== notification.id));
      if (!notification.read_at) setUnreadCount((count) => Math.max(0, count - 1));
    } catch (value) {
      setError(value instanceof ApiError ? value.message : "Unable to dismiss the notification.");
    }
  };

  const openRoom = async (notification: AppNotification) => {
    await markRead(notification);
    const roomId = notification.suggested_room_id ?? notification.room_id;
    if (roomId) {
      setIsOpen(false);
      navigate(`/rooms/${encodeURIComponent(roomId)}`);
    }
  };

  return <div className="notification-wrapper" ref={panelRef}>
    <button className="header-icon-btn" onClick={() => setIsOpen((open) => !open)}
      aria-label="Notifications" aria-expanded={isOpen}>
      <Bell size={18} />
      {unreadCount > 0 && <span className="notification-badge">{unreadCount > 99 ? "99+" : unreadCount}</span>}
    </button>
    {isOpen && <div className="notification-dropdown">
      <div className="notification-header">
        <h3>Notifications</h3>
        {unreadCount > 0 && <button className="mark-read-btn" disabled={pendingAll} onClick={() => void markAllRead()}>
          {pendingAll ? "Updating…" : "Mark all read"}
        </button>}
      </div>
      <div className="notification-list">
        {loading && <div className="notification-empty" role="status">Loading notifications…</div>}
        {error && <div className="notification-empty notification-error" role="alert">{error} <button onClick={() => void load()}>Try again</button></div>}
        {!loading && !error && notifications.length === 0 && <div className="notification-empty">No notifications yet</div>}
        {!loading && notifications.map((notification) => <div key={notification.id}
          className={`notification-item ${notification.read_at ? "" : "unread"}`}>
          <button className="notification-main" onClick={() => void openRoom(notification)}
            aria-label={`Open ${notification.title}`}>
            <span className={`notification-icon type-${notification.type === "high_occupancy" ? "alert" : "info"}`}>
              {notification.type === "high_occupancy" ? <AlertTriangle size={16}/> :
                notification.category === "success" ? <CheckCircle2 size={16}/> : <Info size={16}/>}
            </span>
            <span className="notification-content">
              <strong>{notification.title}</strong>
              <span>{notification.message}</span>
              <small>{relativeTime(notification.created_at)}</small>
              {notification.suggested_room_id && <em>View suggested room</em>}
            </span>
          </button>
          <button className="notification-dismiss" aria-label={`Dismiss ${notification.title}`}
            onClick={() => void dismiss(notification)}><X size={14}/></button>
        </div>)}
      </div>
    </div>}
  </div>;
}
