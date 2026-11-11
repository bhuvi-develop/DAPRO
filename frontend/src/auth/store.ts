import { create } from "zustand";

export interface Me {
  id: string;
  email: string;
  full_name: string;
  title: string | null;
  roles: string[];
  permissions: string[];
  mfa_enabled: boolean;
  org: { id: string; name: string; type: string };
  unit: { id: string; name: string; kind: string } | null;
  student_id: string | null;
  tenant: { id: string; name: string; code: string; environment: string };
  environment: { env: string; demo: boolean; bank_adapter: string; email_mode: string; sms_mode: string; location_capture: boolean };
  last_login_at: string | null;
  timezone: string;
}

interface AuthState {
  token: string | null;
  me: Me | null;
  status: "booting" | "anonymous" | "authenticated";
  setToken: (t: string | null) => void;
  setMe: (m: Me | null) => void;
  setStatus: (s: AuthState["status"]) => void;
  clear: () => void;
}

/** Access token lives in memory only (LLD section 8); the refresh token is an HttpOnly cookie. */
export const useAuth = create<AuthState>((set) => ({
  token: null,
  me: null,
  status: "booting",
  setToken: (token) => set({ token }),
  setMe: (me) => set({ me, status: me ? "authenticated" : "anonymous" }),
  setStatus: (status) => set({ status }),
  clear: () => set({ token: null, me: null, status: "anonymous" }),
}));

/** UI permission check - for clarity only; the API remains the authority (FR-IAM-02). */
export function useCan() {
  const perms = useAuth((s) => s.me?.permissions);
  return (p: string | string[]) => {
    if (!perms) return false;
    const list = Array.isArray(p) ? p : [p];
    return list.some((x) => perms.includes(x));
  };
}
