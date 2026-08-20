import { describe, expect, it } from "vitest";
import { filterAndSort, formatUsd, formatVnd, LATEST_CATEGORY_ID, normalizeSearch } from "../../src/lib/catalog-filter";
import type { CatalogProductSummary } from "../../src/types/catalog";

const image = { src: "/placeholder.svg", width: 720, height: 720 };
const base = {
  url: null,
  availability: "InStock" as const,
  scale: "1:18",
  material: "ABS/PVC",
  size: "18 cm",
  sizeCm: 18,
  thumbnail: image,
  galleryCount: 11,
  updatedAt: null,
  isLatest: false,
};
const products: CatalogProductSummary[] = [
  {
    ...base,
    slug: "morvenn-vahl",
    name: "Abbess Sanctorum Morvenn Vahl",
    upc: "6973130378872",
    categoryId: "adepta-sororitas",
    categoryEn: "Adepta Sororitas",
    categoryVi: "Nữ tu chiến đấu",
    priceUsd: 80,
    stock: { sku: "JT8872", qty: 2, priceVnd: "3.190", deposit: null },
  },
  {
    ...base,
    slug: "captain-titus",
    name: "Ultramarines Lieutenant Titus",
    upc: "6973130379999",
    categoryId: "ultramarines",
    categoryEn: "Ultramarines",
    categoryVi: "Ultramarines",
    priceUsd: 45,
    availability: "PreOrder",
    size: null,
    sizeCm: null,
    galleryCount: 8,
    stock: null,
  },
  {
    ...base,
    slug: "new-model",
    name: "Blood Angels MkX Helmet",
    upc: null,
    categoryId: "blood-angels",
    categoryEn: "Blood Angels",
    categoryVi: "Blood Angels",
    priceUsd: 25,
    stock: null,
    updatedAt: "2026-08-19T07:30:00Z",
    isLatest: true,
  },
];

describe("catalog filters", () => {
  it("normalizes accents and searches names, identifiers and categories", () => {
    expect(normalizeSearch("Nữ Tù Chiến Đấu")).toBe("nu tu chien dau");
    expect(filterAndSort(products, { query: "JT8872", category: "", shopOnly: false, sort: "name" })).toEqual([products[0]]);
    expect(filterAndSort(products, { query: "ultramarines", category: "", shopOnly: false, sort: "name" })).toEqual([products[1]]);
  });

  it("combines category and stock filters and sorts prices", () => {
    expect(filterAndSort(products, { query: "", category: "adepta-sororitas", shopOnly: true, sort: "price-desc" })).toEqual([products[0]]);
    expect(filterAndSort(products, { query: "", category: "", shopOnly: false, sort: "price-asc" })).toEqual([products[2], products[1], products[0]]);
  });

  it("filters latest models and sorts them by update time", () => {
    expect(filterAndSort(products, { query: "", category: LATEST_CATEGORY_ID, shopOnly: false, sort: "name" })).toEqual([products[2]]);
  });

  it("formats catalog prices", () => {
    expect(formatUsd(80)).toBe("$80.00");
    expect(formatUsd(null)).toBe("—");
    expect(formatVnd("3.190")).toBe("3.190 ₫");
    expect(formatVnd("3190")).toBe("3190.000 ₫");
  });
});
