import { Route, Routes } from "react-router-dom";
import { AppLayout } from "./AppLayout";
import { NotFound } from "../components/feedback/NotFound";
import { DashboardPage } from "../pages/DashboardPage";
import { RoomDetailPage } from "../pages/RoomDetailPage";
import { WelcomePage } from "../pages/WelcomePage";
import { AuthPage } from "../pages/AuthPage";
import { ProtectedRoute } from "../auth/ProtectedRoute";

export function App() {
  return (
    <Routes>
      <Route index element={<WelcomePage />} />
      <Route path="login" element={<AuthPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="rooms/:roomId" element={<RoomDetailPage />} />
        </Route>
      </Route>
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
