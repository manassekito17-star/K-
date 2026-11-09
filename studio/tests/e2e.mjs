/*
 * Test de bout en bout de K+ Studio dans un vrai navigateur (Chromium).
 *
 * Construit le site, le sert en local, l'ouvre avec Playwright et utilise
 * l'interface comme un utilisateur : saisie, Exécuter, Arrêter, exemples...
 * Nécessite Internet (Pyodide est téléchargé depuis cdn.jsdelivr.net).
 *
 * Utilisation (depuis la racine du projet) :
 *     node studio/tests/e2e.mjs [dossier-captures] [--sous-chemin NOM]
 *
 * --sous-chemin sert le site dans un sous-dossier (http://…/NOM/), comme
 * GitHub Pages (https://utilisateur.github.io/K-/).
 */
import { spawn, execFileSync } from "node:child_process";
import { readFileSync, mkdirSync, mkdtempSync, symlinkSync } from "node:fs";
import os from "node:os";
import { createRequire } from "node:module";
import path from "node:path";
import net from "node:net";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");

const RACINE = path.resolve(path.dirname(new URL(import.meta.url).pathname), "../..");
const args = process.argv.slice(2);
const iSous = args.indexOf("--sous-chemin");
const SOUS_CHEMIN = iSous >= 0 ? args.splice(iSous, 2)[1] : "";
const CAPTURES = args[0] || null;
const resultats = [];

function verifier(nom, condition, detail = "") {
  resultats.push({ nom, ok: Boolean(condition), detail });
  console.log(`${condition ? "ok    " : "ÉCHEC "} ${nom}${condition ? "" : "  → " + detail}`);
}

function portLibre() {
  return new Promise((resoudre) => {
    const s = net.createServer();
    s.listen(0, "127.0.0.1", () => { const p = s.address().port; s.close(() => resoudre(p)); });
  });
}

execFileSync("python3", ["studio/construire.py"], { cwd: RACINE, stdio: "inherit" });
const port = await portLibre();
let dossierServi = path.join(RACINE, "studio/dist");
if (SOUS_CHEMIN) {
  dossierServi = mkdtempSync(path.join(os.tmpdir(), "kplus-studio-"));
  symlinkSync(path.join(RACINE, "studio/dist"), path.join(dossierServi, SOUS_CHEMIN));
}
const serveur = spawn("python3", ["-m", "http.server", String(port), "--bind", "127.0.0.1",
                                  "--directory", dossierServi], { cwd: RACINE, stdio: "ignore" });
await new Promise((r) => setTimeout(r, 800));

const options = {};
if (process.env.HTTPS_PROXY) {
  options.proxy = { server: process.env.HTTPS_PROXY, bypass: "127.0.0.1,localhost" };
}
const navigateur = await chromium.launch(options);
const page = await navigateur.newPage({ viewport: { width: 1280, height: 800 } });
const erreursPage = [];
page.on("pageerror", (e) => erreursPage.push(String(e)));
page.on("console", (m) => { if (m.type() === "error") erreursPage.push(m.text()); });
page.on("dialog", (d) => d.accept());

const attendreMoteur = () => page.waitForFunction(
  () => document.getElementById("etat-moteur").textContent.includes("prêt"), null, { timeout: 180000 });
const texteConsole = () => page.locator("#console").innerText();

async function executer(source, entree = "") {
  await page.fill("#code", source);
  await page.fill("#entrees", entree);
  await page.click("#bouton-executer");
  await page.waitForFunction(() => {
    const t = document.getElementById("console").textContent;
    return /Programme (terminé|arrêté)/.test(t);
  }, null, { timeout: 60000 });
  return texteConsole();
}

