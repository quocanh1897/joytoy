# Restructure the JoyToy Catalog Site

**Status:** Implemented locally; Cloudflare owner setup and production cutover remain

**Prepared:** 2026-08-18

**Target:** Astro + TypeScript deployed as static assets on Cloudflare Pages at `https://joytoy.binscode.site`

**Cost constraint:** Required solution must remain **USD $0**. Stop implementation before enabling any paid product or entering a paid commitment.

## Implementation checkpoint — 2026-08-18

The repository implementation is complete and verified locally. No paid service, payment method, metered runtime, or Cloudflare resource was enabled.

Implemented:

- Static Astro 7 + strict TypeScript application in `web/`, with no Cloudflare adapter and no server runtime.
- 541 static product routes plus the catalog and 404 routes.
- Compact catalog JSON, URL-synchronized search/filter/sort controls, English/Vietnamese copy, local-stock filtering, incremental rendering, and product galleries.
- Deterministic build-time WebP conversion from the existing local source images.
- Unit, data-contract, desktop, and mobile browser tests.
- Free-tier output verifier and a conditional Cloudflare Pages Direct Upload workflow.
- The existing GitHub Pages workflow and standalone offline catalog remain intact for rollback.

Measured production-build results:

| Check | Result |
|---|---:|
| Products / categories | 541 / 36 |
| Static pages | 543 |
| Generated WebP assets | 6,774 |
| Total deployment files | 7,324 of the 18,999 internal maximum |
| Total deployment size | 240.7 MiB |
| Largest file | 301.7 KiB |
| Homepage HTML, gzip | 5.8 KiB |
| Catalog index, gzip | 28.3 KiB |
| All JavaScript, gzip | 3.0 KiB |
| Missing generated images | 0 |
| Astro diagnostics | 0 errors, warnings, or hints |
| Unit/data tests | 5 passed |
| Browser tests | 7 passed, 1 intentional project skip |
| Throttled local desktop LCP / CLS | approximately 600 ms / 0 |
| Throttled local mobile LCP / CLS | approximately 560 ms / 0 |

The lab render timings use a local server with a simulated 4G connection, so they are directional rather than a promise of production latency. They are well below the 2.5-second release budget and must be remeasured on the deployed `pages.dev` preview.

Current free-tier terms were revalidated against official documentation on 2026-08-18: Pages Free permits 20,000 files, a 25 MiB maximum file, 100 custom domains per project, and static asset requests are free and unlimited. The repository is public, so its standard `ubuntu-latest` GitHub Actions runner is free. The build stays below the deliberately stricter internal thresholds.

Owner checkpoint before this plan can be marked complete:

1. Create the free Direct Upload project `joytoy-catalog` using Section 10.B.
2. Add only the two repository secrets in Sections 10.C–E.
3. Push the implementation and verify the `pages.dev` deployment.
4. Attach `joytoy.binscode.site` using Section 10.H and run the production checks.
5. Keep the old GitHub Pages deployment during acceptance; disable it only after approval.

These steps require the owner's authenticated Cloudflare and GitHub access and are intentionally not automated from a local development session.

## 1. Decision and cost answer

This plan is viable as a free implementation.

The required production architecture will use only:

- A free Cloudflare account.
- Cloudflare Pages static asset hosting.
- The existing `binscode.site` domain, using the exact hostname `joytoy.binscode.site`.
- The free `https://<project>.pages.dev` hostname as a deployment fallback.
- Astro's static output mode, with no server adapter.
- TypeScript running in the browser only where interaction is required.
- Standard GitHub Actions runners while this repository remains public.
- Build-time image conversion using the existing local image files and open-source tooling.

Cloudflare states that static asset requests are free and unlimited on both free and paid Pages plans. The current Pages Free limits relevant to this project are 20,000 files per site, 25 MiB per file, 500 builds per month, and a 20-minute Cloudflare build timeout. This plan uses Direct Upload from GitHub Actions, so Cloudflare will host only prebuilt static files and will not execute a Pages Function.

### Required services and expected price

