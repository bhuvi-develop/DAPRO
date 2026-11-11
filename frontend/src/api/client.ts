import { useAuth } from "@/auth/store";

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public nextStep: string | null = null,
    public correlationId: string | null = null,
    public details: { field: string; message: string }[] = [],
  ) {
    super(message);
  }
}

type Options = { method?: string; body?: unknown; form?: FormData; headers?: Record<string, string>; signal?: AbortSignal };

let refreshing: Promise<boolean> | null = null;

export async function refreshAccessToken(): Promise<boolean> {
  if (!refreshing) {
    refreshing = (async () => {
      try {
        const r = await fetch("/api/v1/auth/refresh", { method: "POST", credentials: "include" });
        if (!r.ok) return false;
        const j = await r.json();
        useAuth.getState().setToken(j.access_token);
        return true;
      } catch {
        return false;
      } finally {
        setTimeout(() => (refreshing = null), 0);
      }
    })();
  }
  return refreshing;
}

async function raw(path: string, opts: Options, retry = true): Promise<Response> {
  const token = useAuth.getState().token;
  const headers: Record<string, string> = { Accept: "application/json", ...(opts.headers ?? {}) };
  if (token) headers.Authorization = `Bearer ${token}`;
  let body: BodyInit | undefined;
  if (opts.form) body = opts.form;
  else if (opts.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(opts.body);
  }
  const res = await fetch(`/api/v1${path}`, { method: opts.method ?? "GET", headers, body, credentials: "include", signal: opts.signal });
  if (res.status === 401 && retry && !path.startsWith("/auth/login")) {
    if (await refreshAccessToken()) return raw(path, opts, false);
    useAuth.getState().clear();
  }
  return res;
}

async function toError(res: Response): Promise<ApiError> {
  try {
    const j = await res.json();
    const e = j.error ?? {};
    return new ApiError(res.status, e.code ?? "HTTP_" + res.status, e.message ?? res.statusText, e.next_step ?? null,
      e.correlation_id ?? res.headers.get("X-Correlation-ID"), e.details ?? []);
  } catch {
    return new ApiError(res.status, "HTTP_" + res.status, res.statusText || "Request failed");
  }
}

export async function api<T = unknown>(path: string, opts: Options = {}): Promise<T> {
  const res = await raw(path, opts);
  if (!res.ok) throw await toError(res);
  if (res.status === 204) return undefined as T;
  const ct = res.headers.get("content-type") ?? "";
  return (ct.includes("application/json") ? res.json() : res.text()) as Promise<T>;
}

export async function download(path: string, fallbackName: string) {
  const res = await raw(path, {});
  if (!res.ok) throw await toError(res);
  const blob = await res.blob();
  const cd = res.headers.get("content-disposition") ?? "";
  const name = /filename="?([^";]+)"?/.exec(cd)?.[1] ?? fallbackName;
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}

export const get = <T,>(p: string, signal?: AbortSignal) => api<T>(p, { signal });
export const post = <T,>(p: string, body?: unknown, headers?: Record<string, string>) => api<T>(p, { method: "POST", body, headers });
export const patch = <T,>(p: string, body?: unknown, headers?: Record<string, string>) => api<T>(p, { method: "PATCH", body, headers });
export const del = <T,>(p: string) => api<T>(p, { method: "DELETE" });
export const upload = <T,>(p: string, form: FormData) => api<T>(p, { method: "POST", form });

export interface Page<T> { items: T[]; total: number; page: number; size: number }
