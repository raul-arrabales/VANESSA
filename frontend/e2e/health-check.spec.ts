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

  await expect(page.locator(".status-pill[data-state='success']")).toContainText("SUCCESS");
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

  await expect(page.locator(".status-pill[data-state='error']")).toContainText("ERROR");
  await expect(page.getByText(/Request failed:/)).toBeVisible();
});

test("switches language to Spanish and persists preference", async ({ page }) => {
  await page.goto("/");

  await page.getByLabel("Language").selectOption("es");
  await expect(page.getByText("Estado del backend")).toBeVisible();
  await expect(page.getByRole("button", { name: "Comprobar backend" })).toBeVisible();
  await expect.poll(async () => page.evaluate(() => window.localStorage.getItem("vanessa.locale"))).toBe("es");

  await page.reload();
  await expect(page.getByText("Estado del backend")).toBeVisible();
  await expect(page.getByRole("button", { name: "Comprobar backend" })).toBeVisible();
});

test("toggles theme and persists mode after reload", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");

  await page.getByTestId("theme-toggle").click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await expect.poll(async () => page.evaluate(() => window.localStorage.getItem("vanessa.theme"))).toBe("dark");

  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await expect(page.getByTestId("theme-toggle")).toContainText("Day mode");
});

test("renders style guide route with primitive examples", async ({ page }) => {
  await page.goto("/style-guide");

  await expect(page.getByRole("heading", { name: "VANESSA" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Color Tokens" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Primary" })).toBeVisible();
  await expect(page.getByPlaceholder("Search logs")).toBeVisible();
});

test("keeps critical text contrast at WCAG AA levels", async ({ page }) => {
  await page.goto("/");

  const contrastRatio = await page.evaluate(() => {
    const parseColor = (color: string): [number, number, number] => {
      const values = color.match(/\d+/g);
      if (!values || values.length < 3) {
        return [0, 0, 0];
      }
      return [Number(values[0]), Number(values[1]), Number(values[2])];
    };

    const toLinear = (channel: number): number => {
      const normalized = channel / 255;
      return normalized <= 0.03928
        ? normalized / 12.92
        : ((normalized + 0.055) / 1.055) ** 2.4;
    };

    const luminance = (rgb: [number, number, number]): number => {
      const [r, g, b] = rgb;
      return 0.2126 * toLinear(r) + 0.7152 * toLinear(g) + 0.0722 * toLinear(b);
    };

    const ratio = (fg: string, bg: string): number => {
      const l1 = luminance(parseColor(fg));
      const l2 = luminance(parseColor(bg));
      const lighter = Math.max(l1, l2);
      const darker = Math.min(l1, l2);
      return (lighter + 0.05) / (darker + 0.05);
    };

    const panel = document.querySelector(".panel") as HTMLElement | null;
    if (!panel) {
      return 0;
    }
    const bodyStyles = window.getComputedStyle(document.body);
    const panelStyles = window.getComputedStyle(panel);
    return ratio(bodyStyles.color, panelStyles.backgroundColor);
  });

  expect(contrastRatio).toBeGreaterThanOrEqual(4.5);
});
