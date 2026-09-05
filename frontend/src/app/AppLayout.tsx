import { LogOut, User } from "lucide-react";
import { Link, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/session";
import { NotificationPanel } from "../components/NotificationPanel";

export function AppLayout() {
  const navigate = useNavigate();
  const {logout}=useAuth();
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">Skip to main content</a>
      <header className="site-header">
        <Link className="brand" to="/dashboard" aria-label="OccupAI dashboard">
          <span className="brand__mark"><img src="/occupai-logo.png" alt="" /></span>
          <span className="brand__name">Occup<span>AI</span></span>
        </Link>
        <nav className="site-nav" aria-label="Dashboard sections">
          <a href="#overview">Overview</a>
          <a href="#floor-map">Floor map</a>
          <a href="#rooms">Rooms</a>
        </nav>
        <div className="site-header__actions">
          <p className="site-header__context"><span /> Campus live</p>
          <NotificationPanel />
          <Link to="/profile" className="header-icon-btn profile-link" aria-label="Profile"><User size={18} /></Link>
          <button className="logout-button" onClick={async () => { await logout(); navigate("/"); }} aria-label="Log out"><LogOut size={16} /><span>Log out</span></button>
        </div>
      </header>
      <main className="page-container" id="main-content">
        <Outlet />
      </main>
      <footer className="site-footer"><strong>OccupAI</strong><span>Smarter space decisions, powered by live campus data.</span></footer>
    </div>
  );
}
