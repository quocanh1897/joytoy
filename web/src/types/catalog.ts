export type Availability = "InStock" | "PreOrder" | "OutOfStock" | "SoldOut" | null;

export interface CatalogImage {
  src: string;
  width: number;
  height: number;
}

export interface CatalogStock {
  sku: string | null;
  qty: number | null;
  priceVnd: string | null;
  deposit: string | null;
}

export interface CatalogProductSummary {
  slug: string;
  name: string;
  upc: string | null;
  url: string | null;
  categoryId: string;
  categoryEn: string;
  categoryVi: string;
  priceUsd: number | null;
  availability: Availability;
  scale: string | null;
  material: string | null;
  size: string | null;
  sizeCm: number | null;
  thumbnail: CatalogImage;
  galleryCount: number;
  stock: CatalogStock | null;
}

export interface CatalogProduct extends CatalogProductSummary {
  gallery: CatalogImage[];
  boxContents: string[];
}

export interface CatalogCategory {
  id: string;
  labelEn: string;
  labelVi: string;
  count: number;
}

export interface CatalogData {
  generatedAt: string | null;
  productCount: number;
  categories: CatalogCategory[];
  products: CatalogProduct[];
}

export interface CatalogIndex {
  generatedAt: string | null;
  productCount: number;
  categories: CatalogCategory[];
  products: CatalogProductSummary[];
}
