export interface LegionTheme {
  base: string;
  glow: string;
  grid: string;
  ink: string;
  inkSoft: string;
  panel: string;
  line: string;
  lineBright: string;
  accent: string;
  accentBright: string;
  highlight: string;
  header: string;
}

export const DEFAULT_LEGION_THEME: LegionTheme = {
  base: "#090a08",
  glow: "rgb(185 154 80 / 38%)",
  grid: "rgb(222 212 186 / 10%)",
  ink: "#12130f",
  inkSoft: "#191a15",
  panel: "#20211b",
  line: "#3e4035",
  lineBright: "#5b594a",
  accent: "#b99a50",
  accentBright: "#e0c477",
  highlight: "rgb(185 154 80 / 28%)",
  header: "rgb(18 19 15 / 97%)",
};

type LegionDef = { h: number; s: number; l: number } | "neutral" | "default";

/** Hue/sat/light presets — expanded into full surface palettes at build time. */
export const LEGION_DEFS: Record<string, LegionDef> = {
  primarch: { h: 42, s: 72, l: 54 },
  "adepta-sororitas": { h: 0, s: 76, l: 46 },
  "adeptus-custodes": { h: 44, s: 82, l: 54 },
  "adeptus-mechanicus": { h: 24, s: 68, l: 46 },
  "age-of-sigmar": { h: 198, s: 58, l: 50 },
  "alpha-legion": { h: 172, s: 58, l: 44 },
  "astra-militarum": { h: 54, s: 38, l: 44 },
  "black-legion": { h: 288, s: 52, l: 42 },
  "black-templars": "neutral",
  "blood-angels": { h: 0, s: 74, l: 46 },
  "chaos-space-marines": { h: 348, s: 62, l: 42 },
  "dark-angels": { h: 138, s: 48, l: 40 },
  "death-guard": { h: 78, s: 38, l: 42 },
  "grey-knights": { h: 212, s: 28, l: 56 },
  "imperial-fists": { h: 46, s: 88, l: 52 },
  "imperial-knights": { h: 218, s: 52, l: 50 },
  "iron-hands": { h: 210, s: 10, l: 52 },
  "iron-warriors": { h: 220, s: 8, l: 48 },
  "night-lords": { h: 248, s: 58, l: 44 },
  "legio-custodes": { h: 44, s: 82, l: 54 },
  necrons: { h: 128, s: 62, l: 46 },
  "ork-kommandos": { h: 118, s: 58, l: 40 },
  "raven-guard": { h: 220, s: 18, l: 46 },
  salamanders: { h: 136, s: 52, l: 40 },
  "sisters-of-silence": { h: 228, s: 12, l: 58 },
  "sons-of-horus": { h: 158, s: 48, l: 42 },
  "space-marine-ii": { h: 220, s: 58, l: 50 },
  "space-wolves": { h: 208, s: 36, l: 54 },
  "tau-empire": { h: 168, s: 32, l: 42 },
  "thousand-sons": { h: 268, s: 58, l: 52 },
  tyranids: { h: 282, s: 52, l: 44 },
  ultramarines: { h: 220, s: 72, l: 50 },
  "white-consuls": { h: 218, s: 42, l: 58 },
  "white-scars": { h: 4, s: 68, l: 50 },
  "world-eaters": { h: 0, s: 78, l: 44 },
  other: "default",
};

