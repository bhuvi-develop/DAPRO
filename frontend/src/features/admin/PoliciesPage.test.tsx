import { screen, within } from "@testing-library/react";
import { Perm } from "@/app/guards";
import { mockApi, renderPage, signIn } from "@/test/render";
import PoliciesPage from "./PoliciesPage";

const base = { description: "Grievance response target", approval_label: "DEMO_FIXTURE", effective_from: "2026-01-01", approved_by: null, created_at: "2026-11-01T00:00:00Z" };
const rows = [
  { ...base, id: "p2", key: "GRIEVANCE_SLA", version: 2, value: { days: 10 }, status: "DRAFT", approval_label: "PENDING_APPROVAL", created_by: "u-1" },
  { ...base, id: "p1", key: "GRIEVANCE_SLA", version: 1, value: { days: 15 }, status: "ACTIVE", created_by: "u-9" },
];

afterEach(() => vi.unstubAllGlobals());

describe("Policy configuration", () => {
  it("shows the version in force and blocks the maker from deciding their own draft (maker-checker)", async () => {
    signIn({ id: "u-1", permissions: ["policy:read", "policy:manage"] });
    mockApi({ "GET /admin/policies": rows });
    renderPage(<PoliciesPage />);
    const card = await screen.findByTestId("policy-GRIEVANCE_SLA");
    expect(within(card).getByText("In force: v1")).toBeInTheDocument();
    expect(within(card).getByText(/"days": 15/)).toBeInTheDocument();
    expect(within(card).getByRole("button", { name: "Approve" })).toBeDisabled();
    expect(within(card).getByRole("button", { name: "Reject" })).toBeDisabled();
  });

  it("lets a different manager approve, and hides actions from read-only users", async () => {
    signIn({ id: "u-2", permissions: ["policy:read", "policy:manage"] });
    mockApi({ "GET /admin/policies": rows });
    const { unmount } = renderPage(<PoliciesPage />);
    expect(await screen.findByRole("button", { name: "Approve" })).toBeEnabled();
    unmount();
    signIn({ id: "u-3", permissions: ["policy:read"] });
    renderPage(<PoliciesPage />);
    await screen.findByTestId("policy-GRIEVANCE_SLA");
    expect(screen.queryByRole("button", { name: "Approve" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Propose change/ })).not.toBeInTheDocument();
  });
});

describe("Permission guard", () => {
  it("explains a missing permission instead of rendering the page", () => {
    signIn({ permissions: ["student:read"] });
    renderPage(<Perm any={["policy:read"]}><p>secret</p></Perm>);
    expect(screen.queryByText("secret")).not.toBeInTheDocument();
    expect(screen.getByText("This area is not available for your role")).toBeInTheDocument();
  });
});
