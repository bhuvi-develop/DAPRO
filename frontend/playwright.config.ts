import { defineConfig, devices } from "@playwright/test";

/** Browser acceptance against the real merged stack (docker compose, web on 8480). */
export default defineConfig({
  testDir: "./e2e",
  timeout: 90_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["list"], ["json", { outputFile: "test-results/results.json" }], ["html", { open: "never" }]],
  use: {
    baseURL: process.env.DAPRO_WEB_URL ?? "http://localhost:8480",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "off",
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } }, testIgnore: /mobile\.spec/ },
    { name: "mobile", use: { ...devices["Pixel 5"], viewport: { width: 360, height: 760 } }, testMatch: /mobile\.spec/ },
  ],
});
