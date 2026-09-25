import { spawn } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "@playwright/test";

const TARGET_MS = 2500;
const RUNS = Number(process.env.LCP_RUNS || 5);
const BACKEND_PORT = 8101;
const PREVIEW_PORT = 4175;

const PROFILES = [
  {
    name: "Slow 4G",
    network: { offline: false, latency: 150 * 3.75, downloadThroughput: (1.6e6 / 8) * 0.9, uploadThroughput: (750e3 / 8) * 0.9 },
    gated: true,
  },
  {
    name: "Fast 4G",
    network: { offline: false, latency: 60 * 2.75, downloadThroughput: (9e6 / 8) * 0.9, uploadThroughput: (1.5e6 / 8) * 0.9 },
    gated: false,
  },
];
const CPU_SLOWDOWN = 4;
const GATED_PAGE = "home";

const here = dirname(fileURLToPath(import.meta.url));
const frontend = join(here, "..");
const backend = join(frontend, "..", "backend");
const python = process.platform === "win32"
  ? join(backend, "venv", "Scripts", "python.exe")
  : join(backend, "venv", "bin", "python");
const origin = `http://127.0.0.1:${PREVIEW_PORT}`;

function start(command, args, options) {
  const child = spawn(command, args, { stdio: "ignore", ...options });
  child.on("error", (error) => {
    console.error(`Could not start ${command}: ${error.message}`);
    process.exit(1);
  });
  return child;
}

async function waitFor(url) {
  const deadline = Date.now() + 60_000;
  while (Date.now() < deadline) {
    try {
      if ((await fetch(url)).ok) return;
    } catch {
      await new Promise((resolve) => setTimeout(resolve, 300));
    }
  }
  throw new Error(`${url} did not come up within 60s`);
}

async function firstId(path) {
  const body = await (await fetch(`${origin}/api/v1/${path}`)).json();
  const rows = Array.isArray(body) ? body : body.results;
  if (!rows?.length) throw new Error(`No rows at /api/v1/${path}; run manage.py seed_demo`);
  return rows[0].id;
}

function observeLcp() {
  window.__lcp = null;
  window.__cls = 0;
  new PerformanceObserver((list) => {
    for (const entry of list.getEntries()) {
      if (!entry.hadRecentInput) window.__cls += entry.value;
    }
  }).observe({ type: "layout-shift", buffered: true });
  new PerformanceObserver((list) => {
    for (const entry of list.getEntries()) {
      window.__lcp = {
        time: entry.startTime,
        element: entry.element ? entry.element.tagName.toLowerCase() : "",
        text: entry.element ? entry.element.textContent.trim().slice(0, 40) : "",
      };
    }
  }).observe({ type: "largest-contentful-paint", buffered: true });
}

async function measure(browser, path, ready, network) {
  const context = await browser.newContext({
    viewport: { width: 360, height: 740 },
    deviceScaleFactor: 2,
    isMobile: true,
    hasTouch: true,
  });
  const page = await context.newPage();
  const cdp = await context.newCDPSession(page);
  await cdp.send("Network.enable");
  await cdp.send("Network.setCacheDisabled", { cacheDisabled: true });
  await cdp.send("Network.emulateNetworkConditions", network);
  await cdp.send("Emulation.setCPUThrottlingRate", { rate: CPU_SLOWDOWN });
  await page.addInitScript(observeLcp);

  await page.goto(origin + path, { timeout: 60_000 });
  await page.locator(ready).first().waitFor({ timeout: 60_000 });
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(1000);
  const result = await page.evaluate(() => ({
    lcp: window.__lcp,
    cls: window.__cls,
    bytes: performance.getEntriesByType("resource")
      .concat(performance.getEntriesByType("navigation"))
      .reduce((sum, r) => sum + (r.transferSize || 0), 0),
  }));
  await context.close();
  if (!result.lcp) throw new Error(`${path} reported no LCP entry`);
  return result;
}

function median(values) {
  const ordered = [...values].sort((a, b) => a - b);
  return ordered[Math.floor(ordered.length / 2)];
}

const servers = [
  start(python, ["manage.py", "runserver", String(BACKEND_PORT), "--noreload"], { cwd: backend }),
  start(process.execPath, [
    join(frontend, "node_modules", "vite", "bin", "vite.js"),
    "preview", "--host", "127.0.0.1", "--port", String(PREVIEW_PORT), "--strictPort",
  ], { cwd: frontend, env: { ...process.env, BACKEND_URL: `http://127.0.0.1:${BACKEND_PORT}` } }),
];

let failed = false;
try {
  await waitFor(`http://127.0.0.1:${BACKEND_PORT}/api/v1/categories/`);
  await waitFor(origin);

  const service = await firstId("services/");
  const provider = await firstId(`providers/?service=${service}`);
  const pages = [
    ["home", "/", "#main h1"],
    ["services", "/services", '#main a[href^="/services/"]'],
    ["search results", `/providers?service=${service}`, '[data-testid="provider-card"]'],
    ["provider profile", `/providers/${provider}`, "#main h1"],
    ["login", "/login", "#main h1"],
  ];

  const browser = await chromium.launch();
  for (const profile of PROFILES) {
    const { latency, downloadThroughput } = profile.network;
    console.log(`
${profile.name}: ${latency}ms latency, ${((downloadThroughput * 8) / 1e6).toFixed(2)} Mbps, `
      + `${CPU_SLOWDOWN}x CPU slowdown, production build, cold cache, ${RUNS} runs`);
    console.log("page               median ms   worst ms   max CLS   KB moved  LCP element");
    for (const [label, path, ready] of pages) {
      const runs = [];
      for (let i = 0; i < RUNS; i += 1) runs.push(await measure(browser, path, ready, profile.network));
      const times = runs.map((r) => r.lcp.time);
      const typical = median(times);
      const worst = Math.max(...times);
      const last = runs[runs.length - 1];
      const cls = Math.max(...runs.map((r) => r.cls));
      const gated = profile.gated && label === GATED_PAGE;
      let verdict = "";
      if (gated) verdict = typical < TARGET_MS ? "  PASS" : "  FAIL";
      else if (typical >= TARGET_MS) verdict = "  over";
      if (gated && typical >= TARGET_MS) failed = true;
      console.log(
        `${label.padEnd(18)} ${typical.toFixed(0).padStart(9)} ${worst.toFixed(0).padStart(10)} ${cls.toFixed(3).padStart(9)} `
        + `${(last.bytes / 1024).toFixed(0).padStart(10)}  <${last.lcp.element}> ${last.lcp.text}${verdict}`,
      );
    }
  }
  await browser.close();
  console.log(`
PRD 12.1 gates the landing page's median on Slow 4G at ${TARGET_MS}ms: ${failed ? "MISSED" : "met"}.`);
} catch (error) {
  console.error(error.message);
  failed = true;
} finally {
  servers.forEach((child) => child.kill());
}
process.exit(failed ? 1 : 0);
