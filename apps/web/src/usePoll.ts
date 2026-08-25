import { useEffect, useState } from "react";

export function usePoll<T>(loader: () => Promise<T>, intervalMs: number, key = "poll"): {
  data: T | null;
  error: string | null;
} {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const tick = async () => {
      try {
        const next = await loader();
        if (!cancelled) {
          setData(next);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "request failed");
      }
    };
    void tick();
    const id = window.setInterval(() => void tick(), intervalMs);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
    // loader is read from the render that created this effect; key resets the poll.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [intervalMs, key]);

  return { data, error };
}
