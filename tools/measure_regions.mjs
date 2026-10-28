// Mide el área visible (px² en 1024x1024) de cada región coloreable.
// Pinta cada región con un color único conservando los contornos negros,
// oculta los detalles y cuenta los píxeles de cada color.
// Uso (desde la raíz del proyecto): node tools/measure_regions.mjs
// Resultado: build/qa/region_areas.json (lo usa tools/validate_assets.py).
import { createRequire } from "node:module";
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
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
const result = {};
for (const item of catalog.drawings) {
  await page.goto(pathToFileURL(resolve(root, item.file)).href);
  result[item.id] = await page.evaluate(async () => {
    const svg = document.querySelector("svg");
    svg.querySelector("#detalles")?.remove();
    const regions = [...svg.querySelectorAll("#regiones > path")];
    // Colores separados 7 unidades por canal para tolerar redondeos.
    const color = (i) => [((i + 1) * 7) % 256, 40 + (((i + 1) * 13) % 200), 200];
    regions.forEach((el, i) => el.setAttribute("fill", `rgb(${color(i).join(",")})`));
    const blob = new Blob([new XMLSerializer().serializeToString(svg)], { type: "image/svg+xml" });
    const img = document.createElementNS("http://www.w3.org/1999/xhtml", "img");
    img.src = URL.createObjectURL(blob);
    await img.decode();
    const canvas = document.createElementNS("http://www.w3.org/1999/xhtml", "canvas");
    canvas.width = canvas.height = 1024;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(img, 0, 0, 1024, 1024);
    const px = ctx.getImageData(0, 0, 1024, 1024).data;
    const key = (r, g, b) => (r << 16) | (g << 8) | b;
    const index = new Map(regions.map((el, i) => [key(...color(i)), el.id]));
    const areas = Object.fromEntries(regions.map((el) => [el.id, 0]));
    for (let p = 0; p < px.length; p += 4) {
      const id = index.get(key(px[p], px[p + 1], px[p + 2]));
      if (id) areas[id]++;
    }
    return areas;
  });
  console.log(item.id, Object.keys(result[item.id]).length - 1, "regiones");
}
await browser.close();
mkdirSync(resolve(root, "build/qa"), { recursive: true });
writeFileSync(resolve(root, "build/qa/region_areas.json"), JSON.stringify(result, null, 2) + "\n");