| Component | Required? | Planned tier | Expected cost |
|---|---:|---|---:|
| Astro and TypeScript | Yes | Open source | $0 |
| Cloudflare Pages static assets | Yes | Free | $0 |
| `*.pages.dev` fallback hostname and TLS | Yes | Included | $0 |
| GitHub Actions | Yes | Standard runner, public repository | $0 |
| `joytoy.binscode.site` | Yes | Existing owner-provided domain | $0 incremental cost |
| Cloudflare Images | No | Explicitly excluded | $0 |
| Cloudflare R2 | No | Explicitly excluded | $0 |
| Pages Functions / Workers | No | Explicitly excluded | $0 |
| D1, KV, database, authentication | No | Explicitly excluded | $0 |
| Analytics or monitoring SaaS | No | Optional only if free | $0 |

### Why Cloudflare Images is excluded

The catalog currently has roughly 6,242 description images. Cloudflare Images currently includes 5,000 unique transformations per month on its free plan. That allowance is too close to or below this catalog's needs once more than one image size is generated. The free plan would stop returning new transformations after the allowance is exceeded. Therefore, transformations will happen during the build, and Pages will serve the resulting WebP files as normal static assets.

### Absolute stop conditions

Stop implementation and ask the owner before proceeding if any of these becomes true:

1. Cloudflare requires selecting a paid Pages, Workers, Images, R2, or domain plan.
2. The Cloudflare setup requires adding a paid subscription to deploy static assets.
3. The generated site exceeds 19,000 files. The official hard limit is 20,000; 19,000 is the safety threshold.
4. Any generated file exceeds 24 MiB. The official hard limit is 25 MiB; 24 MiB is the safety threshold.
5. A required feature cannot be implemented without Pages Functions, Workers, R2, Images, D1, KV, or another metered service.
6. The repository becomes private and its GitHub Actions use would exceed the owner's included free allowance. Configure the GitHub Actions spending budget to stop usage rather than permit charges.
7. Connecting the already-owned `joytoy.binscode.site` hostname requires purchasing a new domain, certificate, DNS product, or paid Cloudflare feature. The `*.pages.dev` hostname remains the no-cost fallback.
8. Cloudflare or GitHub changes its free-tier terms before deployment such that this design would incur a charge.

Do not “temporarily” activate a paid product to get past a blocker. Report the blocker and stop.

## 2. Current baseline

The existing data and scraper pipeline should be retained. The slow website is caused by its generated delivery artifact, not by the scraper.

Current measured baseline:

- 541 products.
- Approximately 6,242 product-description/gallery images.
- 10,405 local source image files in the scraper tree.
- `warhammer-catalog/catalog.html`: 182,407,343 bytes raw.
- Deployed transfer: approximately 137.8 MB with gzip.
- Catalog usable after approximately 44.4 seconds in desktop Chrome during the investigation.
- Approximately 252 MB of JavaScript heap after startup.
- The boot script is located after the embedded image blobs at approximately 99.82% of the HTML file.

The implementation should preserve:

- `warhammer-scraper/` and its scraping/enrichment behavior.
- `warhammer-scraper/data/products.json` as the source catalog.
- Local stock matching and `warhammer-catalog/stock_data.json`.
- Category mapping and bilingual labels.
- The current standalone `warhammer-catalog/catalog.html` as an explicitly downloadable offline artifact.

The new online website must not embed base64 product images in HTML or JSON.

## 3. Target architecture

```text
JoyToy source pages
        |
        v
Existing Python scraper and stock matcher
        |
        +-- products.json
        +-- stock_data.json
        +-- local source images
        |
        v
Web preparation script
        |
        +-- compact catalog index
        +-- product detail records
        +-- WebP card thumbnails
        +-- WebP gallery images
        |
        v
Astro static build
        |
        +-- static HTML routes
        +-- small CSS and TypeScript bundles
        +-- static JSON and image assets
        |
        v
GitHub Actions verification and Direct Upload
        |
        v
Cloudflare Pages CDN
        |
        +-- joytoy.binscode.site (production)
        +-- *.pages.dev (fallback/preview)
```

### Rendering model

- Astro produces static HTML at build time.
- Do not install `@astrojs/cloudflare`; a Cloudflare adapter is unnecessary for static Astro output.
- The initial route contains useful content before JavaScript runs.
- TypeScript handles search, filters, sorting, language state, “load more,” and gallery interaction.
- Product detail pages are statically generated at `/products/<slug>/`.
- Images are ordinary URLs and use native lazy loading and asynchronous decoding.
- Full gallery assets are discovered and downloaded only on a product detail page or when its modal is opened.
- No runtime API, database, server-side render, edge function, or client-side request for all image bytes.

