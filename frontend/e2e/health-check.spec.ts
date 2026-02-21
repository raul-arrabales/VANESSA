import { expect, test } from "@playwright/test";

test("renders app shell and shows backend health success", async ({ page }) => {
  await page.route("**/health", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ status: "ok", service: "backend" }),
    });
  });

  await page.goto("/");

  await expect(page.getByRole("heading", { name: "VANESSA" })).toBeVisible();
  await expect(page.getByText("Backend status")).toBeVisible();

  await page.getByRole("button", { name: "Check backend" }).click();

  await expect(page.locator("strong[data-state='success']")).toContainText("SUCCESS");
  await expect(page.locator("pre")).toContainText('"status": "ok"');
  await expect(page.locator("pre")).toContainText('"service": "backend"');
});

test("shows clear error state when backend request fails", async ({ page }) => {
  await page.route("**/health", async (route) => {
    await route.abort("failed");
  });

  await page.goto("/");
  await page.getByRole("button", { name: "Check backend" }).click();

  await expect(page.locator("strong[data-state='error']")).toContainText("ERROR");
  await expect(page.getByText(/Request failed:/)).toBeVisible();
});
