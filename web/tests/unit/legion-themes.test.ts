import { describe, expect, it } from "vitest";
import catalogJson from "../../src/generated/catalog.json";
import type { CatalogData } from "../../src/types/catalog";
import { LEGION_THEMES } from "../../src/lib/legion-themes";

describe("legion-themes", () => {
  it("defines a palette for every catalog category", () => {
    const catalog = catalogJson as CatalogData;
    for (const category of catalog.categories) {
      expect(LEGION_THEMES[category.id], category.id).toBeDefined();
    }
  });
});
