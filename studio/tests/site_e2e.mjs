/*
 * Test de bout en bout des sites créés avec « kplus --site » : le site est
 * produit par la vraie commande, servi par un serveur web, puis utilisé dans
 * Chromium comme le ferait un visiteur.
 *
 * Utilisation (depuis la racine du projet) : node studio/tests/site_e2e.mjs
 */
import { spawn, execFileSync } from "node:child_process";
import { mkdtempSync } from "node:fs";
import { createRequire } from "node:module";
import net from "node:net";
import os from "node:os";
import path from "node:path";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");
const RACINE = path.resolve(path.dirname(new URL(import.meta.url).pathname), "../..");
const python = process.platform === "win32" ? "python" : "python3";
const resultats = [];

function verifier(nom, condition, detail = "") {
  resultats.push(Boolean(condition));
  console.log(`${condition ? "ok    " : "ÉCHEC "} ${nom}${condition ? "" : "  → " + detail}`);
}
const portLibre = () => new Promise((ok) => {
  const s = net.createServer();
  s.listen(0, "127.0.0.1", () => { const p = s.address().port; s.close(() => ok(p)); });
});

const dossier = mkdtempSync(path.join(os.tmpdir(), "kplus-sites-"));
for (const nom of ["site_taches", "site_calculatrice"]) {
  execFileSync(python, ["-m", "kplus", "--site", `exemples/${nom}.kplus`, path.join(dossier, nom)],
               { cwd: RACINE });
}
const port = await portLibre();
const serveur = spawn(python, ["-m", "http.server", String(port), "--bind", "127.0.0.1", "--directory", dossier],
                      { stdio: "ignore" });
await new Promise((r) => setTimeout(r, 800));

const options = process.env.HTTPS_PROXY
  ? { proxy: { server: process.env.HTTPS_PROXY, bypass: "127.0.0.1,localhost" } } : {};
const navigateur = await chromium.launch(options);
const page = await navigateur.newPage();
const erreurs = [];
page.on("pageerror", (e) => erreurs.push(String(e)));

try {
  await page.goto(`http://127.0.0.1:${port}/site_taches/`);
  await page.waitForSelector("#kp-page h1", { timeout: 120000 });
  verifier("le site se charge (moteur K+ dans le navigateur)", (await page.locator("h1").innerText()) === "Mes tâches");
  verifier("message de chargement retiré", (await page.locator("#kp-chargement").count()) === 0);
  for (const [i, tache] of ["Réviser", "Publier le site"].entries()) {
    await page.locator("input").fill(tache);
    await page.getByRole("button", { name: "Ajouter" }).click();
    await page.waitForFunction((n) => document.querySelectorAll("li").length === n, i + 1);
  }
  verifier("clics : tâches ajoutées et compteur", (await page.locator("p").innerText()) === "2 tâche(s)");
  await page.locator("li", { hasText: "Réviser" }).click();
  await page.waitForFunction(() => document.querySelectorAll("li").length === 1);
  verifier("clic sur une tâche : supprimée", (await page.locator("p").innerText()) === "1 tâche(s)");

  await page.goto(`http://127.0.0.1:${port}/site_calculatrice/`);
  await page.waitForSelector("#kp-page h1", { timeout: 120000 });
  verifier("titre de l'onglet défini par titre_page()", (await page.title()) === "Calculatrice", await page.title());
  await page.locator("input").fill("4.5");
  await page.getByRole("button", { name: "Calculer" }).click();
  await page.waitForFunction(() => document.querySelector("p").textContent === "Le double est 9.0");
  verifier("calculatrice : résultat affiché", true);
  verifier("aucune erreur JavaScript", erreurs.length === 0, erreurs.join("\n"));
} catch (e) {
  verifier("déroulement du test", false, String(e && e.stack || e));
} finally {
  await navigateur.close();
  serveur.kill();
}
const echecs = resultats.filter((r) => !r).length;
console.log(`\n${resultats.length - echecs}/${resultats.length} vérifications réussies.`);
process.exit(echecs ? 1 : 0);
