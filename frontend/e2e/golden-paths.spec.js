import { expect, test } from "@playwright/test";

const RUN = Date.now().toString().slice(-8);
const PROVIDER = { name: `Kamal E2E ${RUN}`, phone: `017${RUN}`, password: "GoldenPath1!" };
const CUSTOMER = { name: `Rumana E2E ${RUN}`, phone: `019${RUN}`, password: "GoldenPath1!" };
const ADDRESS = `House ${RUN.slice(-3)}, Road 5, Dhanmondi`;
const SERVICE_OPTION = "AC servicing — AC & Refrigeration";

async function expectNoHorizontalScroll(page) {
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow, `page ${page.url()} scrolls sideways at 360px`).toBeLessThanOrEqual(0);
}

async function register(page, { name, phone, password }, roleLabel) {
  await page.goto("/register");
  await page.getByText(roleLabel).click();
  await page.getByLabel("Full name").fill(name);
  await page.getByLabel("Mobile number").fill(phone);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByRole("heading", { name: "Verify your phone" })).toBeVisible();
  await page.getByRole("button", { name: "Skip for now" }).click();
}

test("customer books and reviews; provider accepts and completes", async ({ browser }) => {
  const providerContext = await browser.newContext();
  const customerContext = await browser.newContext();
  const provider = await providerContext.newPage();
  const customer = await customerContext.newPage();

  await test.step("provider signs up and sets up a findable profile", async () => {
    await register(provider, PROVIDER, "Offer my services");
    await expect(provider).toHaveURL(/\/provider\/profile$/);
    await expect(provider.getByText("Profile setup · 0 of 4 done")).toBeVisible();
    await expectNoHorizontalScroll(provider);

    await provider.getByLabel("Add a service").selectOption({ label: SERVICE_OPTION });
    await provider.getByLabel("Your price (৳)").fill("1800");
    await provider.getByRole("button", { name: "Add", exact: true }).click();
    await expect(provider.getByText("৳1,800")).toBeVisible();

    await provider.getByText("Dhanmondi", { exact: true }).click();
    await provider.getByRole("button", { name: "Save areas" }).click();
    await expect(provider.getByText("Saved").first()).toBeVisible();

    for (const day of ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]) {
      await provider.getByLabel(day, { exact: true }).check();
    }
    await provider.getByRole("button", { name: "Save hours" }).click();
    await expect(provider.getByText("Profile setup · 3 of 4 done")).toBeVisible();
  });

  let providerUrl;

  await test.step("customer signs up and finds the provider by trust", async () => {
    await register(customer, CUSTOMER, "Hire a provider");
    await expect(customer).toHaveURL(/\/$/);
    await expectNoHorizontalScroll(customer);

    await customer.getByLabel("Service").selectOption({ label: SERVICE_OPTION });
    await customer.getByLabel("Area").selectOption({ label: "All of Dhanmondi" });
    await customer.getByRole("button", { name: "Find providers" }).click();

    const card = customer.getByTestId("provider-card").filter({ hasText: PROVIDER.name });
    await expect(card).toBeVisible();
    await expect(card.getByText("Unverified")).toBeVisible();
    await expect(card.getByText("৳1,800")).toBeVisible();
    await expectNoHorizontalScroll(customer);

    await card.getByRole("link", { name: "View" }).click();
    providerUrl = customer.url().split("?")[0];
    await expect(customer.getByRole("heading", { name: "Provider trust" })).toBeVisible();
    await expect(customer.getByText("Identity verified (NID)")).toBeVisible();
    await expectNoHorizontalScroll(customer);
  });

  await test.step("customer requests the job through the wizard", async () => {
    await customer.getByRole("link", { name: /^Request / }).click();
    await expect(customer.getByText("Step 2 of 6 · Where")).toBeVisible();

    await customer.getByLabel("Area").selectOption({ label: "All of Dhanmondi" });
    await customer.getByLabel("Full address").fill(ADDRESS);
    await customer.getByRole("button", { name: "Continue" }).click();

    await customer.getByLabel("Describe the problem").fill("The bedroom AC runs but does not cool at all.");
    await customer.getByRole("button", { name: "Continue" }).click();
    await customer.getByRole("button", { name: "Continue" }).click();

    await expect(customer.getByText(`Only ${PROVIDER.name}`)).toBeVisible();
    await customer.getByRole("button", { name: "Continue" }).click();
    await expectNoHorizontalScroll(customer);
    await customer.getByRole("button", { name: "Send request" }).click();

    await expect(customer).toHaveURL(/\/my-requests$/);
    await expect(customer.getByText("Request sent.")).toBeVisible();
    await expect(customer.getByTestId("request-row").first()).toContainText("Waiting for a provider");
  });

  await test.step("provider sees the request without the address, then accepts", async () => {
    await provider.getByRole("button", { name: "Menu" }).click();
    await provider.getByRole("link", { name: "Dashboard" }).click();
    const item = provider.getByTestId("inbox-item").first();
    await expect(item).toContainText("AC servicing");
    await expect(item).toContainText("Sent to you");
    await expect(item).not.toContainText(ADDRESS);
    await expect(item).toContainText("The exact address is shared once you accept.");
    await expectNoHorizontalScroll(provider);

    await item.getByRole("button", { name: "Accept job" }).click();
    await expect(provider).toHaveURL(/\/provider\/bookings\/\d+$/);
    await expect(provider.getByText(ADDRESS)).toBeVisible();
    await expect(provider.getByRole("link", { name: `+880${CUSTOMER.phone.slice(1)}` })).toBeVisible();
  });

  await test.step("provider starts and completes the job", async () => {
    await provider.getByRole("button", { name: "I have arrived — start job" }).click();
    await expect(provider.getByText("In progress").first()).toBeVisible();

    await expect(provider.getByLabel("Amount collected in cash (৳)")).toHaveValue("1800.00");
    await provider.getByRole("button", { name: "Mark job complete" }).click();
    await expect(provider.getByText("Awaiting confirmation").first()).toBeVisible();
    await expectNoHorizontalScroll(provider);
  });

  await test.step("customer confirms payment and leaves a sealed review", async () => {
    await customer.getByRole("button", { name: "Menu" }).click();
    await customer.getByRole("link", { name: "My bookings" }).click();
    await customer.getByTestId("booking-row").first().click();

    await expect(customer.getByRole("heading", { name: "Is the job done?" })).toBeVisible();
    await customer.getByRole("button", { name: "Confirm and pay" }).click();
    await expect(customer.getByText("Completed").first()).toBeVisible();

    await customer.getByRole("link", { name: "Leave a review" }).click();
    await expect(customer.getByText("Your review is sealed until both sides have rated.")).toBeVisible();
    await customer.getByTestId("overall-5").click();
    await customer.getByLabel("Comment (optional)").fill("Arrived on time and fixed it within the hour.");
    await expectNoHorizontalScroll(customer);
    await customer.getByRole("button", { name: "Submit review" }).click();

    await expect(customer.getByText(/Thanks for your review\. It will be published once/)).toBeVisible();
  });

  await test.step("the review stays hidden until the provider rates back", async () => {
    await customer.goto(providerUrl);
    await expect(customer.getByText("No published reviews yet.")).toBeVisible();
  });

  await test.step("provider rates the customer, which unseals the review", async () => {
    await provider.reload();
    await expect(provider.getByRole("heading", { name: "Rate this customer" })).toBeVisible();
    await provider.getByTestId("customer-rating-5").click();
    await provider.getByRole("button", { name: "Submit rating" }).click();
    await expect(provider.getByText(/You rated this customer/)).toBeVisible();
  });

  await test.step("the public profile now shows the review and the completed job", async () => {
    await customer.goto(providerUrl);
    await expect(customer.getByText("Arrived on time and fixed it within the hour.")).toBeVisible();
    await expect(customer.getByRole("heading", { name: "Reviews (1)" })).toBeVisible();

    const trust = customer.getByRole("region", { name: "Provider trust" });
    await expect(trust.getByText("Jobs completed").locator("..")).toContainText("1");
    await expect(trust.getByText("Completion rate").locator("..")).toContainText("100%");
  });

  await test.step("provider earnings reflect the cash job and the commission owed", async () => {
    await provider.goto("/provider/earnings");
    await expect(provider.getByText("Earned (gross)").locator("..")).toContainText("৳1,800");
    await expect(provider.getByText("You owe the platform").locator("..")).toContainText("৳216");
    await expectNoHorizontalScroll(provider);
  });

  await providerContext.close();
  await customerContext.close();
});
