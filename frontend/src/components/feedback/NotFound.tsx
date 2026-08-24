import { Link } from "react-router-dom";

export function NotFound() {
  return (
    <section className="state-panel">
      <p className="eyebrow">404</p><h1>Page not found</h1>
      <p>The page you requested does not exist.</p>
      <Link className="button" to="/">Back to dashboard</Link>
    </section>
  );
}
