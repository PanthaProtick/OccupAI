import { Navigate, Outlet, useLocation } from "react-router-dom";
import { hasActiveSession } from "./session";

export function ProtectedRoute() {
  const location = useLocation();
  if (!hasActiveSession()) {
    return <Navigate to="/login" replace state={{ from: `${location.pathname}${location.search}` }} />;
  }
  return <Outlet />;
}
