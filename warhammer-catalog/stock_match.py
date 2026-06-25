"""Map Discount.csv / stock_data.json rows onto scraped catalog products."""

from __future__ import annotations

import re
from typing import Any

UPC_IN_TEXT_RE = re.compile(r"UPC\s*[：:]\s*(\d{10,14})", re.I)
UPC_PREFIXES = (
    "697313037",
    "6927054400",
    "6927054401",
    "6927054402",
    "6927054403",
    "6927054404",
    "692705440",
)
COLLECTIVE_NOUNS = frozenset(
    {
        "squad",
        "cabal",
        "cadre",
        "pack",
        "team",
        "set",
        "company",
        "regiment",
        "battalion",
        "forces",
    }
)
STOP_WORDS = frozenset(
    {
        "warhammer",
        "40k",
        "k",
        "the",
        "with",
        "and",
        "of",
        "age",
        "sigmar",
        "40",
        "kina",
        "th",
    }
)
STOCK_NAME_ALIASES = (
    (re.compile(r"deathwing\s+terminator", re.I), "deathwing knight"),
)


ROMAN_NUMERALS = frozenset({"i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x"})


def _collapse_mk_tokens(words: list[str]) -> list[str]:
    collapsed: list[str] = []
    index = 0
    while index < len(words):
        word = words[index]
        if (
            word == "mk"
            and index + 1 < len(words)
            and words[index + 1] in ROMAN_NUMERALS
        ):
            collapsed.append(f"mk{words[index + 1]}")
            index += 2
            continue
        collapsed.append(word)
        index += 1
    return collapsed


def _words(text: str) -> list[str]:
    words = [
        word.lower()
        for word in re.findall(r"[a-z0-9']+", text, re.I)
        if len(word) > 1 and word.lower() not in STOP_WORDS
    ]
    return _collapse_mk_tokens(words)


def _normalize_stock_name(name: str) -> str:
    normalized = name
    for pattern, replacement in STOCK_NAME_ALIASES:
        normalized = pattern.sub(replacement, normalized)
    return normalized


def _product_match_words(name: str) -> list[str]:
    words = _words(name)
    while words and words[-1] in COLLECTIVE_NOUNS:
        words = words[:-1]
    return words


def _word_subsequence(product_words: list[str], stock_words: list[str]) -> bool:
    index = 0
    for word in product_words:
        while index < len(stock_words) and stock_words[index] != word:
            index += 1
        if index >= len(stock_words):
            return False
        index += 1
    return True


def product_upcs(product: dict[str, Any]) -> set[str]:
    upcs: set[str] = set()
    sku = (product.get("sku") or "").strip()
    if sku.isdigit() and len(sku) >= 10:
        upcs.add(sku)
    text = (product.get("description_text") or "") + (product.get("description_html") or "")
    upcs.update(UPC_IN_TEXT_RE.findall(text))
    return upcs


def jt_codes_from_upc(upc: str) -> list[str]:
    codes: list[str] = []
    for prefix in UPC_PREFIXES:
        if not upc.startswith(prefix):
            continue
        suffix = upc[len(prefix) :]
        for raw in {suffix, suffix.lstrip("0")}:
            if not raw:
                continue
            codes.extend(
                [
                    f"JT{raw}",
                    f"JT{raw.zfill(4)}",
                    f"JT{raw.zfill(5)}",
                ]
            )
    return list(dict.fromkeys(codes))


def _build_product_indexes(
    products: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], list[tuple[list[str], dict[str, Any]]]]:
    by_upc: dict[str, dict[str, Any]] = {}
    by_jt: dict[str, dict[str, Any]] = {}
    by_name: list[tuple[list[str], dict[str, Any]]] = []

    for product in products:
        for upc in product_upcs(product):
            by_upc.setdefault(upc, product)
            for jt_code in jt_codes_from_upc(upc):
                by_jt.setdefault(jt_code.upper(), product)
        name_words = _product_match_words(product.get("name") or "")
        if name_words:
            by_name.append((name_words, product))

    return by_upc, by_jt, by_name


def match_stock_row(
    row: dict[str, Any],
    *,
    by_upc: dict[str, dict[str, Any]],
    by_jt: dict[str, dict[str, Any]],
    by_name: list[tuple[list[str], dict[str, Any]]],
) -> tuple[dict[str, Any] | None, str, int]:
    """Return (product, method, priority). Higher priority wins per product."""
    stock_upc = (row.get("upc") or "").strip()
    stock_sku = (row.get("sku") or "").strip().upper()

    if stock_upc and stock_upc in by_upc:
        return by_upc[stock_upc], "upc", 300

    if stock_sku and stock_sku in by_jt:
        return by_jt[stock_sku], "jt", 280

    for jt_code in jt_codes_from_upc(stock_upc):
        product = by_jt.get(jt_code.upper())
        if product:
            return product, "jt-derived", 260

    stock_words = _words(_normalize_stock_name(row.get("name") or ""))
    best_product: dict[str, Any] | None = None
    best_len = 0
    for product_words, product in by_name:
        if len(product_words) < 2:
            continue
        if _word_subsequence(product_words, stock_words) and len(product_words) > best_len:
            best_len = len(product_words)
            best_product = product

    if best_product:
        return best_product, f"name:{best_len}", 100 + best_len

    return None, "", 0


def assign_stock_to_products(
    products: list[dict[str, Any]],
    stock_rows: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    """Map product slug -> chosen stock row. Each stock row matches at most one product."""
    by_upc, by_jt, by_name = _build_product_indexes(products)
    chosen: dict[str, tuple[dict[str, Any], int, str]] = {}
    unmatched: list[dict[str, Any]] = []
    methods: dict[str, int] = {}

    for row in stock_rows:
        product, method, priority = match_stock_row(
            row,
            by_upc=by_upc,
            by_jt=by_jt,
            by_name=by_name,
        )
        if not product:
            unmatched.append(row)
            continue

        methods[method.split(":")[0]] = methods.get(method.split(":")[0], 0) + 1
        slug = (product.get("slug") or product.get("name") or "").strip()
        if not slug:
            continue

        prev = chosen.get(slug)
        if prev is None or priority > prev[1]:
            chosen[slug] = (row, priority, method)

    stock_by_slug = {slug: row for slug, (row, _, _) in chosen.items()}
    return stock_by_slug, unmatched, methods
