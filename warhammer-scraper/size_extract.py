"""Extract marketing height (e.g. '20cm action figure') from product photos."""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance, ImageOps

try:
    import pytesseract
except ImportError:  # pragma: no cover
    pytesseract = None

ROOT = Path(__file__).resolve().parent

ACTION_FIGURE_RE = re.compile(r"ac[t]?ion\s+fig", re.I)
ARTICULATED_RE = re.compile(r"art[il][a-z]*c?ulat", re.I)
# OCR often misreads 18cm as 48cm / 78cm on marketing labels.
SUSPICIOUS_SIZES = {38, 48, 58, 68, 78, 88}

# Number + mangled cm + action figure (covers 10.7om, 20,5em, 12.4¢m, etc.)
ACTION_SIZE_RE = re.compile(
    r"(?:^|[^\d])"
    r"(?P<size>\d{1,2}(?:[.,]\d{1,2})?)"
    r"\s*"
    r"(?P<unit>c[o0]?m|c[eE]m|o[mM]|em|com|¢m|\?cm|\.?cm)"
    r"\s+action\s+fig",
    re.I,
)

MARKETING_SIZE_PATTERNS = (
    r"(\d{1,2}(?:[.,]\d{1,2})?)\s*c[mi][a-zA-Z.¢?]{0,4}",
    r"(\d{2,3})\s*厘米",
    r"(\d{2,3})\s*mm\b",
)


def _parse_size_token(token: str) -> float | None:
    text = token.strip().replace(",", ".")
    text = re.sub(r"\.(\d)$", r".\1", text)
    if not text or not re.fullmatch(r"\d{1,2}(?:\.\d{1,2})?", text):
        return None
    value = float(text)
    if 8 <= value <= 45:
        return value
    return None


def normalize_marketing_ocr(text: str) -> str:
    flat = " ".join(text.split())
    flat = flat.replace("¢", "c")
    flat = re.sub(r"\blO\.?\s*(\d)", r"10.\1", flat, flags=re.I)
    flat = re.sub(r"(\d{1,2})\s*\.\s*(\d)", r"\1.\2", flat)
    flat = re.sub(r"(\d),(\d)", r"\1.\2", flat)
    flat = re.sub(r"(\d)O(?=[CcMmTt])", r"\g<1>0", flat)
    flat = re.sub(r"(\d)O(?=\s*(?:ac|Ac))", r"\g<1>0", flat)
    flat = re.sub(r"(\d)\?(\d)", r"\1.\2", flat)
    return flat


def _score_candidate(value: float, source: str) -> float:
    score = 0.0
    if value in SUSPICIOUS_SIZES:
        score += 60
    if source in {"fuzzy_bom", "fuzzy_tgom", "fuzzy_jcm"}:
        score -= 20
    elif source == "action_size":
        score -= 18
    elif source == "strict_cm_action":
        score -= 15
    elif source == "cm_near_action":
        score -= 8
    if 15 <= value <= 22:
        score -= 6
    elif 10 <= value <= 14:
        score -= 4
    elif 20 <= value <= 25:
        score -= 3
    # Prefer typical figure heights over odd OCR fragments.
    if value > 30:
        score += 15
    if abs(value - round(value)) > 0.01:
        score -= 2
    return score