## 4. Proposed repository structure

```text
joytoy/
├── web/
│   ├── astro.config.mjs
│   ├── package.json
│   ├── package-lock.json
│   ├── tsconfig.json
│   ├── public/
│   │   ├── _headers
│   │   ├── favicon.svg
│   │   ├── data/
│   │   │   └── catalog-index.json
│   │   └── media/                 # generated during CI; not base64
│   │       ├── thumbs/
│   │       └── gallery/
│   ├── scripts/
│   │   ├── prepare-catalog.mjs
│   │   ├── prepare-images.py
│   │   ├── validate-data.mjs
│   │   └── verify-free-limits.mjs
│   ├── src/
│   │   ├── components/
│   │   ├── layouts/
│   │   ├── pages/
│   │   │   ├── index.astro
│   │   │   ├── 404.astro
│   │   │   └── products/[slug].astro
│   │   ├── scripts/
│   │   ├── styles/
│   │   ├── types/
│   │   └── data/                  # compact generated build inputs
│   └── tests/
├── warhammer-catalog/             # existing offline build remains
├── warhammer-scraper/             # existing source pipeline remains
└── .github/workflows/
    └── cloudflare-pages.yml
```

Generated `web/dist/` must not be committed. The plan should decide during implementation whether generated WebP media is cached between CI builds. Do not upload a GitHub Actions artifact solely for storage; Wrangler should deploy `web/dist` directly.

## 5. Data contract

Create a typed web-specific data model instead of sending the scraper's complete raw records to every visitor.

### Catalog index record

The index requires only fields used by cards, search, filtering, and sorting:

```ts
export interface CatalogProductSummary {
  slug: string;
  name: string;
  upc?: string;
  categoryId: string;
  categoryEn: string;
  categoryVi: string;
  availability?: "InStock" | "PreOrder" | "OutOfStock" | "SoldOut";
  priceUsd?: number;
  sizeCm?: number;
  thumbnail: {
    src: string;
    width: number;
    height: number;
  };
  stock?: {
    sku?: string;
    qty?: number;
    priceVnd?: string;
    deposit?: string;
  };
}
```

### Product detail record

Product detail HTML can contain the selected product's additional fields:

- JoyToy product URL.
- Box contents.
- Material and scale.
- Availability and prices.
- Gallery image URLs and dimensions.
- Local stock information.

Do not include every product's gallery array in the homepage index. This keeps parsing and memory proportional to visible catalog metadata rather than all media.

### Data validation

The build must fail when:

- Slugs are empty or duplicated.
- Required names or categories are missing.
- A referenced local image does not exist.
- Generated image dimensions are invalid.
- A URL uses an unsafe scheme.
- A product route collides with a reserved route.
- JSON contains unexpected executable HTML in fields rendered without escaping.

## 6. Image strategy within the free Pages limits

Only images referenced by the online product model should enter `dist`; do not copy all 10,405 scraper files blindly.

Initial planned derivative set:

| Use | Count estimate | Output | Target |
|---|---:|---|---|
| Card thumbnail | Up to 541 | WebP, max 360×360 | Prefer ≤60 KB each |
| Gallery/detail | Approximately 6,242 | WebP, max 960 px longest edge | Prefer ≤180 KB each |
| Product HTML pages | Up to 541 | HTML | Prefer ≤50 KB each |
| App/data/support files | Under 200 | HTML/CSS/JS/JSON | Budgeted below |

Estimated output count is approximately 7,500 files, comfortably below the 19,000 internal stop threshold. The implementation must calculate the exact count rather than trust this estimate.

Image preparation requirements:

1. Select only the first valid description image as the card thumbnail.
2. Select only deduplicated description/gallery images for product details.
3. Normalize EXIF orientation.
4. Preserve aspect ratio.
5. Emit WebP with explicit width and height metadata.
6. Strip unnecessary metadata.
7. Use deterministic output paths, for example `<slug>/<content-hash>.webp`.
8. Reuse a generated file when multiple products reference identical source content.
9. Generate into a clean directory to prevent stale files from surviving.
10. Never inline the generated bytes as base64.
11. Add `loading="lazy"` and `decoding="async"` to noncritical images.
12. Mark only the actual above-the-fold LCP image, if any, as eager/high priority.

