# Warhammer Action Figure Scraper

Scrapes all products from [JoyToy Warhammer Action Figures](https://joytoy.com/collections/warhammer-action-figure), including images, specs, and pricing.

## Setup

```bash
cd warhammer-scraper
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

Scrape everything (products JSON + images):

```bash
python scrape.py
```

Options:

```bash
python scrape.py --limit 5          # test on first 5 products
python scrape.py --no-images        # metadata only
python scrape.py --resume           # skip already-scraped products (default)
python scrape.py --delay 1.5        # seconds between requests (default: 1.0)
```

## Output

```
data/
  products.json       # all product metadata
  images/
    {product-slug}/
      001.jpg         # gallery images
      002.jpg
      description/
        001.jpg       # description/marketing images
        002.jpg
```

Each product entry includes:

- `name`, `slug`, `url`, `sku`
- `price_usd`, `price_currency`, `availability`
- `size_cm`, `height_inches`, `product_dimensions_cm`, `package_size_cm`, `package_weight_kg`
- `scale`, `material`, `applicable_age`
- `description_text`, `description_html`
- `images` (product gallery) and `description_images` (detail/marketing photos)
- `local_images` and `local_description_images` (paths after download)

The collection currently has **541 products** across 17 pages.
