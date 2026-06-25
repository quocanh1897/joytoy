# JoyToy — Agent Rules

Project-specific instructions for AI agents working in this repository.

## Primary deliverable: portable all-in-one HTML

The shipped artifact is a **single HTML file** that works offline and opens on any device (desktop, tablet, phone) without a server or sibling asset folders.

### Requirements

- Build **`warhammer-catalog/catalog.html`** in **standalone** mode (default). Do **not** treat `catalog-linked.html` as the final deliverable.
- Run the catalog builder without `--linked`:

  ```bash
  cd warhammer-catalog
  python build_catalog.py
  ```

- Standalone output must:
  - Embed product JSON in the page (no external API).
  - Inline images as WebP data URIs (via `build_catalog.py` + Pillow), not relative paths to `warhammer-scraper/data/images/`.
  - Remain self-contained: one file can be copied, emailed, or opened via `file://` on another machine.

### When changing the UI or data pipeline

1. Edit source (`catalog.template.html`, `build_catalog.py`, scraper data, or `warhammer-catalog/stock_data.json`).
2. Rebuild standalone `catalog.html`.
3. Confirm file size is reasonable; use `--image-scope thumb` only if the user accepts smaller previews—not linked mode.

### Avoid

- Shipping `catalog-linked.html` as the main result.
- Relying on external CDNs or runtime fetches for core catalog content.
- Splitting required assets across multiple files for the primary catalog.

---

## Verify every change with Playwright

After **any** code or catalog change, validate the standalone HTML in a real browser using **Playwright** (Cursor Playwright MCP or `npx playwright`).

### Rebuild first

```bash
cd warhammer-catalog && python build_catalog.py
```

### Browser checks (minimum)

Open the standalone catalog via absolute `file://` URL, e.g.:

`file:///Users/<you>/Documents/mine/joytoy/warhammer-catalog/catalog.html`

Using Playwright MCP, verify:

1. **Load** — Page renders without console errors; hero and product grid appear.
2. **Search** — Type in the search box; product count updates and results filter.
3. **Category** — Click a sidebar faction; correct section scrolls/filters.
4. **Product detail** — Open a product card/modal; images and metadata display (not broken `img` icons).
5. **Language** — Toggle EN/VI if present; labels switch without layout break.
6. **Mobile** — Resize viewport (~390×844); layout remains usable (sticky bar, grid, sidebar).

Capture a snapshot or screenshot if something fails; fix before committing.

### Playwright MCP workflow (Cursor)

```
browser_navigate → file://.../warhammer-catalog/catalog.html
browser_snapshot → confirm structure
browser_click / browser_type → exercise search, categories, modal
browser_resize → mobile viewport, snapshot again
browser_console_messages → level error (no new errors)
```

Do not mark work complete until Playwright verification passes.

---

## Commit and push after every change

This repo requires a **commit and push** at the end of each task, including small fixes.

### Workflow

1. Finish the change and rebuild `catalog.html` if the catalog pipeline was touched.
2. Run Playwright verification (above).
3. Stage relevant files (include regenerated `catalog.html` when applicable).
4. Commit with a clear message (what changed and why).
5. Push to `origin` on the current branch.

```bash
git status
git add <files>
git commit -m "$(cat <<'EOF'
Short imperative summary.

Optional one-line context.
EOF
)"
git push
```

### Notes

- Do not skip push unless the user explicitly says not to push (e.g. WIP on a private branch).
- Never force-push `main`.
- Large `catalog.html` is tracked with Git LFS; ensure LFS objects are pushed.
- Do not commit secrets (`.env`, credentials).

---

## Project context (quick reference)

| Path | Role |
|------|------|
| `warhammer-scraper/` | Scrape JoyToy.com → `data/products.json` + images |
| `warhammer-catalog/build_catalog.py` | Merge scraper + stock → standalone HTML |
| `warhammer-catalog/catalog.template.html` | Catalog UI shell |
| `warhammer-catalog/catalog.html` | **Primary deliverable** (standalone) |
| `warhammer-catalog/stock_data.json` | Local VND shop inventory (optional merge) |
| `warhammer-catalog/import_stock.py` | Import `Discount.csv` into stock data |

Tech: Python 3, requests, BeautifulSoup, Pillow; static HTML/CSS/vanilla JS.

See root `README.md` for architecture and setup.