If the gallery derivative count or total build size proves operationally unsuitable for Pages, reduce online galleries to a deliberately selected subset per product. Do not switch to a paid image service without explicit approval.

## 7. UI and UX implementation

### Home/catalog page

- Render the header, statistics, categories, and first 24–48 cards as static HTML.
- Keep the current English/Vietnamese language feature.
- Make search available after a small TypeScript module loads.
- Debounce input by approximately 100–150 ms.
- Normalize searchable text once rather than on every keystroke.
- Store filters in URL query parameters so results are shareable and survive refresh.
- Render results in pages or batches instead of rebuilding all 541 cards.
- Use one delegated click handler for the catalog instead of one listener per card.
- Preserve visible image aspect ratios to prevent layout shift.
- Provide meaningful empty, loading, and error states.
- Support keyboard navigation and visible focus states.

### Product detail page

- Generate one static route per product.
- Put name, price, stock, availability, and the first image in initial HTML.
- Load gallery thumbnails and noncurrent large images lazily.
- Preserve previous/next navigation.
- Make the product URL directly shareable.
- Include a link to the original JoyToy product.
- Add basic title, description, canonical URL, and social metadata.

### Offline catalog

- Keep the standalone builder as a separate deliverable.
- Do not deploy the 182 MB standalone file as the Cloudflare homepage.
- Offer it only as an explicit download if it remains within Cloudflare's 25 MiB per-file limit; the current file does not.
- Because the current standalone file is larger than 25 MiB, initially link to its GitHub Release/LFS location or omit the download from Pages. Do not enable paid storage to host it.

## 8. Performance budgets

Treat these as release gates:

| Metric | Target |
|---|---:|
| Initial compressed HTML | ≤150 KB |
| Initial route JavaScript | ≤80 KB compressed |
| Compact catalog index | ≤300 KB compressed |
| Initial page transfer on desktop | ≤1.5 MB |
| Initial image requests | Only above-fold cards plus browser preload decisions |
| LCP, mobile lab test | ≤2.5 seconds |
| INP or interaction latency | ≤200 ms |
| CLS | ≤0.1 |
| Search update for 541 records | ≤100 ms on test hardware |
| Output files | <19,000 |
| Largest output file | <24 MiB |

Also compare against the recorded current baseline. The desired practical result is useful catalog content in approximately 1–2.5 seconds instead of approximately 44 seconds on a comparable connection.

## 9. Detailed implementation phases

### Phase 0 — Revalidate the free approach

1. Confirm Cloudflare Pages Free still offers static hosting, a `pages.dev` URL, and custom subdomains at no additional charge.
2. Confirm the limits listed in Section 1 against current official documentation.
3. Confirm this GitHub repository is public before relying on unlimited free standard-runner Actions usage.
4. Confirm no paid Cloudflare subscription is active or required.
5. Confirm `binscode.site` is still owned and determine whether its DNS is managed by Cloudflare or another provider.
6. Confirm the intended production hostname is exactly `joytoy.binscode.site`. Cloudflare Pages does not support attaching `*.binscode.site` itself as a wildcard Pages custom domain.
7. Calculate the exact set of referenced online gallery images.
8. Estimate generated file count, maximum file size, and output size.
9. Record the audit in the implementation PR or commit message.
10. Apply every stop condition before writing deployment credentials.

Acceptance: all required components have a verified $0 path and projected output is under internal safety limits.

### Phase 1 — Scaffold the Astro application

1. Create `web/` using the current stable Astro release.
2. Enable strict TypeScript.
3. Keep Astro's default static output.
4. Do not install the Cloudflare server adapter.
5. Pin Node using `web/.node-version` and `package.json` engines.
6. Commit `package-lock.json` and use `npm ci` in CI.
7. Add scripts for development, type checking, data preparation, build, tests, and limit verification.
8. Add a minimal static index and 404 page.

Suggested scripts:

```json
{
  "scripts": {
    "dev": "astro dev",
    "prepare:data": "node scripts/prepare-catalog.mjs",
    "prepare:images": "python3 scripts/prepare-images.py",
    "check": "astro check && node scripts/validate-data.mjs",
    "build": "npm run prepare:data && npm run prepare:images && astro build && npm run verify:limits",
    "verify:limits": "node scripts/verify-free-limits.mjs",
    "test:e2e": "playwright test"
  }
}
```

