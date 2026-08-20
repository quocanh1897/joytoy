import type { CatalogProductSummary } from "../types/catalog";

export const LATEST_CATEGORY_ID = "latest";

export type SortMode = "name" | "name-desc" | "price-asc" | "price-desc";

export interface FilterState {
  query: string;
  category: string;
  shopOnly: boolean;
  sort: SortMode;
}

export function normalizeSearch(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[đĐ]/g, "d")
    .toLocaleLowerCase()
    .trim();
}

export function searchableText(product: CatalogProductSummary): string {
  return normalizeSearch(
    [product.name, product.upc, product.stock?.sku, product.categoryEn, product.categoryVi]
      .filter(Boolean)
      .join(" "),
  );
}

export function filterAndSort(
  products: CatalogProductSummary[],
  state: FilterState,
): CatalogProductSummary[] {
  const query = normalizeSearch(state.query);
  const filtered = products.filter((product) => {
    if (state.category === LATEST_CATEGORY_ID) {
      if (!product.isLatest) return false;
    } else if (state.category && product.categoryId !== state.category) {
      return false;
    }
    if (state.shopOnly && !product.stock) return false;
    return !query || searchableText(product).includes(query);
  });

  return filtered.toSorted((left, right) => {
    if (state.category === LATEST_CATEGORY_ID) {
      const byUpdated = (right.updatedAt ?? "").localeCompare(left.updatedAt ?? "");
      if (byUpdated !== 0) return byUpdated;
    }
    if (state.sort === "name-desc") return right.name.localeCompare(left.name);
    if (state.sort === "price-asc") {
      return (left.priceUsd ?? Number.POSITIVE_INFINITY) - (right.priceUsd ?? Number.POSITIVE_INFINITY);
    }
    if (state.sort === "price-desc") return (right.priceUsd ?? -1) - (left.priceUsd ?? -1);
    return left.name.localeCompare(right.name);
  });
}

export function formatUsd(value: number | null): string {
  return value == null ? "—" : `$${value.toFixed(2)}`;
}

export function formatVnd(value: string | null | undefined): string {
  if (!value) return "";
  const cleaned = String(value).replace(/\s/g, "");
  return `${cleaned.includes(".") ? cleaned : `${cleaned}.000`} ₫`;
}
