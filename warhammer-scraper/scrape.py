#!/usr/bin/env python3
"""Scrape JoyToy Warhammer Action Figure collection."""

from __future__ import annotations

import argparse
import json
import re
import time
from html import unescape
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://joytoy.com"
COLLECTION_URL = f"{BASE_URL}/collections/warhammer-action-figure"
IMG_CDN = "https://img.joytoy.com"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
IMAGES_DIR = DATA_DIR / "images"
PRODUCTS_FILE = DATA_DIR / "products.json"


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"})
    return session


def fetch_html(session: requests.Session, url: str, delay: float) -> str:
    time.sleep(delay)
    response = session.get(url, timeout=60)
    response.raise_for_status()
    return response.text


def slug_from_path(path: str) -> str:
    return path.strip("/").split("/")[-1]


def normalize_product_path(href: str) -> str | None:
    if not href or "javascript" in href:
        return None
    if href.startswith("http"):
        parsed = urlparse(href)
        if "joytoy.com" not in parsed.netloc:
            return None
        path = parsed.path
    else:
        path = href
    if not path.startswith("/products/"):
        return None
    slug = slug_from_path(path)
    if not slug or slug == "products":
        return None
    return f"/products/{slug}"


def collect_product_paths(session: requests.Session, delay: float) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    page = 1

    while True:
        url = COLLECTION_URL if page == 1 else f"{COLLECTION_URL}?page={page}"
        html = fetch_html(session, url, delay)
        soup = BeautifulSoup(html, "html.parser")
        page_paths = []
        for anchor in soup.select(".list_products_item a[href]"):
            path = normalize_product_path(anchor["href"])
            if path and path not in seen:
                seen.add(path)
                ordered.append(path)
                page_paths.append(path)

        print(f"  page {page}: {len(page_paths)} new products ({len(ordered)} total)")
        if not page_paths:
            break
        page += 1

    return ordered


def parse_json_ld(html: str) -> dict[str, Any]:
    for match in re.finditer(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        re.S | re.I,
    ):
        try:
            data = json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and data.get("@type") == "Product":
            return data
    return {}


def parse_product_data(html: str) -> dict[str, Any]:
    match = re.search(r"product_data\s*=\s*(\{.*?\});", html, re.S)
    if not match:
        return {}
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return {}


def full_image_url(path: str) -> str:
    path = path.split("?")[0]
    if path.startswith("http"):
        return f"{path}?x-oss-process=image/quality,q_100"
    return f"{IMG_CDN}{path}?x-oss-process=image/quality,q_100"


