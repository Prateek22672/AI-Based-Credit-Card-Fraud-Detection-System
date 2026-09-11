import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "../lib/api.js";

// Small async-state helper: { data, error, loading, offline, reload }.
export function useAsync(fn, deps = [], { enabled = true, keep = true } = {}) {
  const [state, setState] = useState({ data: null, error: null, loading: !!enabled });
  const fnRef = useRef(fn);
  fnRef.current = fn;
  const seq = useRef(0);

  const run = useCallback(async () => {
    const id = ++seq.current;
    setState((s) => ({ ...s, loading: true, error: null, data: keep ? s.data : null }));
    try {
      const data = await fnRef.current();
      if (id === seq.current) setState({ data, error: null, loading: false });
    } catch (error) {
      if (id === seq.current) setState((s) => ({ data: keep ? s.data : null, error, loading: false }));
    }
  }, [keep]);

  useEffect(() => {
    if (!enabled) return;
    run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, ...deps]);

  return { ...state, reload: run, offline: state.error instanceof ApiError && state.error.offline };
}