Acceptance: `npm ci`, `npm run check`, and a minimal `npm run build` succeed locally.

### Phase 2 — Extract and validate web data

1. Reuse existing category detection, size resolution, and stock matching behavior.
2. Avoid maintaining two divergent copies of business rules; either invoke the Python builder helpers or extract shared helpers into a neutral Python module.
3. Generate the summary index and product detail inputs.
4. Escape user-facing data correctly.
5. Add deterministic snapshots/count assertions for 541 products and expected categories.
6. Add reports for unmatched stock without failing unrelated catalog generation.

Acceptance: generated web records match the existing catalog's names, categories, prices, stock, and sizes for a representative sample and all 541 products validate.

### Phase 3 — Build the image pipeline

1. Create an inventory of used source images.
2. Deduplicate by normalized source and/or content hash.
3. Generate thumbnail and gallery WebP derivatives.
4. Write dimensions into the product manifest.
5. Ensure clean builds remove stale derivatives.
6. Print build statistics: source count, deduplicated count, output count, bytes, largest file, missing images, and processing time.
7. Add the Cloudflare limit verifier.
8. Benchmark the full image build on a standard GitHub Actions runner.

Acceptance: no base64 media appears in HTML/JSON; every referenced image resolves; output remains under the free-plan stop thresholds.

### Phase 4 — Implement the static catalog UI

1. Port design tokens and useful visual styling from the current template.
2. Build semantic Astro components for header, controls, sidebar/categories, product cards, badges, and empty state.
3. Render an initial useful subset as static HTML.
4. Add TypeScript search, filters, sorting, language selection, and incremental result rendering.
5. Synchronize UI state with the URL.
6. Keep interaction code scoped to the catalog rather than hydrating the whole document.
7. Add responsive desktop, tablet, and mobile layouts.

Acceptance: the homepage works without JavaScript for browsing initial content and becomes fully searchable/filterable when its small script loads.

### Phase 5 — Implement product detail routes and gallery

1. Generate all product routes with Astro `getStaticPaths()`.
2. Render product information and first image in static HTML.
3. Lazy-load remaining gallery images.
4. Implement accessible modal/carousel behavior only if it materially improves the experience.
5. Add keyboard controls, focus management, close behavior, and reduced-motion handling.
6. Add metadata, canonical links, and structured product information where accurate.

Acceptance: every product route builds, has no broken media, is directly shareable, and does not download unrelated products' images.

### Phase 6 — Add tests and performance checks

1. Add unit tests for normalization, filtering, sorting, formatting, and image mapping.
2. Add data-contract validation.
3. Add Playwright desktop and 390×844 mobile tests.
4. Test language toggle, search, category filter, stock-only filter, sorting, product navigation, gallery, back navigation, and URL restoration.
5. Check keyboard-only operation and obvious accessibility issues.
6. Run Lighthouse or equivalent lab measurements against a production build served locally.
7. Fail CI on free-tier file limits and essential functional failures.
8. Initially report performance-budget failures; make them blocking after measurements stabilize.

Acceptance: functional checks pass and performance budgets are met or any exception is explicitly documented and approved.

### Phase 7 — Create Cloudflare Direct Upload deployment

Use Direct Upload rather than Cloudflare Git builds. This gives the image pipeline more build time on the existing public repository's free standard GitHub Actions runner and lets Cloudflare receive only the verified `dist` directory.

1. Build and verify `web/dist` in GitHub Actions.
2. Run the free-limit verifier before deployment.
3. Deploy only pushes to `main` as production.
4. Deploy pull requests or manually selected branches as Cloudflare preview branches when secrets are available and the PR is trusted.
5. Use minimal GitHub workflow permissions.
6. Never expose the Cloudflare API token in logs or pull-request jobs.
7. Do not upload `web/dist` as a long-lived GitHub artifact unless needed for debugging.

Acceptance: a preview deployment succeeds at a `pages.dev` URL and reports the expected production commit. The custom domain is not attached until this preview passes.

### Phase 8 — User acceptance and production cutover

