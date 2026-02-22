import { expect, test } from "@playwright/test";

test("renders app shell and shows backend health success", async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem("vanessa.locale", "en");
  });

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
  await expect(page.getByLabel("Language")).toHaveValue("en");

  await page.getByRole("button", { name: "Check backend" }).click();

  await expect(page.locator("strong[data-state='success']")).toContainText("SUCCESS");
  await expect(page.locator("pre")).toContainText('"status": "ok"');
  await expect(page.locator("pre")).toContainText('"service": "backend"');
});

test("shows clear error state when backend request fails", async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem("vanessa.locale", "en");
  });

  await page.route("**/health", async (route) => {
    await route.abort("failed");
  });

  await page.goto("/");
  await page.getByRole("button", { name: "Check backend" }).click();

  await expect(page.locator("strong[data-state='error']")).toContainText("ERROR");
  await expect(page.getByText(/Request failed:/)).toBeVisible();
});

test("switches language to Spanish and persists preference", async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem("vanessa.locale", "en");
  });

  await page.goto("/");

  await page.getByLabel("Language").selectOption("es");
  await expect(page.getByText("Estado del backend")).toBeVisible();
  await expect(page.getByRole("button", { name: "Comprobar backend" })).toBeVisible();

  await page.reload();
  await expect(page.getByText("Estado del backend")).toBeVisible();
  await expect(page.getByRole("button", { name: "Comprobar backend" })).toBeVisible();
});
