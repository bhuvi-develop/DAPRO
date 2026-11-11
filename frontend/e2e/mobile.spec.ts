import { expect, test, type Page } from "@playwright/test";
import { borrowerAt, login, USERS } from "./helpers";

/** Field and borrower workflows must remain usable at phone width (NFR-USA, UC-28 mobile field visit). */
async function noHorizontalScroll(page: Page) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow).toBeLessThanOrEqual(1);
}

test.describe("Mobile layouts", () => {
  test("field officer visit list fits a 360px screen", async ({ page }) => {
    await login(page, USERS.field);
    await page.goto("/field");
    await expect(page.getByRole("heading", { name: "My field visits" })).toBeVisible();
    await noHorizontalScroll(page);
  });

  test("borrower portal pages fit a 360px screen", async ({ page }) => {
    await login(page, borrowerAt("ANB").email);
    for (const path of ["/portal", "/portal/profile", "/portal/grievances", "/portal/messages"]) {
      await page.goto(path);
      await expect(page.locator("main h1").first()).toBeVisible();
      await noHorizontalScroll(page);
    }
  });
});