1. Compare the preview with the old GitHub Pages site.
2. Run full desktop and mobile UAT.
3. Test from a cold browser cache and a throttled mobile profile.
4. Verify all 541 products and sample galleries across multiple categories.
5. Verify Cloudflare Analytics/usage shows static asset requests only and no Function invocations.
6. Deploy `main` to the production Pages project.
7. Attach and activate `joytoy.binscode.site` using the steps in Section 10.H.
8. Verify the custom hostname, TLS certificate, canonical URLs, product routes, and static assets.
9. Keep the GitHub Pages deployment available during a stabilization window.
10. After approval, disable the old GitHub Pages deployment workflow or replace its homepage with a small redirect/link to `https://joytoy.binscode.site`.
11. Do not delete the standalone catalog or scraper data.

Acceptance: the Cloudflare production site passes UAT and the old site can be retired without losing the offline artifact.

### Phase 9 — Ongoing maintenance

1. Rebuild the website after scraper or stock updates.
2. Keep dependency updates reviewed and locked.
3. Re-run the cost/limit audit before adding a major category or new image variant.
4. Monitor exact output file count and largest asset in every deployment.
5. Re-check Cloudflare and GitHub free-tier terms at least before major releases.
6. Maintain a rollback link to the preceding Cloudflare deployment.

## 10. Cloudflare Pages configuration — exact owner steps

These steps are intentionally separated because the repository owner must authenticate to Cloudflare and GitHub. Never paste an API token into a chat, commit, issue, or build log.

### A. Create or select a free Cloudflare account

1. Open the Cloudflare dashboard and create/sign into an account.
2. Stay on the Free plan.
3. Do not purchase a domain or add a payment plan, R2 subscription, Images subscription, Workers Paid plan, or other product. The existing `binscode.site` domain is sufficient.
4. Confirm the dashboard provides access to **Workers & Pages**.
5. If Cloudflare asks for a paid commitment for ordinary Pages static hosting, stop.

### B. Create the Direct Upload Pages project

The site will contain more than the dashboard drag-and-drop limit of 1,000 files, so use Wrangler rather than drag and drop.

1. Locally, build a verified `web/dist` first.
2. Run `npx wrangler login` and complete the browser authorization.
3. Run `npx wrangler pages project create`.
4. Choose a project name such as `joytoy-catalog`.
5. Set the production branch to `main` when prompted.
6. Confirm the assigned URL, such as `https://joytoy-catalog.pages.dev`.
7. Do not configure Functions or bindings.
8. Do not add R2, D1, KV, Images, Queues, or Workers.
9. Optionally make a first manual preview deployment:

```bash
npx wrangler pages deploy web/dist --project-name=joytoy-catalog --branch=preview
```

Do not make the first production deployment until tests and the free-limit verifier pass.

### C. Create a least-privilege Cloudflare API token

1. In the Cloudflare dashboard, open **My Profile → API Tokens**.
2. Select **Create Token**.
3. Under **Custom Token**, select **Get started**.
4. Name it `joytoy-github-pages-deploy`.
5. Add permission **Account → Cloudflare Pages → Edit**.
6. Restrict account resources to the intended Cloudflare account if the UI permits.
7. Select **Continue to summary**, review it, and create the token.
8. Copy it once into the GitHub secret in the next section.
9. Never store it in a local tracked `.env` file.

### D. Get the Cloudflare account ID

1. Open the Cloudflare dashboard account overview.
2. Find and copy the **Account ID**.
3. This identifier is not treated like a password, but keep deployment configuration scoped to the intended account.

### E. Add GitHub repository secrets

1. Open the GitHub repository.
2. Go to **Settings → Secrets and variables → Actions**.
3. Select **New repository secret**.
4. Add `CLOUDFLARE_ACCOUNT_ID` with the account ID.
5. Add `CLOUDFLARE_API_TOKEN` with the token value.
6. Confirm neither value appears in workflow YAML.
7. Configure the GitHub Actions spending budget to stop usage instead of allowing additional paid usage. The repository is expected to remain public and use only `ubuntu-latest`, which GitHub documents as free for public repositories.

### F. Add the deployment workflow

Create `.github/workflows/cloudflare-pages.yml` with these responsibilities:

