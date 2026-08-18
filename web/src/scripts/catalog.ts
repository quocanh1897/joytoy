import { filterAndSort, formatUsd, formatVnd, type FilterState, type SortMode } from "../lib/catalog-filter";
import type { CatalogIndex, CatalogProductSummary } from "../types/catalog";
import { applyLanguage, bindLanguageToggle, type Language } from "./language";

const PAGE_SIZE = 36;

function required<T extends Element>(selector: string): T {
  const element = document.querySelector<T>(selector);
  if (!element) throw new Error(`Missing catalog element: ${selector}`);
  return element;
}

function availabilityCopy(value: CatalogProductSummary["availability"], language: Language): string {
  const copy = {
    InStock: { en: "In stock", vi: "Còn hàng" },
    PreOrder: { en: "Pre-order", vi: "Đặt trước" },
    OutOfStock: { en: "Sold out", vi: "Hết hàng" },
    SoldOut: { en: "Sold out", vi: "Hết hàng" },
  } as const;
  return value ? copy[value]?.[language] ?? (language === "vi" ? "Lưu trữ" : "Archive") : language === "vi" ? "Lưu trữ" : "Archive";
}

function makeElement<K extends keyof HTMLElementTagNameMap>(tag: K, className?: string): HTMLElementTagNameMap[K] {
  const element = document.createElement(tag);
  if (className) element.className = className;
  return element;
}

function renderCard(product: CatalogProductSummary, language: Language): HTMLElement {
  const article = makeElement("article", "product-card");
  article.dataset.productCard = "";
  article.dataset.slug = product.slug;

  const imageLink = makeElement("a", "card-image");
  imageLink.href = `/products/${product.slug}/`;
  imageLink.setAttribute("aria-label", `${language === "vi" ? "Xem" : "View"} ${product.name}`);
  const image = makeElement("img");
  image.src = product.thumbnail.src;
  image.alt = "";
  image.width = product.thumbnail.width;
  image.height = product.thumbnail.height;
  image.loading = "lazy";
  image.decoding = "async";
  imageLink.append(image);

  const availability = makeElement("span", `availability ${(product.availability ?? "unknown").toLowerCase()}`);
  availability.textContent = availabilityCopy(product.availability, language);
  imageLink.append(availability);
  if (product.stock) {
    const shop = makeElement("span", "shop-flag");
    shop.textContent = language === "vi" ? "Hàng tại shop" : "Local stock";
    imageLink.append(shop);
  }
  const galleryCount = makeElement("span", "gallery-count");
  galleryCount.textContent = `${String(product.galleryCount).padStart(2, "0")} ${language === "vi" ? "ảnh" : "plates"}`;
  imageLink.append(galleryCount);

  const copy = makeElement("div", "card-copy");
  const taxonomy = makeElement("div", "card-taxonomy");
  const category = makeElement("span");
  category.textContent = language === "vi" ? product.categoryVi : product.categoryEn;
  const scale = makeElement("span");
  scale.textContent = product.scale ?? "1:18";
  taxonomy.append(category, scale);

  const title = makeElement("h2");
  const titleLink = makeElement("a");
  titleLink.href = `/products/${product.slug}/`;
  titleLink.textContent = product.name;
  title.append(titleLink);

  const meta = makeElement("div", "card-meta");
  const sku = makeElement("span");
  sku.textContent = product.stock?.sku || product.upc || "NO UPC";
  meta.append(sku);
  if (product.size) {
    const size = makeElement("span");
    size.textContent = product.size;
    meta.append(size);
  }

  const price = makeElement("div", "card-price");
  const usd = makeElement("strong");
  usd.textContent = formatUsd(product.priceUsd);
  price.append(usd);
  if (product.stock?.priceVnd) {
    const vnd = makeElement("span");
    vnd.textContent = formatVnd(product.stock.priceVnd);
    price.append(vnd);
  }

  copy.append(taxonomy, title, meta, price);
  article.append(imageLink, copy);
  return article;
}

