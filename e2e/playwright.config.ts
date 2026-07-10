import { defineConfig, devices } from "@playwright/test";
import { fileURLToPath } from "node:url";

const webDirectory = fileURLToPath(new URL("../apps/web", import.meta.url));
const liveBaseUrl = process.env.E2E_BASE_URL;

export default defineConfig({
  testDir: ".",
  fullyParallel: true,
  forbidOnly: true,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: liveBaseUrl ?? "http://127.0.0.1:4173",
    trace: "retain-on-failure",
  },
  webServer: liveBaseUrl ? undefined : {
    command: "npm run dev -- --host 127.0.0.1 --port 4173",
    cwd: webDirectory,
    url: "http://127.0.0.1:4173",
    reuseExistingServer: false,
  },
  projects: [
    { name: "mobile-chromium", use: { ...devices["Pixel 7"] } },
    { name: "desktop-chromium", use: { ...devices["Desktop Chrome"] } },
  ],
});
