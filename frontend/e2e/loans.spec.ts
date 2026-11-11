import { expect, test } from "@playwright/test";
import { login, sql, sqlCount, USERS, uniq } from "./helpers";

const ANB = "(select id from organizations where code = 'ANB' and tenant_id = (select id from tenants where code = 'DEMO'))";

test.describe("Loans and repayment", () => {
  test("Journey 3: link an unmatched bank loan, then it persists with schedule and audit", async ({ page }) => {
    const row = sql(`select m.bank_loan_ref || '|' || s.id from mock_bank_records m join students s on s.full_name = m.borrower_name and s.dob = m.borrower_dob and s.tenant_id = m.tenant_id
      where m.bank_org_id = ${ANB} and not exists (select 1 from loan_accounts l where l.bank_loan_ref = m.bank_loan_ref) limit 1`);
    test.skip(!row, "no unmatched ANB bank loan left in the demo dataset (reset demo data to rerun)");
    const [ref, studentId] = row.split("|");
    await login(page, USERS.loanOps);
    await page.goto(`/loans/link?student_id=${studentId}`);
    await page.getByLabel("Bank loan reference").fill(ref);
    await page.getByRole("button", { name: /validate and link/i }).click();
    await expect(page.getByText("Linked to bank loan")).toBeVisible();
    await page.getByRole("link", { name: /open loan details/i }).click();
    await expect(page.getByRole("heading", { name: ref })).toBeVisible();
    await page.reload();
    await expect(page.getByRole("heading", { name: ref })).toBeVisible();
    expect(sql(`select link_status || '|' || sync_state from loan_accounts where bank_loan_ref = '${ref}'`)).toBe("LINKED|CURRENT");
    expect(sqlCount(`select count(*) from audit_events where action = 'loan.linked' and target_label = '${ref}'`)).toBeGreaterThan(0);
  });

  test("Journey 4: loan detail shows bank schedule and transactions with source and freshness", async ({ page }) => {
    const id = sql(`select id from loan_accounts where bank_org_id = ${ANB} and repayment_status = 'OVERDUE' and sync_state = 'CURRENT' order by dpd desc limit 1`);
    await login(page, USERS.loanOps);
    await page.goto(`/loans/${id}`);
    await expect(page.getByText("MOCK bank feed - read only")).toBeVisible();
    await expect(page.getByText(/read-only mirror/i)).toBeVisible();
    await expect(page.getByRole("table", { name: "Repayment schedule" })).toBeVisible();
    await expect(page.getByRole("table", { name: "Repayment schedule" }).getByText("Overdue").first()).toBeVisible();
    await page.getByRole("tab", { name: "Transactions" }).click();
    await expect(page.getByRole("table", { name: "Bank transactions" })).toBeVisible();
    await expect(page.getByText("Mock bank feed").first()).toBeVisible();
  });

  test("Repayment monitoring honours dashboard deep links", async ({ page }) => {
    await login(page, USERS.loanOps);
    await page.goto("/repayments?repayment_status=OVERDUE");
    await expect(page.getByRole("heading", { name: "Repayment monitoring" })).toBeVisible();
    const table = page.getByRole("table", { name: "Repayment accounts" });
    await expect(table).toBeVisible();
    await expect(table.getByText("Current", { exact: true })).toHaveCount(0);
  });

  test("College admin sees loan linkage but bank amounts are restricted (AC-02)", async ({ page }) => {
    await login(page, USERS.collegeAdmin);
    await page.goto("/loans");
    await expect(page.getByRole("table", { name: "Loan accounts" })).toBeVisible();
    await expect(page.getByText("Restricted").first()).toBeVisible();
    await expect(page.getByRole("link", { name: /link a bank loan/i })).toHaveCount(0);
  });

  test("Reconciliation: confirming an ambiguous link records the human decision", async ({ page }) => {
    const item = sql(`select r.id from reconciliation_items r where r.kind = 'AMBIGUOUS_LINK' and r.status = 'OPEN' and r.bank_org_id = ${ANB} limit 1`);
    test.skip(!item, "no open ambiguous link in the demo dataset");
    const note = uniq("Identity confirmed against signed agreement E2E-");
    await login(page, USERS.loanOps);
    await page.goto("/reconciliation?kind=AMBIGUOUS_LINK");
    await page.getByRole("table", { name: "Reconciliation items" }).getByRole("row").nth(1).click();
    await page.getByLabel("Action").selectOption("CONFIRM_LINK");
    await page.getByLabel("Resolution and evidence").fill(note);
    await page.getByRole("button", { name: /record decision/i }).click();
    await expect(page.locator("[data-sonner-toast]").filter({ hasText: /closed and audited/i })).toBeVisible();
    expect(sql(`select status from reconciliation_items where resolution = '${note}'`)).toBe("RESOLVED");
  });
});
