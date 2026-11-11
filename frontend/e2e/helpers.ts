import { execFileSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { expect, type Page } from "@playwright/test";

export const PASSWORD = process.env.DAPRO_DEMO_PASSWORD ?? "";
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");

export const USERS = {
  platform: "platform.admin@dapro.demo", collegeAdmin: "priya.admin@nbit.demo", collegeOfficer: "officer@nbit.demo",
  rceAdmin: "admin@rce.demo", bankAdmin: "admin@anb.demo", bankAdmin2: "admin@mfb.demo", loanOps: "ravi.ops@anb.demo", investigator: "investigator@anb.demo",
  manager: "head.followup@anb.demo", regionalManager: "meena.manager@anb.demo", field: "karthik.field@anb.demo",
  field2: "nithya.field@anb.demo", auditor: "sanjay.audit@anb.demo", mfbOps: "ops@mfb.demo",
} as const;

export async function login(page: Page, email: string) {
  await page.goto("/login");
  await page.getByLabel("Work email").fill(email);
  await page.locator("#password").fill(PASSWORD);
  await page.getByRole("button", { name: /sign in securely/i }).click();
  await page.waitForURL((u) => !u.pathname.startsWith("/login"), { timeout: 20_000 });
}

export async function logout(page: Page) {
  if (new URL(page.url()).pathname.startsWith("/portal")) {
    await page.getByRole("button", { name: /sign out/i }).click();
  } else {
    await page.getByRole("button", { name: "Account menu" }).click();
    await page.getByRole("menuitem", { name: /sign out/i }).click();
  }
  await page.waitForURL(/\/login/);
}

/** Direct PostgreSQL verification (owner role) - proves persistence independently of the UI and API. */
export function sql(query: string): string {
  const out = execFileSync("docker", ["compose", "exec", "-T", "postgres", "psql", "-U", "dapro_owner", "-d", "dapro", "-At", "-c", query], {
    cwd: ROOT, encoding: "utf-8",
  });
  return out.trim();
}

export function sqlCount(query: string): number {
  return Number(sql(query) || "0");
}

export async function expectToast(page: Page, text: RegExp | string) {
  await expect(page.locator("[data-sonner-toast]").filter({ hasText: text }).first()).toBeVisible();
}

export function uniq(prefix: string) {
  return `${prefix}${Date.now().toString(36).slice(-5).toUpperCase()}`;
}

/** Demo borrower login whose linked loan is held by the given bank (looked up, never hardcoded: the seed may vary). */
export function borrowerAt(bankCode: string): { email: string; studentId: string; name: string } {
  const row = sql(`select u.email || '|' || s.id || '|' || s.full_name from users u join students s on s.id = u.student_id
    join loan_accounts l on l.student_id = s.id and l.link_status = 'LINKED' join organizations o on o.id = l.bank_org_id
    where o.code = '${bankCode}' and u.status = 'ACTIVE' order by u.email limit 1`);
  const [email, studentId, name] = row.split("|");
  return { email: email!, studentId: studentId!, name: name! };
}
