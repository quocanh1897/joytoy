import { describe, expect, it } from "vitest";
import { catalogHomeUrl, resolveCatalogState } from "../../src/scripts/catalog-state";

describe("catalog-state", () => {
  it("builds a homepage URL from saved filters", () => {
    expect(
      catalogHomeUrl({
        query: "Sanguinius",
        category: "primarch",
        shopOnly: true,
        sort: "price-desc",
      }),
    ).toBe("/?q=Sanguinius&category=primarch&shop=1&sort=price-desc");
  });

  it("prefers URL params over saved state", () => {
    expect(
      resolveCatalogState("?category=ultramarines&sort=name-desc"),
    ).toEqual({
      query: "",
      category: "ultramarines",
      shopOnly: false,
      sort: "name-desc",
    });
  });

  it("defaults to the latest category when no URL or saved state exists", () => {
    expect(resolveCatalogState("")).toEqual({
      query: "",
      category: "latest",
      shopOnly: false,
      sort: "name",
    });
  });
});