export async function initCatalog(): Promise<void> {
  const grid = required<HTMLElement>("[data-catalog-grid]");
  const search = required<HTMLInputElement>("[data-catalog-search]");
  const sort = required<HTMLSelectElement>("[data-catalog-sort]");
  const shopOnly = required<HTMLInputElement>("[data-shop-only]");
  const categoryNav = required<HTMLElement>("[data-category-nav]");
  const resultCount = required<HTMLElement>("[data-result-count]");
  const loadMore = required<HTMLButtonElement>("[data-load-more]");
  const error = required<HTMLElement>("[data-catalog-error]");

  let language: Language = "en";
  let data: CatalogIndex;
  let visibleCount = PAGE_SIZE;
  const params = new URLSearchParams(location.search);
  const state: FilterState = {
    query: params.get("q") ?? "",
    category: params.get("category") ?? "",
    shopOnly: params.get("shop") === "1",
    sort: (["name", "name-desc", "price-asc", "price-desc"].includes(params.get("sort") ?? "")
      ? params.get("sort")
      : "name") as SortMode,
  };

  search.value = state.query;
  sort.value = state.sort;
  shopOnly.checked = state.shopOnly;

  const updateUrl = () => {
    const next = new URLSearchParams();
    if (state.query) next.set("q", state.query);
    if (state.category) next.set("category", state.category);
    if (state.shopOnly) next.set("shop", "1");
    if (state.sort !== "name") next.set("sort", state.sort);
    history.replaceState(null, "", `${location.pathname}${next.size ? `?${next}` : ""}`);
  };

  const render = () => {
    const results = filterAndSort(data.products, state);
    const fragment = document.createDocumentFragment();
    for (const product of results.slice(0, visibleCount)) fragment.append(renderCard(product, language));
    grid.replaceChildren(fragment);
    resultCount.textContent = language === "vi"
      ? `${results.length} mẫu phù hợp`
      : `${results.length} matching ${results.length === 1 ? "model" : "models"}`;
    loadMore.hidden = results.length <= visibleCount;
    loadMore.textContent = language === "vi"
      ? `Xem thêm (${Math.min(PAGE_SIZE, results.length - visibleCount)})`
      : `Load next ${Math.min(PAGE_SIZE, results.length - visibleCount)}`;
    categoryNav.querySelectorAll<HTMLButtonElement>("[data-category]").forEach((button) => {
      const active = (button.dataset.category ?? "") === state.category;
      button.classList.toggle("active", active);
      button.setAttribute("aria-pressed", String(active));
    });
    updateUrl();
  };

  try {
    const response = await fetch("/data/catalog-index.json");
    if (!response.ok) throw new Error(`Catalog request failed: ${response.status}`);
    data = (await response.json()) as CatalogIndex;
    language = bindLanguageToggle((nextLanguage) => {
      language = nextLanguage;
      render();
      applyLanguage(language);
    });
    render();
  } catch (cause) {
    console.error(cause);
    error.hidden = false;
    error.textContent = "The full catalog index could not be loaded. The first archive pages remain available below.";
    return;
  }

  let debounce = 0;
  search.addEventListener("input", () => {
    window.clearTimeout(debounce);
    debounce = window.setTimeout(() => {
      state.query = search.value.trim();
      visibleCount = PAGE_SIZE;
      render();
    }, 120);
  });
  sort.addEventListener("change", () => {
    state.sort = sort.value as SortMode;
    visibleCount = PAGE_SIZE;
    render();
  });
  shopOnly.addEventListener("change", () => {
    state.shopOnly = shopOnly.checked;
    visibleCount = PAGE_SIZE;
    render();
  });
  categoryNav.addEventListener("click", (event) => {
    const button = (event.target as Element).closest<HTMLButtonElement>("[data-category]");
    if (!button) return;
    state.category = button.dataset.category ?? "";
    visibleCount = PAGE_SIZE;
    render();
    document.querySelector("#catalog-start")?.scrollIntoView({ behavior: "smooth", block: "start" });
  });
  loadMore.addEventListener("click", () => {
    visibleCount += PAGE_SIZE;
    render();
  });
}
