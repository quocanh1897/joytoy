#!/usr/bin/env python3
"""Generate compact catalog records and optimized static images for Astro."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import sys
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps

WEB_DIR = Path(__file__).resolve().parent.parent
ROOT = WEB_DIR.parent
CATALOG_DIR = ROOT / "warhammer-catalog"
PUBLIC_DIR = WEB_DIR / "public"
MEDIA_DIR = PUBLIC_DIR / "media"
GENERATED_DIR = WEB_DIR / "src" / "generated"
PUBLIC_DATA_DIR = PUBLIC_DIR / "data"

sys.path.insert(0, str(CATALOG_DIR))
import build_catalog  # noqa: E402

THUMB_MAX = 360
GALLERY_MAX = 960
THUMB_QUALITY = 65
GALLERY_QUALITY = 72
PLACEHOLDER = {
    "src": "/placeholder.svg",
    "width": 720,
    "height": 720,
}


def source_for_catalog_path(value: str) -> Path | None:
    source = build_catalog.catalog_path_to_local(value)
    return source if source and source.exists() else None


def convert_image(task: tuple[str, str, int, int]) -> tuple[str, int, int, int]:
    source_text, output_text, max_edge, quality = task
    source = Path(source_text)
    output = Path(output_text)
    output.parent.mkdir(parents=True, exist_ok=True)

    if output.exists() and output.stat().st_mtime_ns >= source.stat().st_mtime_ns:
        with Image.open(output) as cached:
            return output_text, cached.width, cached.height, output.stat().st_size

    with Image.open(source) as original:
        frame = ImageOps.exif_transpose(original)
        if getattr(frame, "is_animated", False):
            frame.seek(0)
        if frame.mode not in ("RGB", "RGBA"):
            frame = frame.convert("RGBA" if "A" in frame.getbands() else "RGB")
        frame.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
        frame.save(output, "WEBP", quality=quality, method=4, exact=True)
        width, height = frame.size
    return output_text, width, height, output.stat().st_size


def normalize_stock(stock: dict[str, Any] | None) -> dict[str, Any] | None:
    if not stock:
        return None
    return {
        "sku": stock.get("sku"),
        "qty": stock.get("qty"),
        "priceVnd": stock.get("price_vnd"),
        "deposit": stock.get("deposit"),
    }


def prepare(*, skip_images: bool) -> None:
    raw = build_catalog.build_catalog_data()
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    PUBLIC_DATA_DIR.mkdir(parents=True, exist_ok=True)

    MEDIA_DIR.mkdir(parents=True, exist_ok=True)

    tasks: list[tuple[str, str, int, int]] = []
    product_sources: dict[str, list[Path]] = {}
    expected_outputs: set[Path] = set()

    for product in raw["products"]:
        slug = product["slug"]
        sources = [
            source
            for image in product.get("images") or []
            if (source := source_for_catalog_path(image)) is not None
        ]
        product_sources[slug] = sources
        if skip_images:
            continue
        for index, source in enumerate(sources, start=1):
            output = MEDIA_DIR / "gallery" / slug / f"{index:03d}.webp"
            expected_outputs.add(output)
            tasks.append((str(source), str(output), GALLERY_MAX, GALLERY_QUALITY))
        if sources:
            output = MEDIA_DIR / "thumbs" / f"{slug}.webp"
            expected_outputs.add(output)
            tasks.append((str(sources[0]), str(output), THUMB_MAX, THUMB_QUALITY))

    image_meta: dict[str, tuple[int, int, int]] = {}
    if not skip_images:
        workers = min(8, max(1, os.cpu_count() or 1))
        print(f"Preparing {len(tasks)} WebP assets with {workers} workers…", flush=True)
        with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
            for index, (output, width, height, size) in enumerate(
                pool.map(convert_image, tasks, chunksize=12), start=1
            ):
                image_meta[output] = (width, height, size)
                if index % 500 == 0:
                    print(f"  prepared {index}/{len(tasks)}", flush=True)
        for stale in (path for path in MEDIA_DIR.rglob("*") if path.is_file() and path not in expected_outputs):
            stale.unlink()

    products: list[dict[str, Any]] = []
    missing_images = 0
    for product in raw["products"]:
        slug = product["slug"]
        sources = product_sources[slug]
        gallery: list[dict[str, Any]] = []
        for index, _source in enumerate(sources, start=1):
            output = MEDIA_DIR / "gallery" / slug / f"{index:03d}.webp"
            meta = image_meta.get(str(output))
            if meta is None and output.exists():
                with Image.open(output) as image:
                    meta = (image.width, image.height, output.stat().st_size)
            if meta is None:
                missing_images += 1
                continue
            gallery.append(
                {
                    "src": f"/media/gallery/{slug}/{index:03d}.webp",
                    "width": meta[0],
                    "height": meta[1],
                }
            )

        thumb_output = MEDIA_DIR / "thumbs" / f"{slug}.webp"
        thumb_meta = image_meta.get(str(thumb_output))
        if thumb_meta is None and thumb_output.exists():
            with Image.open(thumb_output) as image:
                thumb_meta = (image.width, image.height, thumb_output.stat().st_size)
        thumbnail = (
            {
                "src": f"/media/thumbs/{slug}.webp",
                "width": thumb_meta[0],
                "height": thumb_meta[1],
            }
            if thumb_meta
            else PLACEHOLDER
        )

        products.append(
            {
                "slug": slug,
                "name": product.get("name") or "Untitled model",
                "upc": product.get("upc") or None,
                "url": product.get("url") or None,
                "categoryId": product["category_id"],
                "categoryEn": product["category_en"],
                "categoryVi": product["category_vi"],
                "priceUsd": product.get("price_usd"),
                "availability": product.get("availability"),
                "scale": product.get("scale") or None,
                "material": product.get("material") or None,
                "size": product.get("size") or None,
                "sizeCm": product.get("size_cm"),
                "thumbnail": thumbnail,
                "galleryCount": len(gallery),
                "gallery": gallery,
                "boxContents": product.get("box_contents") or [],
                "stock": normalize_stock(product.get("stock")),
            }
        )

    categories = [
        {
            "id": category["id"],
            "labelEn": category["label_en"],
            "labelVi": category["label_vi"],
            "count": category["count"],
        }
        for category in raw["categories"]
    ]
    catalog = {
        "generatedAt": raw.get("generated_at"),
        "productCount": len(products),
        "categories": categories,
        "products": products,
    }
    summaries = [
        {key: value for key, value in product.items() if key not in {"gallery", "boxContents"}}
        for product in products
    ]
    index = {
        "generatedAt": catalog["generatedAt"],
        "productCount": catalog["productCount"],
        "categories": categories,
        "products": summaries,
    }

    options = {"ensure_ascii": False, "separators": (",", ":")}
    (GENERATED_DIR / "catalog.json").write_text(
        json.dumps(catalog, **options), encoding="utf-8"
    )
    (PUBLIC_DATA_DIR / "catalog-index.json").write_text(
        json.dumps(index, **options), encoding="utf-8"
    )

    media_files = [path for path in MEDIA_DIR.rglob("*") if path.is_file()]
    media_bytes = sum(path.stat().st_size for path in media_files)
    print(
        f"Prepared {len(products)} products, {len(categories)} categories, "
        f"{len(media_files)} media files ({media_bytes / 1024 / 1024:.1f} MiB), "
        f"{missing_images} missing outputs."
    )
    if missing_images:
        raise SystemExit("Image preparation left missing outputs")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-images",
        action="store_true",
        help="Regenerate JSON using existing media outputs without converting images",
    )
    args = parser.parse_args()
    prepare(skip_images=args.skip_images)


if __name__ == "__main__":
    main()
