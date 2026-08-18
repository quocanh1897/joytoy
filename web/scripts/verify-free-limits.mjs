#!/usr/bin/env node

import { gzipSync } from "node:zlib";
import { readdir, readFile, stat } from "node:fs/promises";
import { extname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("../dist/", import.meta.url));
const MAX_FILES = 19_000;
const MAX_FILE_BYTES = 24 * 1024 * 1024;
const INDEX_HTML_GZIP = 150 * 1024;
const INDEX_JSON_GZIP = 300 * 1024;
const JAVASCRIPT_GZIP = 80 * 1024;

async function walk(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const nested = await Promise.all(
    entries.map((entry) => {
      const path = join(directory, entry.name);
      return entry.isDirectory() ? walk(path) : Promise.resolve([path]);
    }),
  );
  return nested.flat();
}

const files = await walk(root);
const records = await Promise.all(
  files.map(async (file) => ({
    file,
    relative: relative(root, file),
    size: (await stat(file)).size,
    extension: extname(file).toLowerCase() || "[none]",
  })),
);
const failures = [];
const byExtension = new Map();

for (const record of records) {
  const current = byExtension.get(record.extension) ?? { count: 0, bytes: 0 };
  current.count += 1;
  current.bytes += record.size;
  byExtension.set(record.extension, current);
  if (record.size >= MAX_FILE_BYTES) failures.push(`${record.relative} is ${(record.size / 1024 / 1024).toFixed(2)} MiB`);
  if (record.relative === "_worker.js" || record.relative.startsWith("functions/")) {
    failures.push(`${record.relative} would deploy runtime code`);
  }
}

if (records.length >= MAX_FILES) failures.push(`${records.length} files exceeds the internal ${MAX_FILES - 1} file budget`);

for (const record of records.filter(({ extension }) => extension === ".html" || extension === ".json")) {
  const text = await readFile(record.file, "utf8");
  if (/data:image\/(?:png|jpe?g|webp|avif);base64,/i.test(text)) {
    failures.push(`${record.relative} contains an inlined raster image`);
  }
}

async function gzipSize(relativePath) {
  const buffer = await readFile(join(root, relativePath));
  return gzipSync(buffer, { level: 9 }).byteLength;
}

const indexHtmlGzip = await gzipSize("index.html");
const indexJsonGzip = await gzipSize("data/catalog-index.json");
const javascript = records.filter(({ extension }) => extension === ".js");
const javascriptGzipSizes = await Promise.all(
  javascript.map(async (record) => gzipSync(await readFile(record.file), { level: 9 }).byteLength),
);
const javascriptGzip = javascriptGzipSizes.reduce((total, size) => total + size, 0);

if (indexHtmlGzip > INDEX_HTML_GZIP) failures.push(`index.html gzip size is ${(indexHtmlGzip / 1024).toFixed(1)} KiB`);
if (indexJsonGzip > INDEX_JSON_GZIP) failures.push(`catalog-index.json gzip size is ${(indexJsonGzip / 1024).toFixed(1)} KiB`);
if (javascriptGzip > JAVASCRIPT_GZIP) failures.push(`JavaScript gzip total is ${(javascriptGzip / 1024).toFixed(1)} KiB`);

const totalBytes = records.reduce((sum, record) => sum + record.size, 0);
console.log(`Files: ${records.length}/${MAX_FILES - 1}`);
console.log(`Total output: ${(totalBytes / 1024 / 1024).toFixed(1)} MiB`);
console.log(`index.html gzip: ${(indexHtmlGzip / 1024).toFixed(1)} KiB`);
console.log(`catalog-index.json gzip: ${(indexJsonGzip / 1024).toFixed(1)} KiB`);
console.log(`JavaScript gzip: ${(javascriptGzip / 1024).toFixed(1)} KiB`);
console.log("\nAssets by extension:");
for (const [extension, value] of [...byExtension].sort((left, right) => right[1].bytes - left[1].bytes)) {
  console.log(`  ${extension.padEnd(8)} ${String(value.count).padStart(5)} files  ${(value.bytes / 1024 / 1024).toFixed(1)} MiB`);
}
console.log("\nLargest files:");
for (const record of records.toSorted((left, right) => right.size - left.size).slice(0, 10)) {
  console.log(`  ${(record.size / 1024).toFixed(1).padStart(8)} KiB  ${record.relative}`);
}

if (failures.length) {
  console.error("\nFREE-TIER CHECK: FAIL");
  failures.forEach((failure) => console.error(`  - ${failure}`));
  process.exit(1);
}
console.log("\nFREE-TIER CHECK: PASS");
