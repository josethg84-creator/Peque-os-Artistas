// Renderiza cada SVG del catálogo a PNG 1024x1024 (fondo blanco) con Chromium.
// Uso (desde la raíz del proyecto): node tools/render_previews.mjs
import { createRequire } from "node:module";
import { readFileSync, mkdirSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const require = createRequire(import.meta.url);
let playwright;
try {
  playwright = require("playwright");
} catch {
  playwright = require("/opt/node-tools/node_modules/playwright");
}

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const catalog = JSON.parse(readFileSync(resolve(root, "assets/catalog/catalog.json"), "utf8"));

const browser = await playwright.chromium.launch();
const page = await browser.newPage({ viewport: { width: 1024, height: 1024 }, deviceScaleFactor: 1 });
for (const item of catalog.drawings) {
  const out = resolve(root, item.preview);
  mkdirSync(dirname(out), { recursive: true });
  await page.goto(pathToFileURL(resolve(root, item.file)).href);
  await page.screenshot({ path: out, omitBackground: false });
  console.log(`${item.id} -> ${item.preview}`);
}
await browser.close();
