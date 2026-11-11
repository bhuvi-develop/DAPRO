import { ApiError, get, post } from "./client";
import { useAuth } from "@/auth/store";
import { mockApi, signIn } from "@/test/render";

// The client reuses an in-flight refresh until a setTimeout(0) reset; let it settle between tests.
afterEach(async () => { await new Promise((r) => setTimeout(r, 0)); vi.unstubAllGlobals(); useAuth.getState().clear(); });

describe("API client", () => {
  it("sends the in-memory bearer token and JSON bodies", async () => {
    signIn();
    const { fn, calls } = mockApi({ "POST /grievances": { id: "g1" } });
    await post("/grievances", { subject: "x" });
    const init = fn.mock.calls[0]![1] as RequestInit;
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer test-token");
    expect(calls[0]).toMatchObject({ method: "POST", url: "/grievances", body: { subject: "x" } });
  });

  it("maps the error envelope to ApiError with next step and correlation id", async () => {
    signIn();
    mockApi({ "GET /loans/1": new Response(JSON.stringify({ error: { code: "FORBIDDEN", message: "Not in your scope", next_step: "Ask an admin", correlation_id: "c-9" } }), { status: 403, headers: { "content-type": "application/json" } }) });
    const err = await get("/loans/1").catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err).toMatchObject({ status: 403, code: "FORBIDDEN", message: "Not in your scope", nextStep: "Ask an admin", correlationId: "c-9" });
  });

  it("refreshes once on 401 and retries the original request", async () => {
    signIn();
    let n = 0;
    mockApi({
      "GET /me": () => (n++ === 0 ? new Response("{}", { status: 401 }) : { ok: true }),
      "POST /auth/refresh": { access_token: "fresh-token" },
    });
    await expect(get("/me")).resolves.toEqual({ ok: true });
    expect(useAuth.getState().token).toBe("fresh-token");
  });

  it("clears the session when the refresh fails", async () => {
    signIn();
    mockApi({ "GET /me": new Response("{}", { status: 401 }), "POST /auth/refresh": new Response("{}", { status: 401 }) });
    await expect(get("/me")).rejects.toBeInstanceOf(ApiError);
    expect(useAuth.getState().status).toBe("anonymous");
  });
});