1. Trigger pull-request verification without deployment credentials.
2. Trigger production deployment only on pushes to `main` and manual dispatch.
3. Use `actions/checkout` on a standard `ubuntu-latest` runner.
4. Install pinned Node and Python versions.
5. Install dependencies with `npm ci` and the existing Python requirements.
6. Run data preparation, image preparation, type checks, tests, Astro build, and free-limit verification.
7. Deploy using `cloudflare/wrangler-action` only after all checks pass.
8. Grant only `contents: read` and `deployments: write` where required.
9. Set a concurrency group to cancel obsolete production builds.
10. Use `web/dist` and the exact Pages project name.

Deployment command shape:

```yaml
- name: Deploy to Cloudflare Pages
  uses: cloudflare/wrangler-action@v3
  with:
    apiToken: ${{ secrets.CLOUDFLARE_API_TOKEN }}
    accountId: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
    command: pages deploy web/dist --project-name=joytoy-catalog --branch=main
    gitHubToken: ${{ secrets.GITHUB_TOKEN }}
```

Pin actions to reviewed versions or immutable commit SHAs during implementation.

### G. Verify the Pages project after deployment

1. Open **Workers & Pages → joytoy-catalog → Deployments**.
2. Confirm the production deployment is associated with `main`.
3. Open the `pages.dev` production URL before custom-domain activation.
4. Confirm TLS works without configuration.
5. Confirm no Pages Functions are deployed or invoked.
6. Check browser network requests: HTML, CSS, JavaScript, JSON, and WebP files should be separate.
7. Confirm the response is not the old 182 MB HTML document.
8. Test a preview branch URL before each risky release.

### H. Connect `joytoy.binscode.site`

The owner already has `*.binscode.site` available. Cloudflare Pages cannot attach a wildcard such as `*.binscode.site` directly; configure the exact production hostname `joytoy.binscode.site`. This has no incremental hosting charge. Existing domain-renewal costs are outside the website hosting architecture.

#### H.1 Configure Astro for the production origin

Set the canonical production origin in `web/astro.config.mjs`:

```js
import { defineConfig } from "astro/config";

export default defineConfig({
  site: "https://joytoy.binscode.site",
  output: "static",
});
```

Additional requirements:

1. Do not configure the old GitHub Pages `/joytoy/` base path.
2. Serve the new site from `/`.
3. Generate canonical and social URLs using `Astro.site`.
4. Use Astro-managed or root-relative asset paths.
5. Verify `/products/<slug>/` routes and direct refreshes under the custom origin.

#### H.2 If `binscode.site` DNS is managed by Cloudflare

After the first successful production deployment:

1. Open **Cloudflare Dashboard → Workers & Pages**.
2. Select the `joytoy-catalog` Pages project.
3. Open **Custom domains**.
4. Select **Set up a custom domain**.
5. Enter `joytoy.binscode.site` exactly, not `*.binscode.site`.
6. Select **Continue → Activate domain**.
7. Allow Cloudflare to create the DNS record automatically.
8. Verify the resulting record is equivalent to:

```text
Type:    CNAME
Name:    joytoy
Target:  joytoy-catalog.pages.dev
Proxy:   Proxied
```

9. Wait until the Pages custom-domain status becomes **Active**.
10. Confirm `https://joytoy.binscode.site` presents a valid automatically managed TLS certificate.

An existing wildcard DNS record for `*.binscode.site` does not need to be removed solely for this site. The explicit `joytoy` record should take precedence. Resolve any existing explicit `joytoy` A, AAAA, or CNAME conflict before activation.

#### H.3 If DNS is managed by another provider

1. First add `joytoy.binscode.site` in **Pages project → Custom domains**.
2. Only after Pages recognizes the hostname, open the external DNS provider.
3. Create:

```text
Type:    CNAME
Name:    joytoy
Target:  joytoy-catalog.pages.dev
TTL:     Auto or provider default
```

4. Return to Cloudflare Pages and wait for the custom-domain status to become **Active**.
5. Do not create only the DNS record without first associating the hostname with the Pages project; Cloudflare documents that this can result in a `522` response.
6. If certificate activation fails, inspect restrictive CAA records and allow a certificate authority supported by Cloudflare Pages. Do not buy a certificate.

#### H.4 Validate DNS, TLS, routing, and SEO

Run these checks after activation:

```bash
dig joytoy.binscode.site CNAME
curl -I https://joytoy.binscode.site/
curl -I https://joytoy.binscode.site/products/<known-slug>/
```

