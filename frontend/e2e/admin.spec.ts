import { expect, test } from "@playwright/test";
import { expectToast, login, logout, sql, USERS } from "./helpers";

/** FR-ADM-01, BR-12 maker-checker; UC-02 users and roles; FR-ADM-02 integration status. */
test.describe("Administration", () => {
  test("policy change is proposed as DRAFT and cannot be self-approved", async ({ page }) => {
    await login(page, USERS.bankAdmin);
    await page.goto("/admin/policies");
    const card = page.getByTestId("policy-GRIEVANCE_SLA");
    await expect(card.getByText(/In force: v\d+/)).toBeVisible();
    await card.getByRole("button", { name: "Propose change" }).click();
    await page.getByLabel(/Policy value/).fill("{ not json");
    await expect(page.getByText(/Invalid JSON/)).toBeVisible();
    await page.getByLabel(/Policy value/).fill('{ "days": 14 }');
    await page.getByLabel(/Reason for change/).fill("E2E: client asked for a 14-day target");
    await page.getByRole("button", { name: "Submit for approval" }).click();
    await expectToast(page, /must approve/);
    const draft = sql(`select version from policy_configs where key = 'GRIEVANCE_SLA' and status = 'DRAFT' order by version desc limit 1`);
    expect(Number(draft)).toBeGreaterThan(0);
    const row = card.getByRole("listitem").filter({ hasText: `v${draft}` });
    await expect(row.getByRole("button", { name: "Approve" })).toBeDisabled();
    await expect(row.getByRole("button", { name: "Reject" })).toBeDisabled();
    await logout(page);

    // A different authorised user (checker) decides. Rejecting keeps reruns clean; approval is covered by the API tests.
    await login(page, USERS.bankAdmin2);
    await page.goto("/admin/policies");
    await page.getByTestId("policy-GRIEVANCE_SLA").getByRole("listitem").filter({ hasText: `v${draft}` }).getByRole("button", { name: "Reject" }).click();
    await page.getByLabel("Reason").fill("E2E checker review: not agreed");
    await page.getByRole("dialog").getByRole("button", { name: "Reject" }).click();
    await expectToast(page, /rejected/);
    expect(sql(`select status from policy_configs where key = 'GRIEVANCE_SLA' and version = ${draft}`)).toBe("REJECTED");
    expect(sql(`select count(*) from audit_events where action = 'policy.rejected' and target_label = 'GRIEVANCE_SLA v${draft}'`)).toBe("1");
  });

  test("users, roles and integrations pages load real data", async ({ page }) => {
    await login(page, USERS.bankAdmin);
    await page.goto("/admin/users");
    await expect(page.getByRole("table", { name: "Users" })).toBeVisible();
    await expect(page.getByText(USERS.loanOps)).toBeVisible();
    await page.goto("/admin/integrations");
    await expect(page.getByText(/MOCK provider - not a live integration/).first()).toBeVisible();
  });

  test("a field officer cannot reach administration", async ({ page }) => {
    await login(page, USERS.field);
    await page.goto("/admin/policies");
    await expect(page.getByText("This area is not available for your role")).toBeVisible();
  });
});
