import { Link, useParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { ErrorState } from "../components/feedback/ErrorState";
import { LoadingState } from "../components/feedback/LoadingState";
import { NotFound } from "../components/feedback/NotFound";
import { HistoryPanel } from "../components/history/HistoryPanel";
import { OccupancyReading } from "../components/occupancy/OccupancyReading";
import { StatusBadge } from "../components/occupancy/StatusBadge";
import { useAsyncResource } from "../hooks/useAsyncResource";
import { formatTimestamp } from "../utils/formatters";
import { motion } from "framer-motion";

export function RoomDetailPage() {
  const { roomId = "" } = useParams();
  const result = useAsyncResource((signal) => api.getRoom(roomId, { signal }), [roomId]);
  if (result.loading && !result.data) return <LoadingState label="Loading room details" />;
  if (result.error && !result.data) {
    const notFound = result.error instanceof ApiError && result.error.status === 404;
    return notFound ? <NotFound /> : <ErrorState message={result.error.message} onRetry={result.retry} />;
  }
  if (!result.data) return null;
  const room = result.data.data;
  const dashboardSearch = new URLSearchParams({ building: room.building, floor: String(room.floor) }).toString();
  return <>
    <Link aria-label="Back to dashboard" className="back-link" to={{ pathname: "/dashboard", search: dashboardSearch }}>← Back to dashboard</Link>
    <motion.article initial={{opacity:0,y:30}} whileInView={{opacity:1,y:0}} viewport={{once:false,amount:.2}} transition={{duration:.65}} className="detail-card"><div><p className="eyebrow">{room.building} · Floor {room.floor}</p><h1>{room.name}</h1><p>Camera {room.camera_id} · {room.behavior_profile.replaceAll("_", " ")}</p></div><StatusBadge status={room.status}/><OccupancyReading data={room}/><dl><div><dt>Capacity</dt><dd>{room.capacity}</dd></div><div><dt>Intensity</dt><dd>{room.intensity ?? "Unavailable"}</dd></div><div><dt>Updated</dt><dd><time dateTime={room.updated_at}>{formatTimestamp(room.updated_at)}</time></dd></div></dl></motion.article>
    <HistoryPanel roomId={roomId}/>
  </>;
}
