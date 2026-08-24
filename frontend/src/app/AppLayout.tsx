import { Link, Outlet } from "react-router-dom";

export function AppLayout() {
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">Skip to main content</a>
      <header className="site-header">
        <Link className="brand" to="/" aria-label="OccupAI dashboard">
          <span className="brand__mark" aria-hidden="true">O</span>
          <span>OccupAI</span>
        </Link>
        <p className="site-header__context">Campus occupancy</p>
      </header>
      <main className="page-container" id="main-content">
        <Outlet />
      </main>
      <footer className="site-footer">Occupancy insights for better spaces</footer>
    </div>
  );
}
