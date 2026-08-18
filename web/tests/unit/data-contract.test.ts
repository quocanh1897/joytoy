import { readFile } from "node:fs/promises";
import { describe, expect, it } from "vitest";
import type { CatalogData } from "../../src/types/catalog";

const catalog = JSON.parse(
  await readFile(new URL("../../src/generated/catalog.json", import.meta.url), "utf8"),
) as CatalogData;

describe("generated catalog contract", () => {
  it("contains unique, routable product records", () => {
    expect(catalog.productCount).toBe(541);
    expect(catalog.products).toHaveLength(541);
    expect(new Set(catalog.products.map((product) => product.slug)).size).toBe(541);
    expect(catalog.categories.length).toBeGreaterThan(30);
  });

  it("references static media instead of embedded images", () => {
    const images = catalog.products.flatMap((product) => [product.thumbnail, ...product.gallery]);
    expect(images.length).toBeGreaterThan(6_000);
    expect(images.every((image) => image.src.startsWith("/media/") || image.src === "/placeholder.svg")).toBe(true);
    expect(images.every((image) => image.width > 0 && image.height > 0)).toBe(true);
    expect(JSON.stringify(catalog)).not.toContain("data:image/");
  });
});
