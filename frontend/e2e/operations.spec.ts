import { expect, test } from "@playwright/test";
import { login, sql, sqlCount, USERS } from "./helpers";

/** E1 Student 360, E3 risk review, E7 cases and field operations - smoke journeys against real data. */
test.describe("Students, risk and cases", () => {
  test("college admin searches students and opens Student 360 (access is logged)", async ({ page }) => {
    const s = sql(`select s.full_name || '|' || s.id from students s join organizations o on o.id = s.college_org_id where o.code = 'NBIT' order by s.dapro_ref limit 1`);
    const [name, id] = s.split("|");
    const before = sqlCount(`select count(*) from audit_events where target_id = '${id}'`);
    await login(page, USERS.collegeAdmin);
    await page.goto("/students");
    await expect(page.getByRole("table", { name: "Students" })).toBeVisible();
    await page.getByRole("textbox", { name: "Name, DAPRO ref or college ID" }).fill(name!);
    await page.getByRole("table", { name: "Students" }).getByText(name!).first().click();
    await expect(page).toHaveURL(new RegExp(`/students/${id}`));
    await expect(page.getByText(name!).first()).toBeVisible();
    await expect.poll(() => sqlCount(`select count(*) from audit_events where target_id = '${id}'`)).toBeGreaterThan(before);
  });

  test("register student form blocks submission with missing required fields", async ({ page }) => {
    await login(page, USERS.collegeAdmin);
    await page.goto("/students/new");
    await expect(page.getByRole("heading", { name: "Register student" })).toBeVisible();
    await page.getByRole("button", { name: "Register student" }).click();
    await expect(page).toHaveURL(/\/students\/new/);
  });

  test("manager sees the explainable risk queue and case list", async ({ page }) => {
    await login(page, USERS.manager);
    await page.goto("/risk");
    await expect(page.getByRole("heading", { name: "Risk review queue" })).toBeVisible();
    await expect(page.getByRole("table", { name: "Risk indicators" })).toBeVisible();
    await page.goto("/cases");
    const table = page.getByRole("table", { name: "Cases" });
    await expect(table).toBeVisible();
    const ref = sql(`select case_ref from cases c join organizations o on o.id = c.bank_org_id where o.code = 'ANB' order by c.created_at desc limit 1`);
    await page.goto(`/cases?q=${ref}`);
    await table.getByText(ref).click();
    await expect(page.getByRole("heading", { name: new RegExp(ref) })).toBeVisible();
    await expect(page.getByRole("tab", { name: /Timeline/ })).toBeVisible();
  });

  test("field officer sees only assigned visits", async ({ page }) => {
    await login(page, USERS.field);
    await page.goto("/field");
    await expect(page.getByRole("heading", { name: "My field visits" })).toBeVisible();
    await page.goto("/cases/new");
    await expect(page.getByText("This area is not available for your role")).toBeVisible();
  });
});
