import { expect, test, type Page } from "@playwright/test";

async function sidebarCategoryCount(page: Page, categoryId: string): Promise<number> {
  const badge = page.locator(`[data-category="${categoryId}"] strong`);
  return Number((await badge.textContent())?.trim());
}

function matchingModelsLabel(count: number): string {
  return count === 1 ? "1 matching model" : `${count} matching models`;
}

async function inShopCount(page: Page): Promise<number> {
  return page.evaluate(async () => {
    const response = await fetch("/data/catalog-index.json");
    const catalog = (await response.json()) as { products: Array<{ stock: unknown }> };
    return catalog.products.filter((product) => product.stock).length;
  });
}

test("searches the archive and opens a product record", async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on("console", (message) => message.type() === "error" && consoleErrors.push(message.text()));
  await page.goto("/");

  await expect(page.getByRole("heading", { name: /Factions/i })).toBeVisible();
  await expect(page.locator("[data-product-card]")).toHaveCount(36);
  await page.locator("[data-catalog-search]").fill("Morvenn Vahl");
  await expect(page.locator("[data-result-count]")).toHaveText("1 matching model");
  await expect(page.locator("[data-product-card]")).toHaveCount(1);
  await expect(page).toHaveURL(/\?q=Morvenn\+Vahl$/);

  await page.reload();
  await expect(page.locator("[data-product-card]")).toHaveCount(1);

  await page.locator("[data-product-card] h2 a").click();
  await expect(page).toHaveURL(/\/products\/adepta-sororitas-abbess-sanctorum-morvenn-vahl\/$/);
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Morvenn Vahl");
  await expect(page.locator("[data-gallery-main]")).toBeVisible();
  await expect(page.locator("[data-gallery-counter]")).toHaveText("1 / 11");
  await page.keyboard.press("ArrowRight");
  await expect(page.locator("[data-gallery-counter]")).toHaveText("2 / 11");
  await page.goBack();
  await expect(page).toHaveURL(/\?q=Morvenn\+Vahl$/);
  await expect(page.locator("[data-product-card]")).toHaveCount(1);
  expect(consoleErrors).toEqual([]);
});

test("filters local inventory and switches language", async ({ page }) => {
  await page.goto("/");
  const shopCount = await inShopCount(page);
  await page.locator("[data-shop-only]").check();
  await expect(page.locator("[data-result-count]")).toHaveText(matchingModelsLabel(shopCount));
  await page.locator("[data-language-toggle]").click();
  await expect(page.locator("html")).toHaveAttribute("lang", "vi");
  await expect(page.locator("[data-result-count]")).toHaveText(`${shopCount} mẫu phù hợp`);
  await expect(page.getByText("Danh mục", { exact: true })).toBeVisible();
});

test("filters latest models from the sidebar", async ({ page }) => {
  await page.goto("/");
  const latestCount = await sidebarCategoryCount(page, "latest");
  await page.locator('[data-category="latest"]').click();
  await expect(page).toHaveURL(/category=latest/);
  await expect(page.locator('[data-category="latest"]')).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator("[data-result-count]")).toHaveText(matchingModelsLabel(latestCount));
  await expect(page.locator("[data-product-card]")).toHaveCount(latestCount);
});

test("persists category and sort state in the URL", async ({ page }) => {
  await page.goto("/");
  const primarchCount = await sidebarCategoryCount(page, "primarch");
  await page.locator('[data-category="primarch"]').click();
  await expect(page.locator("[data-result-count]")).toHaveText(matchingModelsLabel(primarchCount));
  await page.locator("[data-catalog-sort]").selectOption("name-desc");
  await expect(page).toHaveURL(/category=primarch/);
  await expect(page).toHaveURL(/sort=name-desc/);

  const names = await page.locator("[data-product-card] h2").allTextContents();
  expect(names).toEqual([...names].sort((left, right) => right.localeCompare(left)));

  await page.reload();
  await expect(page.locator('[data-category="primarch"]')).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator("[data-catalog-sort]")).toHaveValue("name-desc");
  await expect(page.locator("[data-product-card]")).toHaveCount(primarchCount);
});

test("keeps the mobile catalog usable", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "mobile", "mobile-only layout assertion");
  await page.goto("/");
  await expect(page.locator("[data-category-nav]")).toBeVisible();
  await expect(page.locator("[data-catalog-search]")).toBeVisible();
  await expect(page.locator("[data-product-card]").first()).toBeVisible();
  await expect(page.locator("body")).not.toHaveCSS("overflow-x", "scroll");
});
