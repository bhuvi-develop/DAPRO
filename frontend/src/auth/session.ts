import { api, refreshAccessToken } from "@/api/client";
import { useAuth, type Me } from "@/auth/store";

export async function loadMe() {
  const me = await api<Me>("/auth/me");
  useAuth.getState().setMe(me);
  return me;
}

/** On page load, silently restore the session from the HttpOnly refresh cookie. */
export async function bootstrapSession() {
  const ok = await refreshAccessToken();
  if (!ok) {
    useAuth.getState().setStatus("anonymous");
    return;
  }
  try {
    await loadMe();
  } catch {
    useAuth.getState().clear();
  }
}

export async function signOut() {
  try {
    await api("/auth/logout", { method: "POST" });
  } catch {
    await fetch("/api/v1/auth/logout-cookie", { method: "POST", credentials: "include" });
  }
  useAuth.getState().clear();
}
