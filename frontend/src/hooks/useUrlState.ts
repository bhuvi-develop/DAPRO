import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";

/** Filters live in the URL so dashboard KPIs can deep-link into pre-filtered module pages. */
export function useUrlState<T extends Record<string, string | undefined>>(defaults: T) {
  const [sp, setSp] = useSearchParams();
  const state = useMemo(() => {
    const out: Record<string, string | undefined> = { ...defaults };
    sp.forEach((v, k) => (out[k] = v));
    return out as T & { page?: string; size?: string };
  }, [sp, defaults]);
  const update = useCallback(
    (patch: Partial<Record<string, string | undefined | null>>, resetPage = true) => {
      setSp((prev) => {
        const next = new URLSearchParams(prev);
        for (const [k, v] of Object.entries(patch)) {
          if (v === undefined || v === null || v === "") next.delete(k);
          else next.set(k, v);
        }
        if (resetPage && !("page" in patch)) next.delete("page");
        return next;
      }, { replace: true });
    },
    [setSp],
  );
  const page = Number(state.page ?? 1) || 1;
  const size = Number(state.size ?? 25) || 25;
  return { state, update, page, size };
}
