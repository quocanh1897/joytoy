#!/usr/bin/env python3
"""Build warhammer-catalog/catalog.html from scraper data + optional local stock."""

from __future__ import annotations

import argparse
import base64
import io
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SCRAPER_DIR = ROOT / "warhammer-scraper"

sys.path.insert(0, str(SCRAPER_DIR))
from scrape import extract_specs  # noqa: E402
from size_extract import resolve_display_height_cm  # noqa: E402
from joytoy_categories import CATEGORY_BY_ID, CATEGORY_ORDER, JOYTOY_CATEGORIES, legion_display_labels  # noqa: E402
from stock_match import assign_stock_to_products  # noqa: E402

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None  # type: ignore

SCRAPER_JSON = SCRAPER_DIR / "data" / "products.json"
STOCK_JSON = Path(__file__).resolve().parent / "stock_data.json"
TEMPLATE = Path(__file__).resolve().parent / "catalog.template.html"
OUTPUT = Path(__file__).resolve().parent / "catalog.html"
OUTPUT_LINKED = Path(__file__).resolve().parent / "catalog-linked.html"
SCRAPER_IMAGES = ROOT / "warhammer-scraper" / "data" / "images"
TOTAL_EXPECTED = 541
DEFAULT_MAX_WIDTH = 640
DEFAULT_QUALITY = 70
DEFAULT_IMAGE_SCOPE = "description"
IMAGE_SCOPES = ("description", "thumb")

# Fallback keywords when joytoy_category is missing (name-only heuristics).
NAME_FALLBACK_RULES: list[tuple[str, list[str]]] = [
    ("word-bearers", ["Word Bearers"]),
    ("stormcast-eternals", ["Stormcast Eternals"]),
    ("emperors-children", ["Emperor's Children", "Emperors Children"]),
]

CATALOG_CATEGORY_ORDER = [*CATEGORY_ORDER, "other"]

PLACEHOLDER = "/*__CATALOG_JSON__*/"
BLOB_PLACEHOLDER = "/*__IMAGE_BLOB_CHUNKS__*/"
CHUNK_MAX_BYTES = 6 * 1024 * 1024


def detect_category(product: dict) -> tuple[str, str, str]:
    joytoy_id = (product.get("joytoy_category") or "").strip()
    if joytoy_id in CATEGORY_BY_ID:
        cat = CATEGORY_BY_ID[joytoy_id]
        return cat.id, cat.label_en, cat.label_vi

    slug = (product.get("slug") or "").lower()
    name = product.get("name") or ""
    lower = name.lower()

    slug_prefix_rules: list[tuple[str, str]] = [
        ("chaos-space-marines", "chaos-space-marines"),
        ("chaos-space-marine", "chaos-space-marines"),
        ("chaos-terminator", "chaos-space-marines"),
        ("word-bearers", "chaos-space-marines"),
        ("imperiar-fists", "imperial-fists"),
        ("iron-hands", "iron-hands"),
        ("legio-custodes", "legio-custodes"),
        ("adeptus-mechanicus", "adeptus-mechanicus"),
        ("stormcast", "age-of-sigmar"),
        ("white-consuls", "white-consuls"),
        ("ork-kommandos", "ork-kommandos"),
        ("space-marine-ii", "space-marine-ii"),
        ("mkvi-", "space-marine-ii"),
        ("primaris-", "space-marine-ii"),
        ("invictor-", "space-marine-ii"),
    ]
    for prefix, cat_id in slug_prefix_rules:
        if slug.startswith(prefix) and cat_id in CATEGORY_BY_ID:
            cat = CATEGORY_BY_ID[cat_id]
            return cat.id, cat.label_en, cat.label_vi

    for cat_id, keywords in NAME_FALLBACK_RULES:
        for keyword in keywords:
            if keyword.lower() in lower:
                if cat_id == "word-bearers":
                    cat = CATEGORY_BY_ID["chaos-space-marines"]
                    return cat.id, cat.label_en, cat.label_vi
                if cat_id == "stormcast-eternals":
                    cat = CATEGORY_BY_ID["age-of-sigmar"]
                    return cat.id, cat.label_en, cat.label_vi
                if cat_id == "emperors-children":
                    cat = CATEGORY_BY_ID["chaos-space-marines"]
                    return cat.id, cat.label_en, cat.label_vi

    if "chaos space marine" in lower or "chaos terminator" in lower:
        cat = CATEGORY_BY_ID["chaos-space-marines"]
        return cat.id, cat.label_en, cat.label_vi
    if "imperiar fists" in lower or "imperial fists" in lower:
        cat = CATEGORY_BY_ID["imperial-fists"]
        return cat.id, cat.label_en, cat.label_vi
    if "space wolve" in lower or "space wolves" in lower:
        cat = CATEGORY_BY_ID["space-wolves"]
        return cat.id, cat.label_en, cat.label_vi

    for cat in JOYTOY_CATEGORIES:
        if cat.label_en.lower() in lower:
            return cat.id, cat.label_en, cat.label_vi

    return "other", "Other", "Khác"


