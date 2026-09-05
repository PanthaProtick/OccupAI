import type { CameraStatus } from "../../api/types";
import { formatStatus } from "../../utils/formatters";
export function StatusBadge({ status }: { status: CameraStatus }) { return <span className={`status status--${status}`}><div className="status-dot" aria-hidden="true" /> {formatStatus(status)}</span>; }