def _collect_action_figure_sizes(flat: str) -> list[tuple[float, float]]:
    candidates: list[tuple[float, float]] = []

    for match in ACTION_SIZE_RE.finditer(flat):
        raw = match.group("size")
        value = _parse_size_token(raw)
        if value is not None:
            candidates.append((value, _score_candidate(value, "action_size")))
        if value is not None and value > 45 and len(raw) >= 4:
            alt = _parse_size_token(raw[1:])
            if alt is not None:
                candidates.append((alt, _score_candidate(alt, "action_size") - 3))

    for match in re.finditer(
        r"(\d{1,2}(?:[.,]\d{1,2})?)\s*a?c?l?ion\s+fig",
        flat,
        re.I,
    ):
        value = _parse_size_token(match.group(1).replace(",", "."))
        if value is not None:
            candidates.append((value, _score_candidate(value, "action_size")))

    if re.search(r"[Tt1]{1,2}i?em\s+action\s+fig", flat, re.I):
        candidates.append((11.0, _score_candidate(11.0, "fuzzy_tiem")))

    for match in re.finditer(r"articulat", flat, re.I):
        before = flat[max(0, match.start() - 55) : match.start()]
        near = re.search(
            r"(\d{1,2}(?:[.,]\d{1,2})?)\s*(?:cm|em|om|aclion|action)",
            before,
            re.I,
        )
        if near:
            value = _parse_size_token(near.group(1))
            if value is not None:
                candidates.append((value, _score_candidate(value, "action_size") - 2))

    for match in re.finditer(
        r"(\d{3}[.,]\d{1,2})\s*(?:c[o0]?m|o[mM]|em|com|¢m|a?c?l?ion)\s+fig",
        flat,
        re.I,
    ):
        raw = match.group(1).replace(",", ".")
        alt = _parse_size_token(raw[1:])
        if alt is not None:
            candidates.append((alt, _score_candidate(alt, "action_size") - 4))

    for match in re.finditer(r"(\d)\s*[Bb8](?:om|cm|m)\s+action", flat, re.I):
        value = float(match.group(1) + "8")
        if 10 <= value <= 45:
            candidates.append((value, _score_candidate(value, "fuzzy_bom")))

    if re.search(r"[Tt1][Gg8](?:om|cm|m)\s+action", flat, re.I):
        candidates.append((18.0, _score_candidate(18.0, "fuzzy_tgom")))

    if re.search(r"[J1][&8]\s*cm\s+action", flat, re.I):
        candidates.append((18.0, _score_candidate(18.0, "fuzzy_jcm")))

    for match in re.finditer(r"(\d{1,2})\s*O[Cc][MmTt]", flat):
        value = float(match.group(1) + "0")
        if 10 <= value <= 45:
            candidates.append((value, _score_candidate(value, "fuzzy_oct")))

    for match in re.finditer(r"(\d{2,3})\s*cm\s+action", flat, re.I):
        value = float(match.group(1))
        if 10 <= value <= 45 and value not in SUSPICIOUS_SIZES:
            candidates.append((value, _score_candidate(value, "strict_cm_action")))

    for match in re.finditer(r"(\d{1,2}(?:\.\d{1,2})?)\s*cm", flat, re.I):
        after = flat[match.end() : match.end() + 40]
        if ACTION_FIGURE_RE.search(after):
            value = _parse_size_token(match.group(1))
            if value is not None:
                candidates.append((value, _score_candidate(value, "cm_near_action")))

    return candidates


def _collect_all_size_candidates(text: str) -> list[float]:
    flat = normalize_marketing_ocr(text)
    scored = _collect_action_figure_sizes(flat)
    return [value for value, _score in scored]


# OCR often reads 10.7 as 16.7 / 19.7 on the same label.
_CONFUSION_PAIRS = (
    (16.7, 10.7),
    (19.7, 10.7),
    (17.7, 10.7),
)


def _pick_best_size(values: list[float]) -> float | None:
    if not values:
        return None

    from collections import Counter

    rounded = [round(value, 1) for value in values]
    counts = Counter(rounded)

    for wrong, right in _CONFUSION_PAIRS:
        if counts[right] and counts[wrong]:
            if counts[right] >= counts[wrong]:
                counts[wrong] = 0

    best_value, best_count = counts.most_common(1)[0]
    if best_count >= 2:
        return best_value

    scored = [(value, _score_candidate(value, "action_size")) for value in values]
    return min(scored, key=lambda item: item[1])[0]


def parse_marketing_size_text(text: str) -> float | None:
    flat = normalize_marketing_ocr(text)

    if ACTION_FIGURE_RE.search(flat) or ARTICULATED_RE.search(flat):
        values = _collect_all_size_candidates(text)
        value = _pick_best_size(values)
        if value is not None:
            return value

    for pattern in MARKETING_SIZE_PATTERNS:
        match = re.search(pattern, flat, re.I)
        if not match:
            continue
        value = _parse_size_token(match.group(1))
        if value is None:
            value = float(match.group(1).replace(",", "."))
        token = match.group(0).lower()
        if "mm" in token and value > 45:
            value = round(value / 10, 1)
        if 10 <= value <= 45 and value not in SUSPICIOUS_SIZES:
            return value
    return None


def _ocr_image_region(proc: Image.Image) -> str:
    if pytesseract is None:
        return ""
    return pytesseract.image_to_string(proc, config="--psm 6")


def _ocr_single_pass(arr: np.ndarray, y_start: float, mask_thresh: int) -> str:
    height, width, _ = arr.shape
    roi = arr[int(height * y_start) :, : int(width * 0.92)]
    gray = roi.mean(axis=2)
    mask = gray > mask_thresh
    proc = Image.fromarray((mask * 255).astype("uint8"))
    proc = proc.resize(
        (max(proc.width * 4, 480), max(proc.height * 4, 96)),
        Image.NEAREST,
    )
    return _ocr_image_region(proc)


