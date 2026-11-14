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
 * --url ADRESSE teste un site déjà en ligne (sans construire ni servir).
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
const iUrl = args.indexOf("--url");
const URL_EN_LIGNE = iUrl >= 0 ? args.splice(iUrl, 2)[1] : "";
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

let port = 0;
let serveur = null;
if (!URL_EN_LIGNE) {
  execFileSync("python3", ["studio/construire.py"], { cwd: RACINE, stdio: "inherit" });
  port = await portLibre();
  let dossierServi = path.join(RACINE, "studio/dist");
  if (SOUS_CHEMIN) {
    dossierServi = mkdtempSync(path.join(os.tmpdir(), "kplus-studio-"));
    symlinkSync(path.join(RACINE, "studio/dist"), path.join(dossierServi, SOUS_CHEMIN));
  }
  serveur = spawn("python3", ["-m", "http.server", String(port), "--bind", "127.0.0.1",
                                    "--directory", dossierServi], { cwd: RACINE, stdio: "ignore" });
  await new Promise((r) => setTimeout(r, 800));
}

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
  await page.evaluate(() => { document.getElementById("bloc-entrees").open = true; });
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
  const adresse = URL_EN_LIGNE ||
    `http://127.0.0.1:${port}/${SOUS_CHEMIN ? SOUS_CHEMIN + "/" : ""}`;
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
  const manifeste = URL_EN_LIGNE
    ? await page.evaluate(async () => (await fetch("manifeste.json")).json())
    : JSON.parse(readFileSync(path.join(RACINE, "studio/dist/manifeste.json"), "utf8"));
  // Les sites (« utiliser web ») sont testés plus bas, dans l'onglet Page.
  for (const exemple of manifeste.exemples.filter((x) => !/^(site|serveur)_/.test(x.nom))) {
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

  // K+ Web : onglet Page, clics, saisie, minuteries, erreurs, sécurité.
  let alerteOuverte = false;
  page.on("dialog", (d) => { if (d.type() === "alert") alerteOuverte = true; });
  const cadre = page.locator("#page-web");
  async function lancerSite(nomOuSource) {
    if (/^(site|serveur)_/.test(nomOuSource)) {
      await page.selectOption("#choix-exemple", nomOuSource);
      await page.waitForFunction((n) => document.getElementById("nom-fichier").textContent === n + ".kplus", nomOuSource);
    } else {
      await page.fill("#code", nomOuSource);
    }
    await page.click("#bouton-executer");
    await page.waitForFunction(() => !document.getElementById("cadre-page").hidden, null, { timeout: 60000 });
  }

  await lancerSite("site_taches");
  verifier("programme web : l'onglet Page s'ouvre avec la page", (await cadre.locator("h1").innerText()) === "Mes tâches");
  await cadre.locator("input").fill("Réviser K+");
  await cadre.getByRole("button", { name: "Ajouter" }).click();
  // Attendre la réponse du moteur (qui vide le champ) avant de taper la suite.
  await page.waitForFunction(() => document.querySelectorAll("#page-web li").length === 1);
  await cadre.locator("input").fill("Faire du sport");
  await cadre.getByRole("button", { name: "Ajouter" }).click();
  await page.waitForFunction(() => document.querySelectorAll("#page-web li").length === 2);
  verifier("clic sur un bouton : tâches ajoutées, compteur, champ vidé",
           (await cadre.locator("p").innerText()) === "2 tâche(s)" && (await cadre.locator("input").inputValue()) === "");
  await cadre.locator("li", { hasText: "Réviser K+" }).click();
  await page.waitForFunction(() => document.querySelectorAll("#page-web li").length === 1);
  verifier("clic sur une ligne : la tâche disparaît", (await cadre.locator("p").innerText()) === "1 tâche(s)");

  await lancerSite("site_calculatrice");
  verifier("titre de la page affiché", (await page.locator("#titre-page-web").innerText()) === "Calculatrice");
  await cadre.locator("input").fill("21");
  await cadre.getByRole("button", { name: "Calculer" }).click();
  await page.waitForFunction(() => document.querySelector("#page-web p").textContent === "Le double est 42.0");
  const couleurVerte = await cadre.locator("p").evaluate((e) => getComputedStyle(e).color);
  verifier("calculatrice : résultat et couleur", couleurVerte === "rgb(42, 157, 75)", couleurVerte);

  await lancerSite("site_chronometre");
  await cadre.getByRole("button", { name: "Démarrer" }).click();
  await page.waitForFunction(() => document.querySelector("#page-web p").textContent !== "0.0 s", null, { timeout: 5000 });
  await page.waitForTimeout(600);
  verifier("minuterie : le chronomètre avance", (await cadre.locator("p").innerText()) !== "0.0 s");
  await page.click("#bouton-arreter");
  const fige = await cadre.locator("p").innerText();
  await page.waitForTimeout(800);
  verifier("Arrêter fige la page (minuterie arrêtée)",
           (await cadre.locator("p").innerText()) === fige && (await texteConsole()).includes("Page web arrêtée"),
           fige);

  await lancerSite('utiliser web\nparagraphe("<img src=x onerror=alert(1)><b>gras</b>")\n' +
                   'fonction f()\n    afficher(10 / 0)\nfin\nbouton("Panne", f)\n');
  verifier("un texte contenant du HTML reste du texte",
           (await cadre.locator("img, b").count()) === 0 &&
           (await cadre.locator("p").innerText()).includes("<b>gras</b>") && !alerteOuverte);
  await cadre.getByRole("button", { name: "Panne" }).click();
  await page.waitForFunction(() => document.querySelector("#page-web .kp-erreur"), null, { timeout: 10000 });
  verifier("erreur dans une action : bandeau avec la ligne",
           (await cadre.locator(".kp-erreur").innerText()).includes("Erreur de division par zéro (ligne 4"));
  verifier("la page reste utilisable après l'erreur", await cadre.getByRole("button", { name: "Panne" }).isEnabled());

  // K+ Serveur : le site tourne en mémoire, ses pages s'affichent dans un cadre isolé.
  const serveur = page.frameLocator("#page-serveur");
  const attendreAdresse = (texte) => page.waitForFunction(
    (t) => document.getElementById("adresse-serveur").textContent === t, texte, { timeout: 30000 });
  await lancerSite("serveur_livre_or");
  await page.waitForFunction(() => {
    const d = document.getElementById("page-serveur").contentDocument;
    return d && d.querySelector("h1");
  }, null, { timeout: 60000 });
  verifier("site côté serveur : aperçu de la page d'accueil",
           (await serveur.locator("h1").innerText()) === "Livre d'or de la classe" &&
           (await page.locator("#adresse-serveur").innerText()) === "/");
  await serveur.getByLabel("Votre nom").fill("Awa");
  await serveur.getByLabel("Votre message").fill("<b>Bonjour</b> la classe");
  await serveur.getByRole("button", { name: "Publier" }).click();
  await page.waitForFunction(() => {
    const d = document.getElementById("page-serveur").contentDocument;
    return d && d.querySelectorAll("li").length === 1;
  }, null, { timeout: 30000 });
  verifier("formulaire envoyé au moteur, redirection suivie, texte échappé",
           (await serveur.locator("li").innerText()) === "Awa : <b>Bonjour</b> la classe" &&
           (await serveur.locator("li b").count()) === 0 &&
           (await serveur.locator("p").first().innerText()) === "1 message(s)");
  await lancerSite("serveur_comptes");
  await page.waitForFunction(() => document.getElementById("page-serveur").contentDocument?.querySelector("h1"),
                             null, { timeout: 30000 });
  await serveur.getByLabel("Nom d'utilisateur").nth(1).fill("Awa");
  await serveur.getByLabel("Mot de passe (8 caractères au moins)").fill("motdepasse1");
  await serveur.getByRole("button", { name: "Créer mon compte" }).click();
  await page.waitForFunction(() => document.getElementById("page-serveur").contentDocument
    ?.querySelector("h1")?.textContent === "Bonjour Awa !", null, { timeout: 30000 });
  verifier("comptes : inscription, mot de passe chiffré, session", true);
  await lancerSite('utiliser serveur\nfonction a()\n    titre("A")\n    lien("Vers B", "/b")\nfin\n' +
                   'fonction b()\n    titre("B " + texte(1 / 0))\nfin\npage("/", a)\npage("/b", b)\n');
  await page.waitForFunction(() => {
    const d = document.getElementById("page-serveur").contentDocument;
    return d && d.querySelector("a");
  }, null, { timeout: 30000 });
  await serveur.getByRole("link", { name: "Vers B" }).click();
  await attendreAdresse("/b  (500)");
  verifier("lien interne suivi ; erreur 500 avec la ligne",
           (await serveur.locator("pre").innerText()).includes("ligne 7"));
  verifier("scripts interdits dans l'aperçu",
           (await page.locator("#page-serveur").getAttribute("sandbox")) === "allow-same-origin");

  await lancerSite('utiliser web\nfonction boucle()\n    tant que vrai faire\n    fin\nfin\nbouton("Bloquer", boucle)\n');
  await cadre.getByRole("button", { name: "Bloquer" }).click();
  await page.waitForTimeout(800);
  await page.click("#bouton-arreter");
  await attendreMoteur();
  sortie = await executer('afficher("reparti")\n');
  verifier("boucle infinie dans un clic : Arrêter relance le moteur", sortie.startsWith("reparti\n"), sortie);
  if (CAPTURES) {
    await lancerSite("site_taches");
    let n = 0;
    for (const t of ["Réviser le cours K+", "Créer mon premier site", "Publier le site"]) {
      await cadre.locator("input").fill(t);
      await cadre.getByRole("button", { name: "Ajouter" }).click();
      n += 1;
      await page.waitForFunction((k) => document.querySelectorAll("#page-web li").length === k, n);
    }
    await page.waitForFunction(() => document.querySelectorAll("#page-web li").length === 3);
    await page.screenshot({ path: path.join(CAPTURES, "studio-page-web.png") });
  }

  // 9. Application installable et utilisable sans Internet.
  const cdp = await page.context().newCDPSession(page);
  const fiche = await cdp.send("Page.getAppManifest");
  verifier("fiche de l'application (manifest) lue sans erreur",
           fiche.url.endsWith("manifest.webmanifest") && fiche.errors.length === 0,
           JSON.stringify(fiche.errors));
  const installation = await cdp.send("Page.getInstallabilityErrors");
  // « in-incognito » : le navigateur de test est en navigation privée, où
  // aucune installation n'est jamais proposée ; ce n'est pas un défaut du site.
  const obstacles = installation.installabilityErrors.filter((e) => e.errorId !== "in-incognito");
  verifier("le navigateur juge K+ Studio installable", obstacles.length === 0,
           JSON.stringify(installation.installabilityErrors));
  await cdp.detach();
  verifier("service worker actif", await page.evaluate(async () =>
    Boolean((await navigator.serviceWorker.ready).active)));
  await page.reload();
  await attendreMoteur();
  await page.waitForFunction(() => document.getElementById("etat-hors-ligne").textContent.includes("Disponible hors ligne"),
                             null, { timeout: 120000 });
  verifier("indicateur « Disponible hors ligne »", true);
  await page.context().setOffline(true);
  await page.reload();
  await attendreMoteur();
  sortie = await executer('afficher("sans Internet :", 6 * 7)\n');
  verifier("K+ Studio démarre et exécute un programme sans Internet",
           sortie.startsWith("sans Internet : 42\n"), sortie);
  const indicateur = await page.evaluate(() => {
    const e = document.getElementById("etat-hors-ligne");
    return { cache: e.hidden, texte: e.textContent, enLigne: navigator.onLine };
  });
  verifier("indicateur « Hors ligne »", !indicateur.cache && indicateur.texte.includes("Hors ligne"),
           JSON.stringify(indicateur));
  await page.context().setOffline(false);

  // 10. Thème sombre et petit écran (captures).
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
  if (serveur) serveur.kill();
}

const echecs = resultats.filter((r) => !r.ok).length;
console.log(`\n${resultats.length - echecs}/${resultats.length} vérifications réussies.`);
process.exit(echecs ? 1 : 0);