def rel_image_path(local_path: str) -> str:
    """Path relative to warhammer-catalog/catalog.html."""
    return f"../warhammer-scraper/{local_path}"


def catalog_path_to_local(catalog_path: str) -> Path | None:
    """Map a catalog image path to a file under the repo."""
    if catalog_path.startswith("../warhammer-scraper/"):
        return SCRAPER_DIR / catalog_path.removeprefix("../warhammer-scraper/")
    if catalog_path.startswith("data/"):
        return SCRAPER_DIR / catalog_path
    return None


def image_to_data_uri(path: Path, *, max_width: int, quality: int) -> str:
    if Image is None:
        raise SystemExit("Pillow is required for standalone builds: pip install pillow")

    suffix = path.suffix.lower()
    with Image.open(path) as im:
        if getattr(im, "is_animated", False):
            im.seek(0)

        if im.mode in ("RGBA", "LA", "P"):
            if suffix == ".png" and "A" in im.getbands():
                frame = im.convert("RGBA")
                if max(frame.size) > max_width:
                    frame.thumbnail((max_width, max_width), Image.Resampling.LANCZOS)
                buf = io.BytesIO()
                frame.save(buf, format="PNG", optimize=True)
                encoded = base64.b64encode(buf.getvalue()).decode("ascii")
                return f"data:image/png;base64,{encoded}"

        frame = im.convert("RGB")
        if max(frame.size) > max_width:
            frame.thumbnail((max_width, max_width), Image.Resampling.LANCZOS)

        buf = io.BytesIO()
        frame.save(buf, format="WEBP", quality=quality, method=4)
        encoded = base64.b64encode(buf.getvalue()).decode("ascii")
        return f"data:image/webp;base64,{encoded}"


