import * as React from "react";
import { render } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { vi } from "vitest";
import { useAuth, type Me } from "@/auth/store";
import { TooltipProvider } from "@/components/ui/menu";

export function makeMe(over: Partial<Me> = {}): Me {
  return {
    id: "u-1", email: "user@test.demo", full_name: "Test User", title: null, roles: ["LOAN_OPS"], permissions: [], mfa_enabled: false,
    org: { id: "org-1", name: "Test Bank", type: "BANK" }, unit: null, student_id: null,
    tenant: { id: "t-1", name: "Test", code: "TST", environment: "test" },
    environment: { env: "test", demo: true, bank_adapter: "mock", email_mode: "mock", sms_mode: "mock", location_capture: false },
    last_login_at: null, timezone: "Asia/Kolkata", ...over,
  };
}

export function signIn(over: Partial<Me> = {}) {
  useAuth.setState({ token: "test-token", me: makeMe(over), status: "authenticated" });
}

type Handler = (url: string, init?: RequestInit) => unknown;

/** Routes fetch calls by "METHOD /path" prefix to JSON responses; records every call for assertions. */
export function mockApi(routes: Record<string, Handler | unknown>) {
  const calls: { method: string; url: string; body: unknown }[] = [];
  const fn = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input).replace(/^\/api\/v1/, "");
    const method = (init?.method ?? "GET").toUpperCase();
    calls.push({ method, url, body: init?.body ? JSON.parse(String(init.body)) : undefined });
    const key = Object.keys(routes).sort((a, b) => b.length - a.length).find((k) => `${method} ${url}`.startsWith(k));
    if (!key) return new Response(JSON.stringify({ error: { code: "NOT_FOUND", message: `No mock for ${method} ${url}` } }), { status: 404, headers: { "content-type": "application/json" } });
    const h = routes[key];
    const out = typeof h === "function" ? (h as Handler)(url, init) : h;
    if (out instanceof Response) return out;
    return new Response(JSON.stringify(out), { status: method === "POST" ? 201 : 200, headers: { "content-type": "application/json" } });
  });
  vi.stubGlobal("fetch", fn);
  return { fn, calls };
}

export function renderPage(ui: React.ReactElement, { path = "/", route = "/" }: { path?: string; route?: string } = {}) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <TooltipProvider>
        <MemoryRouter initialEntries={[route]}>
          <Routes><Route path={path} element={ui} /><Route path="*" element={<div data-testid="navigated" />} /></Routes>
        </MemoryRouter>
      </TooltipProvider>
    </QueryClientProvider>,
  );
}
