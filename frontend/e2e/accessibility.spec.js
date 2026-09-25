import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const WCAG_AA = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"];
const RUN = Date.now().toString().slice(-8);

async function scan(page, label) {
  await page.waitForLoadState("networkidle");
  const results = await new AxeBuilder({ page }).withTags(WCAG_AA).analyze();
  const report = results.violations.map((v) => ({
    rule: v.id,
    impact: v.impact,
    help: v.help,
    nodes: v.nodes.slice(0, 3).map((n) => n.target.join(" ")),
  }));
  expect(report, `${label} has WCAG 2.1 AA violations`).toEqual([]);
}

async function register(page, name, phone, roleLabel) {
  await page.goto("/register");
  await page.getByText(roleLabel).click();
  await page.getByLabel("Full name").fill(name);
  await page.getByLabel("Mobile number").fill(phone);
  await page.getByLabel("Password").fill("Accessible1!");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByRole("heading", { name: "Verify your phone" })).toBeVisible();
  await scan(page, "OTP verification");
  await page.getByRole("button", { name: "Skip for now" }).click();
}

test("public pages meet WCAG 2.1 AA", async ({ page }) => {
  for (const [path, label] of [
    ["/", "home"],
    ["/services", "all services"],
    ["/services/electrical", "category"],
    ["/providers", "provider search"],
    ["/compare", "compare (empty)"],
    ["/login", "login"],
    ["/register", "register"],
    ["/nowhere", "not found"],
  ]) {
    await page.goto(path);
    await scan(page, label);
  }

  await page.goto("/providers");
  await page.getByRole("button", { name: /^Filters/ }).click();
  await scan(page, "provider search with filters open");

  const cards = page.getByTestId("provider-card");
  expect(await cards.count(), "no providers to scan; run manage.py seed_demo").toBeGreaterThan(0);
  await cards.first().getByRole("link", { name: "View" }).click();
  await page.getByRole("button", { name: "How trust is scored" }).click();
  await scan(page, "provider profile with trust factors open");
});

test("keyboard users can skip the header and always see focus", async ({ page }) => {
  await page.goto("/providers");
  await page.keyboard.press("Tab");
  const skip = page.getByRole("link", { name: "Skip to main content" });
  await expect(skip).toBeFocused();
  await expect(skip).toBeInViewport();

  await page.keyboard.press("Enter");
  await expect(page.locator("main")).toBeFocused();
  await page.keyboard.press("Tab");
  const outline = await page.evaluate(() => getComputedStyle(document.activeElement).outlineStyle);
  expect(await page.evaluate(() => document.activeElement.closest("main") !== null)).toBe(true);
  expect(outline).not.toBe("none");
});

test("customer and provider pages meet WCAG 2.1 AA", async ({ browser }) => {
  const customer = await (await browser.newContext()).newPage();
  await register(customer, `Rumana E2E ${RUN}`, `019${RUN}`, "Hire a provider");
  for (const [path, label] of [
    ["/request-service", "request wizard"],
    ["/my-requests", "my requests"],
    ["/my-bookings", "my bookings"],
  ]) {
    await customer.goto(path);
    await scan(customer, label);
  }
  await customer.getByRole("button", { name: "Menu" }).click();
  await scan(customer, "mobile menu open");

  const provider = await (await browser.newContext()).newPage();
  await register(provider, `Kamal E2E ${RUN}`, `017${RUN}`, "Offer my services");
  for (const [path, label] of [
    ["/provider/profile", "provider profile setup"],
    ["/provider/dashboard", "provider dashboard"],
    ["/provider/bookings", "provider jobs"],
    ["/provider/earnings", "provider earnings"],
    ["/provider/trust", "provider trust"],
  ]) {
    await provider.goto(path);
    await scan(provider, label);
  }
});
