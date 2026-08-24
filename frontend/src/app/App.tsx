import { Route, Routes } from "react-router-dom";
import { AppLayout } from "./AppLayout";
import { NotFound } from "../components/feedback/NotFound";
import { DashboardPage } from "../pages/DashboardPage";
import { RoomDetailPage } from "../pages/RoomDetailPage";

export function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<DashboardPage />} />
        <Route path="rooms/:roomId" element={<RoomDetailPage />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
