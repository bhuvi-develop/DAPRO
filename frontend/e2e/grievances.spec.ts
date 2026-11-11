import { expect, test } from "@playwright/test";
import { borrowerAt, expectToast, login, logout, sql, sqlCount, uniq, USERS } from "./helpers";

/** US-05 / UC-33: a borrower disputes an amount; staff review, respond and resolve; the borrower sees the outcome. */
test.describe("Grievances end to end (portal -> staff -> portal)", () => {
  test("borrower raises a dispute, staff resolve it, outcome persists and is audited", async ({ page }) => {
    const b = borrowerAt("ANB");
    const subject = uniq("E2E amount already paid ");

    await login(page, b.email);
    await expect(page).toHaveURL(/\/portal/);
    await page.getByRole("link", { name: "My requests" }).click();
    await page.getByRole("button", { name: "Raise a request" }).click();
    await page.getByLabel("What is this about?").selectOption("AMOUNT_DISPUTE");
    await page.getByLabel(/Short summary/).fill(subject);
    await page.getByLabel(/^Details/).fill("I paid this EMI by UPI on the due date and still received a reminder.");
    await page.getByRole("button", { name: "Submit request" }).click();
    await expectToast(page, /received/);
    await expect(page.getByText(subject)).toBeVisible();

    const ref = sql(`select ref from grievances where subject = '${subject}'`);
    expect(ref).toMatch(/^GRV-/);
    expect(sql(`select channel || '|' || status from grievances where ref = '${ref}'`)).toBe("PORTAL|SUBMITTED");
    await logout(page);

    await login(page, USERS.manager);
    await page.goto(`/grievances?q=${ref}`);
    await page.getByRole("table", { name: "Grievances" }).getByText(ref).click();
    await expect(page.getByRole("heading", { name: new RegExp(ref) })).toBeVisible();
    await page.getByRole("button", { name: "Under Review" }).click();
    await page.getByRole("button", { name: "Confirm" }).click();
    await expectToast(page, /under review/i);
    await page.getByLabel("Add a response or internal note").fill("We are checking the payment with the bank.");
    await page.getByRole("button", { name: "Add", exact: true }).click();
    await expectToast(page, /Response added/);
    await page.getByRole("button", { name: "Resolved" }).click();
    await page.getByLabel(/Outcome for the borrower/).fill("The bank confirmed your UPI payment and corrected the record.");
    await page.getByRole("button", { name: "Confirm" }).click();
    await expectToast(page, /resolved/i);
    await page.reload();
    await expect(page.getByText("The bank confirmed your UPI payment").first()).toBeVisible();
    expect(sql(`select status from grievances where ref = '${ref}'`)).toBe("RESOLVED");
    expect(sqlCount(`select count(*) from audit_events where action = 'grievance.transition' and target_label = '${ref}'`)).toBe(2);
    await logout(page);

    await login(page, b.email);
    await page.goto("/portal/grievances");
    await page.getByText(subject).click();
    await expect(page.getByText("Outcome:")).toBeVisible();
    await expect(page.getByText("We are checking the payment with the bank.")).toBeVisible();
  });

  test("staff queue filters and validation errors are shown inline", async ({ page }) => {
    await login(page, USERS.loanOps);
    await page.goto("/grievances");
    await expect(page.getByRole("heading", { name: "Grievances and corrections" })).toBeVisible();
    await page.getByRole("combobox", { name: "Status" }).selectOption("");
    await expect(page.getByRole("table", { name: "Grievances" })).toBeVisible();
    await page.getByRole("button", { name: "Record grievance" }).click();
    await expect(page.getByRole("button", { name: "Record grievance" }).last()).toBeDisabled();
  });

  test("a borrower cannot open another borrower's grievance (own records only)", async ({ page }) => {
    const other = sql(`select g.id from grievances g where g.student_id <> '${borrowerAt("ANB").studentId}' limit 1`);
    test.skip(!other, "no grievance for another borrower in the dataset");
    await login(page, borrowerAt("ANB").email);
    await page.goto(`/portal/grievances?id=${other}`);
    await expect(page.getByText(/not found/i)).toBeVisible();
  });
});
