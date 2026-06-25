# Agent instructions

AI agents (Cursor, Claude Code, Codex, etc.) working in this repo should follow the project rules in:

**[`.claude/CLAUDE.md`](.claude/CLAUDE.md)**

Read that file before making changes. Summary of non-negotiable rules:

## 1. Deliverable: all-in-one HTML

The end product is **`warhammer-catalog/catalog.html`** in **standalone** mode—a single file with embedded JSON and inlined WebP images so it opens offline on any device. Rebuild with:

```bash
cd warhammer-catalog && python build_catalog.py
```

Do not ship `catalog-linked.html` as the primary result.

## 2. Verify with Playwright

After every change, open the rebuilt `catalog.html` via `file://` in Playwright and check load, search, categories, product detail, language toggle, and mobile layout. Fix failures before finishing.

## 3. Commit and push

After verification, **commit and push** every change to `origin` unless the user explicitly asks not to.

---

Full workflow, checklists, and paths: [`.claude/CLAUDE.md`](.claude/CLAUDE.md)

Project overview: [`README.md`](README.md)
