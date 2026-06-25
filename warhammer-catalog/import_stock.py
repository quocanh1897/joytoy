#!/usr/bin/env python3
"""Import JoyToy shop stock from Discount.csv into stock_data.json."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_CSV = Path.home() / "Downloads" / "Discount.csv"
OUTPUT = ROOT / "stock_data.json"


def upc_from_sku(sku: str) -> str:
    return f"697313037{sku[2:].strip()}"


def parse_vnd_price(raw: str) -> str:
    s = raw.strip().replace(" ", "")
    if not s:
        return ""
    if s.count(".") >= 2:
        return s
    if "," in s:
        return str(int(s.replace(",", "")) // 1000)
    val = int(s.replace(".", ""))
    if val >= 1_000_000:
        m, rest = divmod(val, 1_000_000)
        t, u = divmod(rest, 1000)
        return f"{m}.{t:03d}.{u:03d}"
    return str(val // 1000)


def import_discount_csv(path: Path) -> list[dict]:
    lines = path.read_text(encoding="utf-8-sig").strip().splitlines()
    rows: list[dict] = []
    for line in lines[1:]:
        if not line.strip():
            continue
        parts = line.split(";")
        if len(parts) < 7 or not parts[1].strip():
            continue
        sku = parts[1].strip()
        rows.append(
            {
                "stt": int(parts[0]),
                "sku": sku,
                "upc": upc_from_sku(sku),
                "name": parts[3].strip(),
                "qty": int(parts[4]),
                "price": parse_vnd_price(parts[5]),
                "deposit": parse_vnd_price(parts[6]),
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", nargs="?", default=str(DEFAULT_CSV), help="Path to Discount.csv")
    parser.add_argument("-o", "--output", default=str(OUTPUT))
    args = parser.parse_args()

    csv_path = Path(args.csv).expanduser()
    if not csv_path.exists():
        raise SystemExit(f"CSV not found: {csv_path}")

    rows = import_discount_csv(csv_path)
    output = Path(args.output)
    output.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(rows)} stock rows to {output}")


if __name__ == "__main__":
    main()
