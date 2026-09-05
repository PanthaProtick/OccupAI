import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "./session";

export function ProtectedRoute() {
  const location = useLocation();
  const {user,loading}=useAuth();
  if(loading) return <p role="status">Checking your session…</p>;
  if (!user) {
    return <Navigate to="/login" replace state={{ from: `${location.pathname}${location.search}` }} />;
  }
  return <Outlet />;
}