try {
  const debut = Date.now();
  const adresse = `http://127.0.0.1:${port}/${SOUS_CHEMIN ? SOUS_CHEMIN + "/" : ""}`;
  console.log(`       (adresse testée : ${adresse})`);
  await page.goto(adresse);
  await attendreMoteur();
  verifier("le moteur K+ se charge dans le navigateur", true,
           `${Math.round((Date.now() - debut) / 1000)} s`);
  console.log(`       (chargement : ${Math.round((Date.now() - debut) / 1000)} s)`);

  // 1. Programme d'accueil (exemple du cahier des charges).
  await page.click("#bouton-executer");
  await page.waitForFunction(() => document.getElementById("console").textContent.includes("Programme terminé"));
  let sortie = await texteConsole();
  verifier("programme d'accueil", sortie.startsWith("Bienvenue dans K+\nTu es majeur\n30\n"), sortie);
  verifier("coloration syntaxique présente",
           await page.locator(".coloration .k-motcle").count() > 5);
  if (CAPTURES) {
    mkdirSync(CAPTURES, { recursive: true });
    await page.screenshot({ path: path.join(CAPTURES, "studio-clair.png") });
  }

  // 2. Tous les exemples, comparés aux sorties attendues des tests.
  const manifeste = JSON.parse(readFileSync(path.join(RACINE, "studio/dist/manifeste.json"), "utf8"));
  for (const exemple of manifeste.exemples) {
    await page.selectOption("#choix-exemple", exemple.nom);
    await page.waitForFunction((n) => document.getElementById("nom-fichier").textContent === n + ".kplus",
                                exemple.nom);
    await page.click("#bouton-executer");
    await page.waitForFunction(() => /Programme (terminé|arrêté)/.test(
      document.getElementById("console").textContent), null, { timeout: 60000 });
    sortie = await texteConsole();
    const attendu = readFileSync(path.join(RACINE, `tests/exemples/${exemple.nom}.sortie`), "utf8");
    if (exemple.entree) {
      // Dans Studio, les réponses utilisées sont réaffichées dans la console.
      // On reconstruit la sortie attendue en réinsérant chaque réponse
      // après l'invite « Ta proposition : ».
      const reponses = exemple.entree.split("\n").filter((l) => l !== "");
      let k = 0;
      const attenduStudio = attendu.replace(/Ta proposition : /g,
                                            () => `Ta proposition : ${reponses[k++]}\n`);
      verifier(`exemple ${exemple.nom} (avec entrées)`, sortie.startsWith(attenduStudio), sortie);
    } else {
      verifier(`exemple ${exemple.nom}`, sortie.startsWith(attendu) &&
               /Programme terminé \(\d+ ms\)\.\n?$/.test(sortie.slice(attendu.length)), sortie);
    }
  }

  // 3. Erreur d'exécution : message, ligne surlignée.
  sortie = await executer('afficher("avant")\nafficher(10 / 0)\n');
  verifier("erreur d'exécution affichée avec sa ligne",
           sortie.includes("avant\nErreur de division par zéro (ligne 2, colonne 13)"), sortie);
  verifier("ligne de l'erreur surlignée dans l'éditeur",
           await page.locator(".coloration .ligne.erreur").count() === 1 &&
           (await page.locator(".numeros .erreur").innerText()) === "2");
  await page.click(".lien-ligne");
  const selection = await page.evaluate(() => {
    const c = document.getElementById("code");
    return c.value.slice(c.selectionStart, c.selectionEnd);
  });
  verifier("« Aller à la ligne » sélectionne la ligne fautive", selection === "afficher(10 / 0)", selection);

  // 4. Vérification pendant la saisie.
  await page.fill("#code", "variable x = 1\nsi x > 0 alors\n    afficher(x)\n");
  await page.waitForFunction(() => document.getElementById("diagnostic").classList.contains("erreur"),
                             null, { timeout: 10000 });
  const diag = await page.locator("#diagnostic").innerText();
  verifier("erreur de syntaxe signalée pendant la saisie", diag.includes("ligne 2") && diag.includes("fin"), diag);
  await page.fill("#code", "variable x = 1\nsi x > 0 alors\n    afficher(x)\nfin\n");
  await page.waitForFunction(() => document.getElementById("diagnostic").classList.contains("ok"),
                             null, { timeout: 10000 });
  verifier("diagnostic correct après correction", true);

  // 5. Boucle infinie : le bouton Arrêter fonctionne et le moteur redémarre.
  await page.fill("#code", 'variable n = 0\ntant que vrai faire\n    n = n + 1\nfin\n');
  await page.click("#bouton-executer");
  await page.waitForTimeout(1500);
  verifier("la page reste réactive pendant une boucle infinie",
           await page.isEnabled("#bouton-arreter"));
  await page.click("#bouton-arreter");
  sortie = await texteConsole();
  verifier("Arrêter interrompt le programme", sortie.includes("Programme arrêté par l'utilisateur."), sortie);
  await attendreMoteur();
  sortie = await executer('afficher("de nouveau prêt")\n');
  verifier("le moteur redémarre après Arrêter", sortie.startsWith("de nouveau prêt\n"), sortie);

  // 6. Récursion et structures profondes dans le navigateur.
  sortie = await executer("fonction f(n)\n    si n == 0 alors\n        retourner 0\n    fin\n" +
                          "    retourner f(n - 1)\nfin\nafficher(f(999))\n");
  verifier("999 appels récursifs dans le navigateur", sortie.startsWith("0\n"), sortie);
  sortie = await executer("fonction f()\n    retourner f()\nfin\nf()\n");
  verifier("récursion infinie : erreur claire", sortie.includes("Erreur de récursion (ligne 2"), sortie);
  sortie = await executer("variable l = []\npour i de 1 à 5000 faire\n    l = [l]\nfin\n" +
                          "afficher(longueur(texte(l)))\n");
  verifier("liste imbriquée 5000 fois sans plantage", sortie.startsWith("10002\n"), sortie);
  sortie = await executer("afficher(" + "(".repeat(5000) + "1" + ")".repeat(5000) + ")\n");
  verifier("5000 parenthèses : erreur claire, pas de plantage",
           sortie.includes("Erreur de récursion"), sortie.slice(0, 300));
  sortie = await executer('afficher("ok")\n');
  verifier("le moteur fonctionne encore après ces cas extrêmes", sortie.startsWith("ok\n"), sortie);

  // 7. demander() avec le panneau des entrées.
  sortie = await executer('variable nom = demander("Nom ? ")\nafficher("Bonjour " + nom)\n' +
                          "afficher(demander())\n", "Awa\n");
  verifier("demander() utilise les entrées préparées", sortie.startsWith("Nom ? Awa\nBonjour Awa\nnul\n"), sortie);

  // 8. Grosse sortie : la page reste utilisable.
  sortie = await executer('pour i de 1 à 20000 faire\n    afficher("ligne", i)\nfin\n');
  verifier("20 000 lignes affichées", sortie.includes("ligne 20000\n"), sortie.slice(-200));

  // 9. Thème sombre et petit écran (captures).
  if (CAPTURES) {
    await page.fill("#code", readFileSync(path.join(RACINE, "exemples/statistiques.kplus"), "utf8"));
    await page.click("#bouton-executer");
    await page.waitForFunction(() => document.getElementById("console").textContent.includes("Programme terminé"));
    await page.emulateMedia({ colorScheme: "dark" });
    await page.screenshot({ path: path.join(CAPTURES, "studio-sombre.png") });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.screenshot({ path: path.join(CAPTURES, "studio-mobile.png"), fullPage: true });
    const deborde = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
    verifier("pas de défilement horizontal sur téléphone", !deborde);
  }

  verifier("aucune erreur JavaScript dans la page", erreursPage.length === 0, erreursPage.join("\n"));
} catch (e) {
  verifier("déroulement du test", false, String(e && e.stack || e));
} finally {
  await navigateur.close();
  serveur.kill();
}

const echecs = resultats.filter((r) => !r.ok).length;
console.log(`\n${resultats.length - echecs}/${resultats.length} vérifications réussies.`);
process.exit(echecs ? 1 : 0);
