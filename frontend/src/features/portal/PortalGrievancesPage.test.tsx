import { fireEvent, screen, waitFor } from "@testing-library/react";
import { mockApi, renderPage, signIn } from "@/test/render";
import PortalGrievancesPage from "./PortalGrievancesPage";

const G = { id: "g1", ref: "GRV-000123", category: "AMOUNT_DISPUTE", subject: "EMI already paid", status: "UNDER_REVIEW", priority: "MEDIUM", channel: "PORTAL",
  due_on: "2026-11-21", overdue: false, student_id: "s1", student_name: "Hari", dapro_ref: "DAP-1", owner_id: null, owner_name: null, case_id: null, loan_id: null,
  created_at: "2026-11-06T08:00:00Z", updated_at: "2026-11-06T08:00:00Z", resolved_at: null };

afterEach(() => vi.unstubAllGlobals());
beforeEach(() => signIn({ roles: ["BORROWER"], permissions: ["portal:self"], student_id: "s1" }));

describe("Borrower portal requests", () => {
  it("lists the borrower's own requests from the API", async () => {
    mockApi({ "GET /portal/grievances": { items: [G], total: 1, page: 1, size: 100 } });
    renderPage(<PortalGrievancesPage />);
    expect(await screen.findByText("EMI already paid")).toBeInTheDocument();
    expect(screen.getByText("GRV-000123")).toBeInTheDocument();
  });

  it("shows an empty state when there are no requests", async () => {
    mockApi({ "GET /portal/grievances": { items: [], total: 0, page: 1, size: 100 } });
    renderPage(<PortalGrievancesPage />);
    expect(await screen.findByText("You have not raised any requests")).toBeInTheDocument();
  });

  it("validates a correction request and submits it to the API", async () => {
    const { calls } = mockApi({
      "GET /portal/grievances": { items: [], total: 0, page: 1, size: 100 },
      "GET /portal/overview": { student: { id: "s1", name: "Hari", dapro_ref: "DAP-1", lifecycle_status: "EMPLOYED" }, loans: [] },
      "POST /portal/grievances": { ...G, id: "g2", ref: "GRV-000124", category: "DATA_CORRECTION" },
    });
    renderPage(<PortalGrievancesPage />, { route: "/?new=1&category=DATA_CORRECTION" });
    const submit = await screen.findByRole("button", { name: "Submit request" });
    fireEvent.change(screen.getByLabelText(/Short summary/), { target: { value: "Wrong mobile number" } });
    fireEvent.change(screen.getByLabelText(/^Details/), { target: { value: "My mobile number on record is outdated." } });
    expect(submit).toBeDisabled(); // correction field and value still missing
    fireEvent.change(screen.getByLabelText(/Detail to correct/), { target: { value: "primary_mobile" } });
    fireEvent.change(screen.getByLabelText(/Correct value/), { target: { value: "+919800000001" } });
    expect(submit).toBeEnabled();
    fireEvent.click(submit);
    await waitFor(() => expect(calls.some((c) => c.method === "POST")).toBe(true));
    expect(calls.find((c) => c.method === "POST")).toMatchObject({
      url: "/portal/grievances",
      body: { category: "DATA_CORRECTION", correction_field: "primary_mobile", correction_requested_value: "+919800000001", loan_id: null },
    });
  });

  it("shows the API error when the server rejects the request", async () => {
    mockApi({ "GET /portal/grievances": { items: [G], total: 1, page: 1, size: 100 },
      "GET /portal/grievances/g1": new Response(JSON.stringify({ error: { code: "NOT_FOUND", message: "Grievance not found" } }), { status: 404, headers: { "content-type": "application/json" } }) });
    renderPage(<PortalGrievancesPage />, { route: "/?id=g1" });
    expect(await screen.findByText("Grievance not found")).toBeInTheDocument();
  });
});
