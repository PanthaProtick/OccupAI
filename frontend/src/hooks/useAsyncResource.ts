import { useCallback, useEffect, useRef, useState } from "react";
export function useAsyncResource<T>(loader: (signal: AbortSignal) => Promise<T>, keys: readonly unknown[]) {
  const [data, setData] = useState<T | null>(null); const [error, setError] = useState<Error | null>(null); const [loading, setLoading] = useState(true); const revision = useRef(0);
  const load = useCallback(() => { const current = ++revision.current; const controller = new AbortController(); setLoading(true); setError(null); loader(controller.signal).then((value) => { if (current === revision.current) setData(value); }).catch((reason: unknown) => { if (current === revision.current && !(reason instanceof Error && "code" in reason && reason.code === "cancelled")) setError(reason instanceof Error ? reason : new Error("Request failed.")); }).finally(() => { if (current === revision.current) setLoading(false); }); return () => controller.abort(); }, keys);
  useEffect(() => load(), [load]);
  return { data, error, loading, retry: load };
}