function buildFromHue(h: number, s: number, accentL: number): LegionTheme {
  const inkS = Math.max(18, Math.round(s * 0.42));
  const softS = Math.max(16, Math.round(s * 0.38));
  const panelS = Math.max(14, Math.round(s * 0.34));
  return {
    base: `hsl(${h} ${inkS}% 5%)`,
    glow: `hsl(${h} ${s}% 52% / 48%)`,
    grid: `hsl(${h} ${s}% 58% / 16%)`,
    ink: `hsl(${h} ${inkS}% 9%)`,
    inkSoft: `hsl(${h} ${softS}% 12%)`,
    panel: `hsl(${h} ${panelS}% 16%)`,
    line: `hsl(${h} ${Math.max(12, Math.round(s * 0.28))}% 28%)`,
    lineBright: `hsl(${h} ${Math.max(14, Math.round(s * 0.32))}% 42%)`,
    accent: `hsl(${h} ${s}% ${accentL}%)`,
    accentBright: `hsl(${h} ${Math.min(s + 12, 94)}% ${Math.min(accentL + 20, 82)}%)`,
    highlight: `hsl(${h} ${s}% ${Math.max(accentL - 2, 38)}% / 34%)`,
    header: `hsl(${h} ${softS}% 9% / 97%)`,
  };
}

function buildNeutralTheme(): LegionTheme {
  return {
    base: "#050505",
    glow: "rgb(210 210 210 / 18%)",
    grid: "rgb(230 230 230 / 6%)",
    ink: "#0c0c0c",
    inkSoft: "#121212",
    panel: "#181818",
    line: "#2e2e2e",
    lineBright: "#454545",
    accent: "#d8d8d8",
    accentBright: "#f2f2f2",
    highlight: "rgb(230 230 230 / 14%)",
    header: "rgb(10 10 10 / 96%)",
  };
}

function expandLegionDef(def: LegionDef): LegionTheme {
  if (def === "default") return DEFAULT_LEGION_THEME;
  if (def === "neutral") return buildNeutralTheme();
  return buildFromHue(def.h, def.s, def.l);
}

export const LEGION_THEMES: Record<string, LegionTheme> = Object.fromEntries(
  Object.entries(LEGION_DEFS).map(([id, def]) => [id, expandLegionDef(def)]),
);

function themeVars(theme: LegionTheme): string {
  return `--legion-base: ${theme.base};
  --legion-glow: ${theme.glow};
  --legion-grid: ${theme.grid};
  --ink: ${theme.ink};
  --ink-soft: ${theme.inkSoft};
  --panel: ${theme.panel};
  --line: ${theme.line};
  --line-bright: ${theme.lineBright};
  --brass: ${theme.accent};
  --brass-bright: ${theme.accentBright};
  --legion-highlight: ${theme.highlight};
  --legion-header: ${theme.header};`;
}

export function buildLegionThemeCss(): string {
  const themeBlock = (selector: string, theme: LegionTheme) => `${selector} {\n  ${themeVars(theme)}\n}`;

  const defaultBlock = themeBlock(":root", DEFAULT_LEGION_THEME);
  const categoryBlocks = Object.entries(LEGION_THEMES).map(([id, theme]) =>
    themeBlock(`html[data-catalog-category="${id}"]`, theme),
  );

  return `${defaultBlock}
${categoryBlocks.join("\n")}
html[data-catalog-category=""],
html[data-catalog-category="latest"] {
  ${themeVars(DEFAULT_LEGION_THEME)}
}
html,
body,
.page-frame,
.site-header,
.hero,
.catalog-sidebar,
.product-card,
.record-panel,
.gallery-stage,
.search-field input,
.select-field select,
.language-toggle,
.load-more,
.primary-action,
.secondary-action {
  transition:
    background-color 420ms ease,
    background 420ms ease,
    border-color 420ms ease,
    color 420ms ease,
    box-shadow 420ms ease;
}

@media (prefers-reduced-motion: reduce) {
  html,
  body,
  .page-frame,
  .site-header,
  .hero,
  .catalog-sidebar,
  .product-card,
  .record-panel,
  .gallery-stage,
  .search-field input,
  .select-field select,
  .language-toggle,
  .load-more,
  .primary-action,
  .secondary-action {
    transition: none;
  }
}`;
}

export function themeForCategory(categoryId: string): LegionTheme {
  return LEGION_THEMES[categoryId] ?? DEFAULT_LEGION_THEME;
}
