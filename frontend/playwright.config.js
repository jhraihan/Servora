import { defineConfig } from "@playwright/test";

const BACKEND_PORT = process.env.E2E_BACKEND_PORT || "8100";
const FRONTEND_PORT = process.env.E2E_FRONTEND_PORT || "5174";
const PYTHON = process.platform === "win32" ? "venv\\Scripts\\python.exe" : "venv/bin/python";

export default defineConfig({
  testDir: "./e2e",
  globalTeardown: "./e2e/teardown.js",
  timeout: 120_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: `http://127.0.0.1:${FRONTEND_PORT}`,
    viewport: { width: 360, height: 740 },
    isMobile: true,
    hasTouch: true,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  webServer: [
    {
      command: `${PYTHON} manage.py runserver ${BACKEND_PORT} --noreload`,
      cwd: "../backend",
      url: `http://127.0.0.1:${BACKEND_PORT}/api/v1/categories/`,
      reuseExistingServer: false,
      timeout: 60_000,
    },
    {
      command: `npx vite --host 127.0.0.1 --port ${FRONTEND_PORT} --strictPort`,
      url: `http://127.0.0.1:${FRONTEND_PORT}`,
      env: { BACKEND_URL: `http://127.0.0.1:${BACKEND_PORT}` },
      reuseExistingServer: false,
      timeout: 60_000,
    },
  ],
});