def strip_html(html_fragment: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", html_fragment, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()


def extract_description_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for selector in (
        ".editor_txt.ck-content.themes_text_content",
        ".themes_text_content",
        ".products_detail_description",
        ".detail_description",
        "#description",
    ):
        node = soup.select_one(selector)
        if node and node.get_text(strip=True):
            return str(node)

    match = re.search(r"Material:.*?(?:Applicable Age:[^<]+)", html, re.S | re.I)
    return match.group(0) if match else ""


def collapse_spaced_numbers(text: str) -> str:
    """Turn '1 2. 5 x 6. 8 cm' into '12.5 x 6.8 cm'."""
    prev = None
    while prev != text:
        prev = text
        text = re.sub(r"(?<=\d)\s+(?=\d)", "", text)
        text = re.sub(r"(?<=\.)\s+(?=\d)", "", text)
        text = re.sub(r"(?<=\d)\s+(?=\.)", "", text)
    return text


def _floats_from_dimension_text(text: str) -> list[float]:
    """Parse cm numbers from strings like '12x6.8cm' or '19cm*9.5cm*7.5cm'."""
    text = collapse_spaced_numbers(text)
    cm_part = re.split(r"\(", text, maxsplit=1)[0]
    repeated_cm = re.findall(r"(\d+(?:\.\d+)?)\s*cm", cm_part, re.I)
    if len(repeated_cm) > 1:
        return [float(n) for n in repeated_cm]
    if re.search(r"[x×*]", cm_part, re.I):
        segment = cm_part.lower().split("cm")[0] if "cm" in cm_part.lower() else cm_part
        return [float(n) for n in re.findall(r"(\d+(?:\.\d+)?)", segment)]
    match = re.search(r"(\d+(?:\.\d+)?)\s*cm", text, re.I)
    if match:
        return [float(match.group(1))]
    match = re.search(r"(\d+(?:\.\d+)?)", cm_part)
    if match:
        return [float(match.group(1))]
    return []


def _inch_height_from_text(text: str) -> float | None:
    collapsed = re.sub(r"\s+", "", text)
    match = re.search(r"H[ei]ght:?(\d+(?:\.\d+)?)inches?", collapsed, re.I)
    if match:
        return float(match.group(1))
    match = re.search(
        r"\(\s*(\d+(?:\.\d+)?)\s*(?:x[\d.]+\s*)*in(?:ches)?\s*\)",
        text,
        re.I,
    )
    if match:
        return float(match.group(1))
    match = re.search(r"(\d+(?:\.\d+)?)\s*inches?", text, re.I)
    if match:
        return float(match.group(1))
    return None


def _cm_in_parens(text: str) -> float | None:
    match = re.search(r"\(\s*(\d+(?:\.\d+)?)\s*cm\s*\)", text, re.I)
    return float(match.group(1)) if match else None


def parse_figure_size(plain: str) -> tuple[float | None, float | None, str | None]:
    """Return figure height (cm), height (inches), and a display dimensions string."""
    height_cm: float | None = None
    height_in: float | None = None
    dims_display: str | None = None

    height_line = re.search(r"Height\s*[:：]?\s*([^\n]+)", plain, re.I)
    if height_line:
        segment = height_line.group(1)
        height_cm = _cm_in_parens(segment)
        if height_cm is None:
            height_in = _inch_height_from_text(segment)

    size_line = re.search(
        r"(?:Product\s*S\s*ize|Product\s*Size|Product\s*Dimensions|^Size)\s*[:：]\s*([^\n]+)",
        plain,
        re.I | re.M,
    )
    if size_line:
        raw = size_line.group(1).strip()
        dims_display = collapse_spaced_numbers(raw)
        numbers = _floats_from_dimension_text(raw)
        if numbers:
            height_cm = numbers[0]
        elif height_in is None:
            inch = _inch_height_from_text(raw)
            if inch:
                height_in = inch

    if height_cm is None and height_in is not None:
        height_cm = round(height_in * 2.54, 2)

    return height_cm, height_in, dims_display


def extract_specs(description_html: str, plain: str) -> dict[str, Any]:
    specs: dict[str, Any] = {
        "material": None,
        "scale": None,
        "height_inches": None,
        "size_cm": None,
        "product_dimensions_cm": None,
        "package_size_cm": None,
        "package_weight_kg": None,
        "applicable_age": None,
    }

    patterns = {
        "material": r"Materials?:\s*([^\n<]+)",
        "scale": r"(?:Product\s+)?Scale:\s*([^\n<]+)",
        "applicable_age": r"Applicable Age:\s*([^\n<]+)",
        "package_size_cm": r"Package Size:\s*([^\n<]+)",
        "package_weight_kg": r"Package Weight:\s*([^\n<]+)",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, plain, re.I)
        if match:
            specs[key] = match.group(1).strip()

    height_cm, height_in, dims_display = parse_figure_size(plain)
    specs["height_inches"] = height_in
    specs["size_cm"] = height_cm
    if dims_display:
        specs["product_dimensions_cm"] = dims_display
    else:
        dim_match = re.search(r"Product Dimensions:\s*([^\n<]+)", plain, re.I)
        if dim_match:
            specs["product_dimensions_cm"] = collapse_spaced_numbers(dim_match.group(1).strip())

    if specs["size_cm"] is None and specs["product_dimensions_cm"]:
        numbers = _floats_from_dimension_text(specs["product_dimensions_cm"])
        if numbers:
            specs["size_cm"] = max(numbers)

    return specs


def extract_listing_price(html: str) -> float | None:
    match = re.search(
        r"""class=['"]price_data[^'"]*['"][^>]*data=['"](\d+(?:\.\d+)?)['"]""",
        html,
    )
    if match:
        return float(match.group(1))
    match = re.search(
        r"""class=['"]themes_products_price[^'"]*['"][^>]*>.*?(\d+(?:\.\d+)?)""",
        html,
        re.S,
    )
    if match:
        return float(match.group(1))
    return None


def extract_images(html: str, product_data: dict[str, Any], description_html: str = "") -> dict[str, list[str]]:
    product_images: list[str] = []
    description_images: list[str] = []
    seen: set[str] = set()

    def add(target: list[str], url: str) -> None:
        url = full_image_url(url)
        if url not in seen:
            seen.add(url)
            target.append(url)

    for path in product_data.get("picture_data", []):
        add(product_images, path)

    gallery = re.search(
        r'class="[^"]*item_img[^"]*".*?</div>\s*</div>\s*</div>',
        html,
        re.S,
    )
    gallery_html = gallery.group(0) if gallery else html
    for path in re.findall(r"""data-large=["']([^"']+)["']""", gallery_html):
        add(product_images, path)

    if description_html:
        for path in re.findall(
            r"""src=["'](https://img\.joytoy\.com/[^"']+)["']""",
            description_html,
        ):
            add(description_images, path)

    return {
        "images": product_images,
        "description_images": description_images,
    }


def scrape_product(
    session: requests.Session,
    path: str,
    delay: float,
) -> dict[str, Any]:
    url = urljoin(BASE_URL, path)
    slug = slug_from_path(path)
    html = fetch_html(session, url, delay)

    json_ld = parse_json_ld(html)
    product_data = parse_product_data(html)
    soup = BeautifulSoup(html, "html.parser")

    name = json_ld.get("name")
    if not name:
        h1 = soup.find("h1")
        name = h1.get_text(strip=True) if h1 else slug.replace("-", " ").title()

    sku = (json_ld.get("sku") or json_ld.get("productID") or "").strip()
    if not sku:
        sku_node = soup.select_one(".prod_info_sku, .sku")
        if sku_node:
            sku = re.sub(r"^SKU:\s*", "", sku_node.get_text(strip=True), flags=re.I)

    offers = json_ld.get("offers", {})
    price_usd = None
    if isinstance(offers, dict) and offers.get("price") not in (None, ""):
        try:
            price_usd = float(str(offers["price"]).replace(",", ""))
        except ValueError:
            price_usd = None
    if price_usd is None:
        price_usd = extract_listing_price(html)

    availability = None
    if isinstance(offers, dict):
        availability = offers.get("availability", "")
        if availability:
            availability = availability.rsplit("/", 1)[-1]

    description_html = extract_description_html(html)
    description_text = strip_html(description_html) if description_html else ""
    if not description_text:
        meta = soup.find("meta", attrs={"name": "description"})
        if meta and meta.get("content"):
            description_text = meta["content"].strip()

    specs = extract_specs(description_html, description_text)
    detail_node = soup.select_one(".detail_description")
    detail_html = str(detail_node) if detail_node else description_html
    image_sets = extract_images(html, product_data, detail_html)

    return {
        "name": name,
        "slug": slug,
        "url": url,
        "sku": sku,
        "price_usd": price_usd,
        "price_currency": offers.get("priceCurrency", "USD") if isinstance(offers, dict) else "USD",
        "availability": availability,
        "size_cm": specs["size_cm"],
        "height_inches": specs["height_inches"],
        "product_dimensions_cm": specs["product_dimensions_cm"],
        "package_size_cm": specs["package_size_cm"],
        "package_weight_kg": specs["package_weight_kg"],
        "scale": specs["scale"],
        "material": specs["material"],
        "applicable_age": specs["applicable_age"],
        "description_text": description_text,
        "description_html": description_html,
        "images": image_sets["images"],
        "description_images": image_sets["description_images"],
        "local_images": [],
        "local_description_images": [],
        "scraped_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def download_images(
    session: requests.Session,
    product: dict[str, Any],
    delay: float,
) -> tuple[list[str], list[str]]:
    slug = product["slug"]
    out_dir = IMAGES_DIR / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    desc_dir = out_dir / "description"
    local_paths: list[str] = []
    local_desc_paths: list[str] = []

    for index, image_url in enumerate(product.get("images", []), start=1):
        filename = f"{index:03d}{Path(urlparse(image_url).path).suffix or '.jpg'}"
        dest = out_dir / filename
        rel_path = str(dest.relative_to(ROOT))

        if dest.exists() and dest.stat().st_size > 0:
            local_paths.append(rel_path)
            continue

        time.sleep(delay)
        try:
            response = session.get(image_url, timeout=90)
            response.raise_for_status()
            dest.write_bytes(response.content)
            local_paths.append(rel_path)
            print(f"    saved {rel_path}")
        except requests.RequestException as exc:
            print(f"    failed image {image_url}: {exc}")

    if product.get("description_images"):
        desc_dir.mkdir(parents=True, exist_ok=True)
        for index, image_url in enumerate(product["description_images"], start=1):
            filename = f"{index:03d}{Path(urlparse(image_url).path).suffix or '.jpg'}"
            dest = desc_dir / filename
            rel_path = str(dest.relative_to(ROOT))

            if dest.exists() and dest.stat().st_size > 0:
                local_desc_paths.append(rel_path)
                continue

            time.sleep(delay)
            try:
                response = session.get(image_url, timeout=90)
                response.raise_for_status()
                dest.write_bytes(response.content)
                local_desc_paths.append(rel_path)
                print(f"    saved {rel_path}")
            except requests.RequestException as exc:
                print(f"    failed image {image_url}: {exc}")

    return local_paths, local_desc_paths


def load_existing() -> dict[str, Any]:
    if PRODUCTS_FILE.exists():
        return json.loads(PRODUCTS_FILE.read_text(encoding="utf-8"))
    return {
        "source_url": COLLECTION_URL,
        "scraped_at": None,
        "product_count": 0,
        "products": [],
    }


def save_catalog(catalog: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    catalog["product_count"] = len(catalog["products"])
    PRODUCTS_FILE.write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def fix_marketing_sizes_in_catalog(
    catalog: dict[str, Any],
    *,
    only_missing: bool = False,
) -> int:
    """OCR marketing photos and store marketing_size_cm on each product."""
    from size_extract import SUSPICIOUS_SIZES, extract_marketing_size_cm

    changed = 0
    products = catalog.get("products", [])
    total = len(products)
    for index, product in enumerate(products, start=1):
        old = product.get("marketing_size_cm")
        if only_missing and old is not None:
            try:
                if float(old) not in SUSPICIOUS_SIZES:
                    continue
            except (TypeError, ValueError):
                pass
        value = extract_marketing_size_cm(product)
        if value is None:
            continue
        if value != old:
            product["marketing_size_cm"] = value
            changed += 1
        if index % 25 == 0 or index == total:
            print(f"  marketing sizes: {index}/{total}")
    return changed


def fix_sizes_in_catalog(catalog: dict[str, Any]) -> int:
    """Re-parse figure sizes from stored descriptions. Returns number of changed products."""
    changed = 0
    for product in catalog.get("products", []):
        plain = product.get("description_text") or ""
        if not plain:
            continue
        specs = extract_specs(product.get("description_html") or "", plain)
        old = (
            product.get("size_cm"),
            product.get("height_inches"),
            product.get("product_dimensions_cm"),
        )
        new = (
            specs["size_cm"],
            specs["height_inches"],
            specs["product_dimensions_cm"],
        )
        if old != new:
            product["size_cm"] = specs["size_cm"]
            product["height_inches"] = specs["height_inches"]
            product["product_dimensions_cm"] = specs["product_dimensions_cm"]
            changed += 1
    return changed


def apply_joytoy_categories(catalog: dict[str, Any], session: requests.Session, delay: float) -> int:
    from joytoy_categories import build_category_map

    print("Fetching JoyToy collection categories...")
    slug_to_category = build_category_map(session, delay=delay)
    changed = 0
    for product in catalog.get("products", []):
        slug = product.get("slug")
        if not slug:
            continue
        category = slug_to_category.get(slug)
        new_id = category.id if category else None
        if product.get("joytoy_category") != new_id:
            if new_id:
                product["joytoy_category"] = new_id
                product["joytoy_category_en"] = category.label_en
            else:
                product.pop("joytoy_category", None)
                product.pop("joytoy_category_en", None)
            changed += 1
    mapped = sum(1 for p in catalog.get("products", []) if p.get("joytoy_category"))
    print(f"Mapped {mapped}/{len(catalog.get('products', []))} products to JoyToy categories")
    return changed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=0, help="Max products to scrape (0 = all)")
    parser.add_argument("--no-images", action="store_true", help="Skip image downloads")
    parser.add_argument("--resume", action="store_true", default=True, help="Skip completed products")
    parser.add_argument("--no-resume", action="store_false", dest="resume", help="Re-scrape all products")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between HTTP requests (seconds)")
    parser.add_argument(
        "--fix-sizes",
        action="store_true",
        help="Re-parse figure sizes from stored descriptions and exit",
    )
    parser.add_argument(
        "--extract-marketing-sizes",
        action="store_true",
        help="OCR marketing photos for height labels (e.g. '20cm action figure') and exit",
    )
    parser.add_argument(
        "--only-missing",
        action="store_true",
        help="With --extract-marketing-sizes, only process products without marketing_size_cm",
    )
    parser.add_argument(
        "--scrape-categories",
        action="store_true",
        help="Assign joytoy_category from JoyToy collection pages and exit",
    )
    args = parser.parse_args()

    if args.scrape_categories:
        catalog = load_existing()
        session = make_session()
        changed = apply_joytoy_categories(catalog, session, args.delay)
        save_catalog(catalog)
        print(f"Updated categories for {changed} products in {PRODUCTS_FILE}")
        return

    if args.extract_marketing_sizes:
        catalog = load_existing()
        changed = fix_marketing_sizes_in_catalog(catalog, only_missing=args.only_missing)
        save_catalog(catalog)
        print(f"Updated marketing sizes for {changed} products in {PRODUCTS_FILE}")
        return

    if args.fix_sizes:
        catalog = load_existing()
        changed = fix_sizes_in_catalog(catalog)
        save_catalog(catalog)
        print(f"Updated sizes for {changed} products in {PRODUCTS_FILE}")
        return

    session = make_session()
    catalog = load_existing()
    products_by_slug: dict[str, dict[str, Any]] = {
        p["slug"]: p for p in catalog.get("products", []) if p.get("slug")
    }

    print("Collecting product URLs...")
    paths = collect_product_paths(session, args.delay)
    if args.limit:
        paths = paths[: args.limit]
    print(f"Found {len(paths)} products to process")

    for index, path in enumerate(paths, start=1):
        slug = slug_from_path(path)
        cached = products_by_slug.get(slug)
        needs_scrape = not (
            args.resume
            and cached
            and cached.get("name")
            and cached.get("images")
            and not cached.get("error")
        )

        if needs_scrape:
            print(f"[{index}/{len(paths)}] scraping {slug}")
            try:
                product = scrape_product(session, path, args.delay)
            except requests.RequestException as exc:
                print(f"  error: {exc}")
                product = cached or {
                    "slug": slug,
                    "url": urljoin(BASE_URL, path),
                    "error": str(exc),
                }
                product.setdefault("images", [])
            products_by_slug[slug] = product
        else:
            product = cached
            print(f"[{index}/{len(paths)}] skip {slug} (cached)")

        if not args.no_images and (product.get("images") or product.get("description_images")):
            needs_images = (
                not product.get("local_images")
                or len(product.get("local_images", [])) < len(product.get("images", []))
                or len(product.get("local_description_images", [])) < len(product.get("description_images", []))
            )
            if needs_images:
                image_count = len(product.get("images", [])) + len(product.get("description_images", []))
                print(f"  downloading {image_count} images...")
                local_images, local_description_images = download_images(
                    session, product, max(args.delay / 2, 0.25)
                )
                product["local_images"] = local_images
                product["local_description_images"] = local_description_images
            products_by_slug[slug] = product

        catalog["products"] = sorted(
            products_by_slug.values(),
            key=lambda item: item.get("name", item.get("slug", "")).lower(),
        )
        catalog["scraped_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        save_catalog(catalog)

    print(f"\nDone. {len(catalog['products'])} products saved to {PRODUCTS_FILE}")


if __name__ == "__main__":
    main()
