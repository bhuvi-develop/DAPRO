import { expect, test } from "@playwright/test";
import { login, sql, sqlCount, USERS, uniq } from "./helpers";

test.describe("Reports, exports and audit", () => {
  test("Journey 11: run a report, export it with a purpose, download, and the export is audited", async ({ page }) => {
    const purpose = uniq("Monthly portfolio review for credit committee E2E ");
    await login(page, USERS.manager);
    await page.goto("/reports");
    await page.locator('a[href="/reports/PORTFOLIO_SUMMARY"]').click();
    await expect(page.getByRole("heading", { name: "Portfolio summary" })).toBeVisible();
    await expect(page.getByText("Calculation definition")).toBeVisible();
    await expect(page.getByText("As of", { exact: true })).toBeVisible();
    await page.getByRole("button", { name: /export csv/i }).click();
    await page.getByLabel("Purpose of export").fill(purpose);
    await page.getByRole("button", { name: /create export/i }).click();
    const history = page.getByRole("table", { name: "Export history" });
    const row = history.getByRole("row").filter({ hasText: purpose });
    await expect(row.getByRole("button", { name: /download/i })).toBeVisible({ timeout: 45_000 });
    const [dl] = await Promise.all([page.waitForEvent("download"), row.getByRole("button", { name: /download/i }).click()]);
    expect(dl.suggestedFilename()).toMatch(/\.csv$/);
    await page.reload();
    await expect(page.getByRole("table", { name: "Export history" }).getByText(purpose)).toBeVisible();
    expect(sql(`select status from export_jobs where purpose = '${purpose}'`)).toBe("COMPLETED");
    expect(sqlCount(`select count(*) from audit_events where action = 'export.created' and payload->>'purpose' = '${purpose}'`)).toBe(1);
    expect(sqlCount(`select count(*) from audit_events where action = 'export.downloaded' and occurred_at > now() - interval '10 minutes'`)).toBeGreaterThan(0);
  });

  test("Field officer cannot use reports or exports", async ({ page }) => {
    await login(page, USERS.field);
    await page.goto("/reports");
    await expect(page.getByText("This area is not available for your role")).toBeVisible();
    await expect(page.getByRole("navigation", { name: "Main navigation" }).getByRole("link", { name: "Reports" })).toHaveCount(0);
  });

  test("Auditor verifies the audit hash chain and browses read-only events", async ({ page }) => {
    await login(page, USERS.auditor);
    await page.goto("/audit");
    await expect(page.getByRole("table", { name: "Audit events" })).toBeVisible();
    await page.getByRole("tab", { name: "Chain verification" }).click();
    await page.getByRole("button", { name: /run verification/i }).click();
    await expect(page.getByText("Chain verified", { exact: true })).toBeVisible();
    expect(sqlCount("select count(*) from audit_checkpoints where ok and verified_at > now() - interval '5 minutes'")).toBeGreaterThan(0);
    await page.getByRole("tab", { name: "Events" }).click();
    await page.getByRole("table", { name: "Audit events" }).getByRole("row").nth(1).click();
    await expect(page.getByText(/Audit events are append-only/)).toBeVisible();
    await expect(page.getByRole("button", { name: /edit|delete/i })).toHaveCount(0);
  });
});