def _ocr_bottom_text(img_path: Path, *, thorough: bool = False) -> str:
    if pytesseract is None:
        return ""
    im = Image.open(img_path).convert("RGB")
    arr = np.array(im)
    texts = [_ocr_single_pass(arr, 0.74, 130)]

    if thorough:
        height, width, _ = arr.shape
        for y_start in (0.68, 0.80):
            texts.append(_ocr_single_pass(arr, y_start, 140))
        gray = arr[int(height * 0.74) :, : int(width * 0.92)].mean(axis=2)
        band = Image.fromarray(gray.astype("uint8"))
        band = ImageOps.autocontrast(band)
        band = ImageEnhance.Contrast(band).enhance(2.5)
        band = band.resize((max(band.width * 4, 480), max(band.height * 4, 96)), Image.NEAREST)
        texts.append(_ocr_image_region(band))

    return "\n".join(texts)


def marketing_image_candidates(product: dict) -> list[Path]:
    """Prefer hero marketing shots that usually contain the height label."""
    slug = product.get("slug", "")
    desc_dir = ROOT / "data" / "images" / slug / "description"
    preferred_names = [
        "001.jpg",
        "001.png",
        "001.gif",
        "002.jpg",
        "002.gif",
        "005.jpg",
        "005.png",
    ]
    paths: list[Path] = []
    seen: set[str] = set()

    for name in preferred_names:
        path = desc_dir / name
        if path.exists():
            key = str(path)
            if key not in seen:
                seen.add(key)
                paths.append(path)

    for local in product.get("local_description_images") or []:
        path = ROOT / local
        key = str(path)
        if path.exists() and key not in seen:
            seen.add(key)
            paths.append(path)
    return paths


def extract_marketing_size_cm(product: dict) -> float | None:
    """OCR marketing photos for a height label."""
    if pytesseract is None:
        return None

    paths = marketing_image_candidates(product)
    if not paths:
        return None

    all_values: list[float] = []
    for index, path in enumerate(paths):
        try:
            thorough = index >= 3
            text = _ocr_bottom_text(path, thorough=thorough)
            all_values.extend(_collect_all_size_candidates(text))
            if not all_values:
                all_values.extend(
                    v
                    for v in [_parse_marketing_fallback(text)]
                    if v is not None
                )
            picked = _pick_best_size(all_values)
            if picked is not None and sum(1 for v in all_values if round(v, 1) == round(picked, 1)) >= 2:
                return picked
        except OSError:
            continue

    return _pick_best_size(all_values)


def _parse_marketing_fallback(text: str) -> float | None:
    flat = normalize_marketing_ocr(text)
    for pattern in MARKETING_SIZE_PATTERNS:
        match = re.search(pattern, flat, re.I)
        if not match:
            continue
        value = _parse_size_token(match.group(1))
        if value is None:
            try:
                value = float(match.group(1).replace(",", "."))
            except ValueError:
                continue
        token = match.group(0).lower()
        if "mm" in token and value > 45:
            value = round(value / 10, 1)
        if 10 <= value <= 45 and value not in SUSPICIOUS_SIZES:
            return value
    return None


def extract_text_height_cm(plain: str) -> float | None:
    if not plain:
        return None

    machine = re.search(r"Machine\s+Size:\s*(\d+)\s*mm", plain, re.I)
    if machine:
        return round(float(machine.group(1)) / 10, 1)

    for pattern in (
        r"(\d{1,2}(?:\.\d+)?)\s*cm\s+action figure",
        r"Height[:\s]+(\d+(?:\.\d+)?)\s*cm",
        r"Size:\s*(\d+(?:\.\d+)?)\s*cm",
    ):
        match = re.search(pattern, plain, re.I)
        if match:
            value = _parse_size_token(match.group(1)) or float(match.group(1))
            if 10 <= value <= 45:
                return value
    return None


def resolve_display_height_cm(product: dict, parsed_size_cm: float | None = None) -> float | None:
    """Best single marketing height for display (uses cached OCR result when present)."""
    cached = product.get("marketing_size_cm")
    if cached is not None:
        try:
            value = float(cached)
            if 10 <= value <= 45 and value not in SUSPICIOUS_SIZES:
                return value
        except (TypeError, ValueError):
            pass

    text_height = extract_text_height_cm(product.get("description_text") or "")
    if text_height is not None:
        return text_height

    if parsed_size_cm is not None and 10 <= parsed_size_cm <= 45:
        return parsed_size_cm
    return None
