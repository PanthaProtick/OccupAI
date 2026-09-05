import { Bell, CheckCircle2, AlertTriangle, Info, X } from "lucide-react";
import { useState, useRef, useEffect } from "react";

export interface AppNotification {
  id: string;
  type: "alert" | "info" | "success";
  message: string;
  time: string;
  read: boolean;
}

export function NotificationPanel() {
  const [isOpen, setIsOpen] = useState(false);
  const [notifications, setNotifications] = useState<AppNotification[]>([
    { id: "1", type: "alert", message: "High occupancy detected in Room 204", time: "2 min ago", read: false },
    { id: "2", type: "info", message: "Scheduled maintenance for HVAC system", time: "1 hour ago", read: false },
    { id: "3", type: "success", message: "Camera system calibration complete", time: "3 hours ago", read: true }
  ]);
  
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const unreadCount = notifications.filter(n => !n.read).length;

  const markAllRead = () => {
    setNotifications(notifications.map(n => ({ ...n, read: true })));
  };

  return (
    <div className="notification-wrapper" ref={panelRef}>
      <button 
        className="header-icon-btn" 
        onClick={() => setIsOpen(!isOpen)}
        aria-label="Notifications"
      >
        <Bell size={18} />
        {unreadCount > 0 && <span className="notification-badge">{unreadCount}</span>}
      </button>

      {isOpen && (
        <div className="notification-dropdown">
          <div className="notification-header">
            <h3>Notifications</h3>
            {unreadCount > 0 && (
              <button className="mark-read-btn" onClick={markAllRead}>Mark all read</button>
            )}
          </div>
          <div className="notification-list">
            {notifications.length === 0 ? (
              <div className="notification-empty">No new notifications</div>
            ) : (
              notifications.map(notif => (
                <div key={notif.id} className={`notification-item ${!notif.read ? 'unread' : ''}`}>
                  <div className={`notification-icon type-${notif.type}`}>
                    {notif.type === 'alert' && <AlertTriangle size={16} />}
                    {notif.type === 'success' && <CheckCircle2 size={16} />}
                    {notif.type === 'info' && <Info size={16} />}
                  </div>
                  <div className="notification-content">
                    <p>{notif.message}</p>
                    <span>{notif.time}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
