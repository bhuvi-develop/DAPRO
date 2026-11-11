import { expect, test } from "@playwright/test";
import { borrowerAt, expectToast, login, sql, sqlCount, uniq } from "./helpers";

/** UC-34 borrower portal, UC-16 address update, UC-23 employment status (FR-BRW-01, FR-ADR-01..03, FR-EMP-02..07). */
test.describe("Borrower portal", () => {
  test("home shows the borrower's own bank loan with source and freshness", async ({ page }) => {
    const b = borrowerAt("ANB");
    await login(page, b.email);
    await expect(page).toHaveURL(/\/portal$/);
    await expect(page.getByRole("heading", { name: new RegExp(`Welcome, ${b.name.split(" ")[0]}`) })).toBeVisible();
    const loan = page.getByTestId("portal-loan").first();
    await expect(loan).toBeVisible();
    await expect(loan.getByText("Mock bank feed")).toBeVisible();
    await expect(loan.getByText(/read-only copy of bank records/)).toBeVisible();
  });

  test("address update is stored as borrower-reported and unverified, previous address kept", async ({ page }) => {
    const b = borrowerAt("ANB");
    const line1 = uniq("12 E2E Street ");
    const before = sqlCount(`select count(*) from student_addresses where student_id = '${b.studentId}'`);
    await login(page, b.email);
    await page.getByRole("link", { name: "My profile" }).click();
    await page.getByRole("button", { name: "Update address" }).click();
    await page.getByLabel(/Address line 1/).fill(line1);
    await page.getByLabel(/^City/).fill("Coimbatore");
    await page.getByLabel(/PIN code/).fill("64100");
    await expect(page.getByText("Enter a 6-digit PIN code")).toBeVisible();
    await expect(page.getByRole("button", { name: "Submit address" })).toBeDisabled();
    await page.getByLabel(/PIN code/).fill("641001");
    await page.getByRole("button", { name: "Submit address" }).click();
    await expectToast(page, /unverified/);
    await page.reload();
    await expect(page.getByText(line1)).toBeVisible();
    expect(sql(`select source_type || '|' || verification || '|' || is_current::text from student_addresses where line1 = '${line1}'`)).toBe("BORROWER_REPORTED|UNVERIFIED|true");
    expect(sqlCount(`select count(*) from student_addresses where student_id = '${b.studentId}'`)).toBe(before + 1);
  });

  test("messages list only shows the borrower's messages and labels mock delivery", async ({ page }) => {
    const b = borrowerAt("ANB");
    const n = sqlCount(`select count(*) from communications where student_id = '${b.studentId}' and recipient_type = 'BORROWER' and status in ('SENT','DELIVERED','QUEUED')`);
    await login(page, b.email);
    await page.getByRole("link", { name: "Messages" }).click();
    await expect(page.getByRole("heading", { name: "Messages" })).toBeVisible();
    if (n === 0) await expect(page.getByText("No messages yet")).toBeVisible();
    else await expect(page.getByText("Demo - not delivered").first()).toBeVisible();
  });

  test("a borrower is kept out of staff areas and staff APIs", async ({ page }) => {
    await login(page, borrowerAt("MFB").email);
    await page.goto("/students");
    await expect(page).toHaveURL(/\/portal$/);
    const status = await page.evaluate(async () => (await fetch("/api/v1/students", { credentials: "include" })).status);
    expect([401, 403]).toContain(status);
  });
});
