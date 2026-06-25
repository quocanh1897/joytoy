"""JoyToy Warhammer sidebar categories — names and collection URLs."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://joytoy.com"

# Official JoyToy Warhammer filter order (sidebar on warhammer-action-figure).
# collection_path is the URL path; priority resolves overlaps (higher wins).
@dataclass(frozen=True)
class JoyToyCategory:
    id: str
    label_en: str
    label_vi: str
    collection_path: str
    priority: int = 50


def _slugify(label: str) -> str:
    s = label.lower().replace("'", "")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


GENERIC_PRIORITY = 15
SPECIFIC_PRIORITY = 50
PRIMARCH_PRIORITY = 100

JOYTOY_CATEGORIES: list[JoyToyCategory] = [
    JoyToyCategory("primarch", "Primarch", "Primarch", "/collections/primarch", PRIMARCH_PRIORITY),
    JoyToyCategory("adepta-sororitas", "Adepta Sororitas", "Adepta Sororitas", "/collections/adepta-sororitas"),
    JoyToyCategory("adeptus-custodes", "Adeptus Custodes", "Adeptus Custodes", "/collections/adeptus-custodes"),
    JoyToyCategory("adeptus-mechanicus", "Adeptus Mechanicus", "Adeptus Mechanicus", "/collections/adeptus-mechanicus"),
    JoyToyCategory("age-of-sigmar", "Age of Sigmar", "Age of Sigmar", "/collections/age-of-sigmar"),
    JoyToyCategory("alpha-legion", "Alpha Legion", "Alpha Legion", "/collections/alpha-legion"),
    JoyToyCategory("astra-militarum", "Astra Militarum", "Astra Militarum", "/collections/astra-militarum"),
    JoyToyCategory("black-legion", "Black Legion", "Black Legion", "/collections/black-legion"),
    JoyToyCategory("black-templars", "Black Templars", "Black Templars", "/collections/black-templars"),
    JoyToyCategory("blood-angels", "Blood Angels", "Blood Angels", "/collections/blood-angels"),
    JoyToyCategory(
        "chaos-space-marines",
        "Chaos Space Marines",
        "Chaos Space Marines",
        "/collections/chaos-space-marines",
        GENERIC_PRIORITY,
    ),
    JoyToyCategory("dark-angels", "Dark Angels", "Dark Angels", "/collections/dark-angels"),
    JoyToyCategory("death-guard", "Death Guard", "Death Guard", "/collections/death-guard"),
    JoyToyCategory("grey-knights", "Grey Knights", "Grey Knights", "/collections/grey-knights"),
    JoyToyCategory("imperial-fists", "Imperial Fists", "Imperial Fists", "/collections/imperial-fists"),
    JoyToyCategory("imperial-knights", "Imperial Knights", "Imperial Knights", "/collections/imperial-knights"),
    JoyToyCategory("iron-hands", "Iron Hands", "Iron Hands", "/collections/iron-hands"),
    JoyToyCategory("iron-warriors", "Iron Warriors", "Iron Warriors", "/collections/iron-warriors"),
    JoyToyCategory("night-lords", "Night Lords", "Night Lords", "/collections/night-lords"),
    JoyToyCategory("legio-custodes", "Legio Custodes", "Legio Custodes", "/collections/legio-custodes"),
    JoyToyCategory("necrons", "Necrons", "Necrons", "/collections/necrons"),
    JoyToyCategory("ork-kommandos", "Ork Kommandos", "Ork Kommandos", "/collections/ork-kommandos"),
    JoyToyCategory("raven-guard", "Raven Guard", "Raven Guard", "/collections/raven-guard"),
    JoyToyCategory("salamanders", "Salamanders", "Salamanders", "/collections/salamanders"),
    JoyToyCategory("sisters-of-silence", "Sisters of Silence", "Sisters of Silence", "/collections/sisters-of-silence"),
    JoyToyCategory("sons-of-horus", "Sons of Horus", "Sons of Horus", "/collections/sons-of-horus"),
    JoyToyCategory(
        "space-marine-ii",
        "Space Marine II",
        "Space Marine II",
        "/collections/space-marine-ii",
        GENERIC_PRIORITY,
    ),
    JoyToyCategory("space-wolves", "Space Wolves", "Space Wolves", "/collections/space-wolves"),
    JoyToyCategory("tau-empire", "T'au Empire", "T'au Empire", "/collections/tau-empire"),
    JoyToyCategory("thousand-sons", "Thousand Sons", "Thousand Sons", "/collections/thousand-sons"),
    JoyToyCategory("tyranids", "Tyranids", "Tyranids", "/collections/tyranids"),
    JoyToyCategory("ultramarines", "Ultramarines", "Ultramarines", "/collections/ultramarines"),
  # JoyToy routes White Consuls through /collections/space-marines (page title is White Consuls).
    JoyToyCategory("white-consuls", "White Consuls", "White Consuls", "/collections/space-marines"),
    JoyToyCategory("white-scars", "White Scars", "White Scars", "/collections/white-scars"),
    JoyToyCategory("world-eaters", "World Eaters", "World Eaters", "/collections/world-eaters"),
]

CATEGORY_ORDER = [cat.id for cat in JOYTOY_CATEGORIES]

CATEGORY_BY_ID = {cat.id: cat for cat in JOYTOY_CATEGORIES}


def normalize_product_slug(href: str) -> str | None:
    if not href or "javascript" in href:
        return None
    if "/products/" not in href:
        return None
    slug = href.strip("/").split("/")[-1]
    if not slug or slug == "products":
        return None
    return slug


def collect_collection_slugs(session: requests.Session, collection_path: str, delay: float = 0.25) -> set[str]:
    """Product slugs listed in a JoyToy collection (main grid only)."""
    seen: set[str] = set()
    page = 1
    while True:
        url = f"{BASE_URL}{collection_path}" if page == 1 else f"{BASE_URL}{collection_path}?page={page}"
        time.sleep(delay)
        response = session.get(url, timeout=60)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        page_slugs: set[str] = set()
        for anchor in soup.select(".list_products_item a[href]"):
            slug = normalize_product_slug(anchor.get("href", ""))
            if slug:
                page_slugs.add(slug)
        new = page_slugs - seen
        if not new:
            break
        seen |= new
        page += 1
    return seen


def build_category_map(session: requests.Session, delay: float = 0.25) -> dict[str, JoyToyCategory]:
    """Map product slug -> JoyToy category (highest priority when listed in multiple collections)."""
    assignments: dict[str, JoyToyCategory] = {}
    for category in sorted(JOYTOY_CATEGORIES, key=lambda c: c.priority, reverse=True):
        slugs = collect_collection_slugs(session, category.collection_path, delay=delay)
        for slug in slugs:
            current = assignments.get(slug)
            if current is None or category.priority > current.priority:
                assignments[slug] = category
    return assignments


def lookup_category(slug: str, name: str, joytoy_category: str | None) -> JoyToyCategory | None:
    if joytoy_category and joytoy_category in CATEGORY_BY_ID:
        return CATEGORY_BY_ID[joytoy_category]
    return None
