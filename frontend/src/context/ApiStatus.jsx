import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { api } from "../lib/api.js";

const Ctx = createContext(null);

// Polls /api/health so the top bar can show the status pill + simulated clock.
// Pages that advance the stream push the fresh status via `setStream`.
export function ApiStatusProvider({ children }) {
  const [health, setHealth] = useState(null);
  const [online, setOnline] = useState(null); // null = unknown (first check pending)
  const [checkedAt, setCheckedAt] = useState(null);
  const timer = useRef(null);

  const refresh = useCallback(async () => {
    try {
      const h = await api.health();
      setHealth(h);
      setOnline(true);
    } catch {
      setOnline(false);
    } finally {
      setCheckedAt(Date.now());
    }
  }, []);

  useEffect(() => {
    refresh();
    timer.current = setInterval(refresh, 15000);
    const onVis = () => document.visibilityState === "visible" && refresh();
    document.addEventListener("visibilitychange", onVis);
    return () => {
      clearInterval(timer.current);
      document.removeEventListener("visibilitychange", onVis);
    };
  }, [refresh]);

  const setStream = useCallback((s) => {
    if (!s) return;
    setHealth((h) => ({ ...(h || {}), ...s }));
    setOnline(true);
  }, []);

  const value = useMemo(
    () => ({ health, online, checkedAt, refresh, setStream, markOffline: () => setOnline(false) }),
    [health, online, checkedAt, refresh, setStream],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export const useApiStatus = () => useContext(Ctx);
