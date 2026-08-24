import type { CameraStatus } from "../../api/types";
import { formatStatus } from "../../utils/formatters";
export function StatusBadge({ status }: { status: CameraStatus }) { return <span className={`status status--${status}`}><span aria-hidden="true">●</span> {formatStatus(status)}</span>; }
