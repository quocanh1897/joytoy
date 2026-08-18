import type { SortMode } from "../lib/catalog-filter";

export interface CatalogUiState {
  query: string;
  category: string;
  shopOnly: boolean;
  sort: SortMode;
}

const STORAGE_KEY = "jt-catalog-state";
const SORT_MODES: SortMode[] = ["name", "name-desc", "price-asc", "price-desc"];

function parseSort(value: string | null | undefined): SortMode {
  return SORT_MODES.includes(value as SortMode) ? (value as SortMode) : "name";
}

export function readCatalogState(): Partial<CatalogUiState> {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as Partial<CatalogUiState>;
    return {
      query: typeof parsed.query === "string" ? parsed.query : "",
      category: typeof parsed.category === "string" ? parsed.category : "",
      shopOnly: Boolean(parsed.shopOnly),
      sort: parseSort(parsed.sort),
    };
  } catch {
    return {};
  }
}

export function writeCatalogState(state: CatalogUiState): void {
  sessionStorage.setItem(
    STORAGE_KEY,
    JSON.stringify({
      query: state.query,
      category: state.category,
      shopOnly: state.shopOnly,
      sort: state.sort,
    }),
  );
}

export function catalogHomeUrl(state: Partial<CatalogUiState> = readCatalogState()): string {
  const params = new URLSearchParams();
  if (state.query) params.set("q", state.query);
  if (state.category) params.set("category", state.category);
  if (state.shopOnly) params.set("shop", "1");
  if (state.sort && state.sort !== "name") params.set("sort", state.sort);
  const query = params.toString();
  return query ? `/?${query}` : "/";
}

export function resolveCatalogState(search = location.search): CatalogUiState {
  const params = new URLSearchParams(search);
  const saved = readCatalogState();
  const hasUrlState = ["q", "category", "shop", "sort"].some((key) => params.has(key));

  if (hasUrlState) {
    return {
      query: params.get("q") ?? "",
      category: params.get("category") ?? "",
      shopOnly: params.get("shop") === "1",
      sort: parseSort(params.get("sort")),
    };
  }

  return {
    query: saved.query ?? "",
    category: saved.category ?? "",
    shopOnly: saved.shopOnly ?? false,
    sort: saved.sort ?? "name",
  };
}
