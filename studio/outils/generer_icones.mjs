/*
 * Génère les icônes PNG de K+ Studio à partir de icones/icone.svg.
 * À relancer seulement si le dessin de l'icône change :
 *     node studio/outils/generer_icones.mjs
 */
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");
const DOSSIER = path.resolve(path.dirname(new URL(import.meta.url).pathname), "../icones");
const svg = readFileSync(path.join(DOSSIER, "icone.svg"), "utf8");

// Version « maskable » : fond plein bord à bord, dessin réduit dans la zone sûre
// (les systèmes Android découpent l'icône en cercle ou en goutte).
const svgMasquable = svg
  .replace('rx="112" ', "")
  .replace('<text x="256" y="338"', '<g transform="translate(256 256) scale(0.72) translate(-256 -256)"><text x="256" y="338"')
  .replace("</text>", "</text></g>");

const navigateur = await chromium.launch();
const page = await navigateur.newPage();
for (const [nom, source, taille] of [
  ["icone-192.png", svg, 192], ["icone-512.png", svg, 512],
  ["icone-masquable-512.png", svgMasquable, 512], ["apple-touch-icon.png", svgMasquable, 180],
]) {
  await page.setViewportSize({ width: taille, height: taille });
  await page.setContent(`<html><body style="margin:0;background:transparent">
    <img src="data:image/svg+xml;base64,${Buffer.from(source).toString("base64")}"
         width="${taille}" height="${taille}"></body></html>`);
  await page.screenshot({ path: path.join(DOSSIER, nom), omitBackground: true });
  console.log("créé :", nom);
}
await navigateur.close();