Then verify in a browser:

1. HTTPS is valid with no certificate warning.
2. `/`, product routes, CSS, JavaScript, JSON, and WebP assets return successfully.
3. HTML canonical URLs use `https://joytoy.binscode.site`.
4. No asset URL contains the obsolete `/joytoy/` base path.
5. Search and product navigation work after a direct page refresh.
6. The `pages.dev` hostname either remains a fallback marked `noindex` or redirects to the custom hostname using a free Cloudflare redirect feature.
7. The old GitHub Pages URL points users to the new custom hostname after the stabilization period.

#### H.5 Cost policy

- Attaching the already-owned subdomain to Cloudflare Pages must cost $0.
- Cloudflare-managed TLS must be used; do not purchase a certificate.
- Do not purchase another domain.
- Do not enable a paid Cloudflare plan to attach the hostname.
- If custom-domain activation requires payment, stop and continue using `joytoy-catalog.pages.dev` while reporting the blocker.

## 11. Automated free-tier verifier

`verify-free-limits.mjs` must recursively inspect `web/dist` and fail with a clear report when:

- File count is 19,000 or higher.
- Any file is 24 MiB or larger.
- An HTML or JSON file contains a product `data:image/` URI.
- `_worker.js` or a `functions/` output is present.
- Unexpected server manifests or Cloudflare Function bundles are present.
- Initial HTML, JavaScript, or catalog-index budgets are exceeded.

It should print:

- Total files.
- Total bytes.
- Largest ten files.
- Count and bytes by extension.
- Number and total bytes of thumbnails and gallery images.
- HTML, JavaScript, CSS, and JSON totals.
- Explicit `FREE-TIER CHECK: PASS` or `FREE-TIER CHECK: FAIL`.

## 12. Rollback strategy

1. Do not immediately remove the current GitHub Pages deployment.
2. Cloudflare Pages retains prior deployments; use the dashboard rollback capability if a release fails.
3. Keep production deployments tied to commits so the previous good commit can be redeployed.
4. If Cloudflare's free terms become unsuitable, stop new deployments and continue serving the last valid static version while selecting another free static host.
5. The scraper and standalone catalog remain independent of the Cloudflare site, so the data pipeline is not lost during rollback.

## 13. Definition of done

The restructuring is complete only when:

- The required architecture costs $0.
- No paid or metered Cloudflare product is enabled.
- The site is served from `https://joytoy.binscode.site`, with `pages.dev` retained only as a fallback or redirected/noindexed origin.
- Useful catalog content appears without waiting for JavaScript or gallery downloads.
- Initial transfer and Core Web Vitals meet the agreed budgets.
- Search, categories, sorting, language, stock filtering, product details, and galleries pass desktop and mobile tests.
- All image bytes are separate static files, not base64 in HTML/JSON.
- Exact output stays below 19,000 files and 24 MiB per file.
- No Pages Function, Worker, database, object store, or image transformation service is required.
- The old GitHub Pages site remains available until owner acceptance.
- The offline standalone catalog remains buildable.
- Deployment and rollback instructions are documented and tested.

## 14. Official references to re-check before implementation

- [Cloudflare Pages limits](https://developers.cloudflare.com/pages/platform/limits/)
- [Cloudflare Pages pricing for static assets and Functions](https://developers.cloudflare.com/pages/functions/pricing/)
- [Cloudflare Pages Direct Upload](https://developers.cloudflare.com/pages/get-started/direct-upload/)
- [Direct Upload with GitHub Actions](https://developers.cloudflare.com/pages/how-to/use-direct-upload-with-continuous-integration/)
- [Cloudflare Pages custom domains](https://developers.cloudflare.com/pages/configuration/custom-domains/)
- [Cloudflare's Astro Pages guide](https://developers.cloudflare.com/pages/framework-guides/deploy-an-astro-site/)
- [Astro Cloudflare integration: static sites do not need an adapter](https://docs.astro.build/en/guides/integrations-guide/cloudflare/)
- [Astro islands architecture](https://docs.astro.build/en/concepts/islands/)
- [Astro image handling](https://docs.astro.build/en/guides/images/)
- [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions)

Free-tier limits and product terms can change. Phase 0 must use current official documentation rather than assuming the values recorded on 2026-08-18 remain permanent.