def safe_script_json(payload: str) -> str:
    """Prevent </script> and line-separator chars from breaking inline JSON scripts."""
    return (
        payload.replace("<", "\\u003c")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def standalone_product_images(product: dict, scope: str) -> list[str]:
    """Choose which description/marketing image paths to embed in a standalone build."""
    description_images = product.get("images") or resolve_images(product)
    if scope == "thumb":
        thumb = resolve_thumb(product, description_images) or (
            description_images[0] if description_images else None
        )
        return [thumb] if thumb else []
    return description_images


def embed_catalog_images(
    data: dict[str, Any],
    *,
    max_width: int,
    quality: int,
    image_scope: str,
) -> tuple[dict[str, Any], dict[str, str], int, int]:
    """Build image key refs for catalog JSON and a separate blob map for standalone HTML."""
    blobs: dict[str, str] = {}
    path_to_key: dict[str, str] = {}
    embedded = 0
    bytes_inlined = 0
    counter = 0

    def key_for(path: str, *, embed: bool) -> str:
        nonlocal counter, embedded, bytes_inlined
        if not path:
            return ""
        if path in path_to_key:
            return path_to_key[path]

        counter += 1
        key = f"i{counter}"
        path_to_key[path] = key

        if not embed:
            return key

        if path.startswith("data:"):
            blobs[key] = path
            return key

        local = catalog_path_to_local(path)
        if local is not None and local.exists():
            uri = image_to_data_uri(local, max_width=max_width, quality=quality)
            blobs[key] = uri
            embedded += 1
            bytes_inlined += len(uri)
            if embedded % 250 == 0:
                print(f"  embedded {embedded} images ({bytes_inlined / 1024 / 1024:.1f} MB)")
        else:
            blobs[key] = path

        return key

    embed_paths: set[str] = set()
    for product in data.get("products") or []:
        scoped_images = standalone_product_images(product, image_scope)
        product["images"] = scoped_images
        embed_paths.update(scoped_images)
        thumb = resolve_thumb(product, scoped_images) or (scoped_images[0] if scoped_images else None)
        product["thumb"] = thumb

    for path in sorted(embed_paths):
        key_for(path, embed=True)

    for product in data.get("products") or []:
        product["images"] = [path_to_key[image] for image in product.get("images") or []]
        thumb = product.get("thumb")
        product["thumb"] = path_to_key.get(thumb) if thumb else None

    return data, blobs, embedded, bytes_inlined


def chunk_image_blobs(blobs: dict[str, str], max_bytes: int = CHUNK_MAX_BYTES) -> list[dict[str, str]]:
    chunks: list[dict[str, str]] = []
    current: dict[str, str] = {}
    current_size = 2

    for key, uri in blobs.items():
        entry_size = len(json.dumps({key: uri}, ensure_ascii=False, separators=(",", ":")))
        if current and current_size + entry_size > max_bytes:
            chunks.append(current)
            current = {}
            current_size = 2
        current[key] = uri
        current_size += entry_size

    if current:
        chunks.append(current)
    return chunks


def render_blob_chunks(blobs: dict[str, str]) -> str:
    if not blobs:
        return ""
    parts: list[str] = []
    for index, chunk in enumerate(chunk_image_blobs(blobs)):
        payload = safe_script_json(
            json.dumps(chunk, ensure_ascii=False, separators=(",", ":"))
        )
        parts.append(
            f'<script type="application/json" class="img-blob" id="img-blob-{index}">'
            f"{payload}</script>"
        )
    return "\n".join(parts)


def _image_key(path_or_url: str) -> str:
    """Normalize local path or URL for deduplication."""
    text = path_or_url.split("?")[0]
    if "/data/images/" in text:
        text = text.split("/data/images/", 1)[-1]
    if "img.joytoy.com" in text:
        text = text.split("img.joytoy.com", 1)[-1]
    return text.lower().lstrip("/")


def resolve_images(product: dict) -> list[str]:
    """Description/marketing images only (product gallery photos are excluded)."""
    paths: list[str] = []
    seen: set[str] = set()

    def add_path(rel_path: str) -> None:
        key = _image_key(rel_path)
        if key not in seen:
            seen.add(key)
            paths.append(rel_path)

    for local in product.get("local_description_images") or []:
        full = ROOT / "warhammer-scraper" / local
        if full.exists():
            add_path(rel_image_path(local))

    if paths:
        return paths

    for url in product.get("description_images") or []:
        key = _image_key(url)
        if key not in seen:
            seen.add(key)
            paths.append(url)
    return paths


def resolve_thumb(product: dict, images: list[str]) -> str | None:
    if not images:
        return None
    for local in product.get("local_description_images") or []:
        rel = rel_image_path(local)
        if rel in images:
            return rel
    return images[0]


def parse_box_contents(description_text: str) -> list[str]:
    if not description_text:
        return []
    match = re.search(r"Box Contents\s*(.+)$", description_text, re.I | re.S)
    if not match:
        return []
    block = match.group(1)
    items = re.findall(r"[·•]\s*([^\n·•]+)", block)
    return [item.strip() for item in items if item.strip()]


def resolve_size_fields(product: dict) -> dict[str, Any]:
    """Re-parse figure size from description (source of truth)."""
    plain = product.get("description_text") or ""
    if plain:
        specs = extract_specs(product.get("description_html") or "", plain)
        return {
            "size_cm": specs["size_cm"],
            "height_inches": specs["height_inches"],
            "product_dimensions_cm": specs["product_dimensions_cm"],
        }
    return {
        "size_cm": product.get("size_cm"),
        "height_inches": product.get("height_inches"),
        "product_dimensions_cm": product.get("product_dimensions_cm"),
    }


def format_size(product: dict, size_fields: dict) -> str | None:
    height = resolve_display_height_cm(product, size_fields.get("size_cm"))
    if height is None:
        return None
    return f"{height:g} cm"


def load_stock_rows() -> list[dict]:
    if not STOCK_JSON.exists():
        return []
    return json.loads(STOCK_JSON.read_text(encoding="utf-8"))


def build_product(product: dict, stock_by_slug: dict[str, dict]) -> dict:
    cat_id, label_en, label_vi = detect_category(product)
    images = resolve_images(product)
    upc = (product.get("sku") or "").strip()
    slug = (product.get("slug") or "").strip()
    stock = stock_by_slug.get(slug)
    size_fields = resolve_size_fields(product)

    entry: dict = {
        "slug": product.get("slug"),
        "name": product.get("name"),
        "upc": upc,
        "url": product.get("url"),
        "category_id": cat_id,
        "category_en": label_en,
        "category_vi": label_vi,
        "price_usd": product.get("price_usd"),
        "availability": product.get("availability"),
        "scale": product.get("scale"),
        "material": product.get("material"),
        "size": format_size(product, size_fields),
        "size_cm": resolve_display_height_cm(product, size_fields.get("size_cm")),
        "thumb": resolve_thumb(product, images),
        "images": images,
        "box_contents": parse_box_contents(product.get("description_text") or ""),
        "scraped_at": product.get("scraped_at"),
    }

    if stock:
        entry["stock"] = {
            "sku": stock.get("sku"),
            "qty": stock.get("qty"),
            "price_vnd": stock.get("price"),
            "deposit": stock.get("deposit"),
        }

    return entry


def build_catalog_data() -> dict:
    catalog_raw = json.loads(SCRAPER_JSON.read_text(encoding="utf-8"))
    products_raw = catalog_raw.get("products") or []
    stock_rows = load_stock_rows()
    stock_by_slug, unmatched_stock, stock_methods = assign_stock_to_products(
        products_raw, stock_rows
    )
    if stock_rows:
        matched_count = len(stock_rows) - len(unmatched_stock)
        print(
            f"Stock match: {matched_count}/{len(stock_rows)} rows → "
            f"{len(stock_by_slug)} products "
            f"({', '.join(f'{k}={v}' for k, v in sorted(stock_methods.items()))})"
        )
        if unmatched_stock:
            print(f"  Unmatched stock ({len(unmatched_stock)}):")
            for row in unmatched_stock[:12]:
                print(f"    {row.get('sku')}  {row.get('name', '')[:70]}")
            if len(unmatched_stock) > 12:
                print(f"    … and {len(unmatched_stock) - 12} more")

    products = [build_product(p, stock_by_slug) for p in products_raw if p.get("name")]

    categories: dict[str, dict] = {}
    for product in products:
        cat_id = product["category_id"]
        if cat_id not in categories:
            categories[cat_id] = {
                "id": cat_id,
                "label_en": product["category_en"],
                "label_vi": product["category_vi"],
                "count": 0,
            }
        categories[cat_id]["count"] += 1

    ordered_categories = []
    for cat_id in CATALOG_CATEGORY_ORDER:
        if cat_id in categories:
            cat = categories[cat_id]
            label_en, label_vi = legion_display_labels(cat_id, cat["label_en"], cat["label_vi"])
            ordered_categories.append(
                {
                    **cat,
                    "label_en": label_en,
                    "label_vi": label_vi,
                }
            )
    for cat_id, cat in sorted(categories.items()):
        if cat_id not in CATALOG_CATEGORY_ORDER:
            ordered_categories.append(cat)

    image_count = sum(len(p.get("images") or []) for p in products)
    in_shop = sum(1 for p in products if p.get("stock"))

    return {
        "generated_at": catalog_raw.get("scraped_at"),
        "source_url": catalog_raw.get("source_url"),
        "standalone": False,
        "product_count": len(products),
        "total_expected": TOTAL_EXPECTED,
        "stats": {
            "factions": len(categories),
            "images": image_count,
            "in_shop": in_shop,
            "in_stock": sum(1 for p in products if p.get("availability") == "InStock"),
        },
        "categories": ordered_categories,
        "products": products,
    }


def write_catalog_html(
    data: dict[str, Any],
    output: Path,
    *,
    standalone: bool,
    max_width: int,
    quality: int,
    image_scope: str,
) -> None:
    if not TEMPLATE.exists():
        raise SystemExit(f"Missing template: {TEMPLATE}")

    if standalone:
        data = json.loads(json.dumps(data))
        data["standalone"] = True
        data["image_scope"] = image_scope
        print(
            f"Embedding images (scope={image_scope}, {max_width}px, WebP q{quality})…"
        )
        data, blobs, embedded, bytes_inlined = embed_catalog_images(
            data,
            max_width=max_width,
            quality=quality,
            image_scope=image_scope,
        )
        blob_html = render_blob_chunks(blobs)
        chunk_count = blob_html.count("img-blob")
        print(
            f"Embedded {embedded} images ({bytes_inlined / 1024 / 1024:.1f} MB image data, "
            f"{chunk_count} chunks)"
        )
        if image_scope != "thumb":
            print(
                "  Tip: use --image-scope thumb for a smaller file (first marketing photo only)."
            )
    else:
        blob_html = ""

    template = TEMPLATE.read_text(encoding="utf-8")
    if PLACEHOLDER not in template:
        raise SystemExit(f"Placeholder {PLACEHOLDER!r} not found in template")
    if BLOB_PLACEHOLDER not in template:
        raise SystemExit(f"Placeholder {BLOB_PLACEHOLDER!r} not found in template")

    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    html = template.replace(BLOB_PLACEHOLDER, blob_html).replace(PLACEHOLDER, payload)
    output.write_text(html, encoding="utf-8")
    size_mb = output.stat().st_size / 1024 / 1024
    mode = "standalone" if standalone else "linked"
    print(
        f"Wrote {output} ({data['product_count']} products, "
        f"{data['stats']['in_shop']} in shop, {mode}, {size_mb:.1f} MB)"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--linked",
        action="store_true",
        help="Build catalog-linked.html with relative image paths (faster, not portable)",
    )
    parser.add_argument(
        "--max-width",
        type=int,
        default=DEFAULT_MAX_WIDTH,
        help=f"Max image width for standalone embed (default {DEFAULT_MAX_WIDTH})",
    )
    parser.add_argument(
        "--quality",
        type=int,
        default=DEFAULT_QUALITY,
        help=f"WebP quality for standalone embed (default {DEFAULT_QUALITY})",
    )
    parser.add_argument(
        "--image-scope",
        choices=IMAGE_SCOPES,
        default=DEFAULT_IMAGE_SCOPE,
        help=(
            "Standalone images to embed: description (marketing/detail photos, default) "
            "or thumb (first marketing photo only, smallest file)"
        ),
    )
    args = parser.parse_args()

    if not SCRAPER_JSON.exists():
        raise SystemExit(f"Missing scraper data: {SCRAPER_JSON}")

    data = build_catalog_data()
    standalone = not args.linked
    output = OUTPUT_LINKED if args.linked else OUTPUT
    write_catalog_html(
        data,
        output,
        standalone=standalone,
        max_width=args.max_width,
        quality=args.quality,
        image_scope=args.image_scope,
    )


if __name__ == "__main__":
    main()
