/*
 * Test de l'extension dans un VRAI VS Code (téléchargé automatiquement).
 *
 * Le test installe le paquet .vsix réellement produit (pas le dossier de
 * travail) : on vérifie exactement ce que l'utilisateur installera.
 *
 * Utilisation (depuis la racine du projet) :
 *     python vscode/construire.py --paquet
 *     xvfb-run -a node vscode/tests/lancer.mjs      (Linux sans écran)
 *     node vscode/tests/lancer.mjs                  (Windows, macOS)
 */
import { runTests } from "@vscode/test-electron";
import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, writeFileSync, mkdirSync, readdirSync } from "node:fs";
import os from "node:os";
import path from "node:path";

const ICI = path.dirname(new URL(import.meta.url).pathname);
const VSCODE = path.resolve(ICI, "..");
const VERSION_VSCODE = "1.96.4";

const version = JSON.parse(readFileSync(path.join(VSCODE, "package.json"), "utf8")).version;
const vsix = path.join(VSCODE, "dist", `kplus-${version}.vsix`);
const temporaire = mkdtempSync(path.join(os.tmpdir(), "kplus-vscode-"));

// 1. Décompresser le .vsix (c'est une archive zip ; l'extension est dans « extension/»).
const python = process.platform === "win32" ? "python" : "python3";
execFileSync(python, ["-c", "import sys, zipfile; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])",
                      vsix, path.join(temporaire, "vsix")]);
const extension = path.join(temporaire, "vsix", "extension");
console.log("Paquet testé :", vsix, "→", readdirSync(extension).join(", "));

// 2. Dossier de travail avec quelques fichiers K+.
const espace = path.join(temporaire, "espace");
mkdirSync(espace);
writeFileSync(path.join(espace, "bonjour.kplus"), 'afficher("Bonjour depuis VS Code", 6 * 7)\n');

// Réglages de la fenêtre (utile pour les captures d'écran facultatives).
const donnees = path.join(temporaire, "donnees");
mkdirSync(path.join(donnees, "User"), { recursive: true });
writeFileSync(path.join(donnees, "User", "settings.json"), JSON.stringify({
  "window.newWindowDimensions": "maximized",
  "workbench.startupEditor": "none",
  "editor.fontSize": 15,
  "editor.minimap.enabled": false,
  "workbench.tips.enabled": false,
}));

// 3. Lancer VS Code avec l'extension et la suite de tests.
try {
  await runTests({
    version: VERSION_VSCODE,
    extensionDevelopmentPath: extension,
    extensionTestsPath: path.join(ICI, "suite", "index.js"),
    // KPLUS_CAPTURE=fichier.png : capture d'écran à la fin (Linux, avec xvfb).
    extensionTestsEnv: { KPLUS_CAPTURE: process.env.KPLUS_CAPTURE || "" },
    launchArgs: [espace, "--disable-extensions", "--disable-workspace-trust", "--no-sandbox",
                 "--user-data-dir", donnees, "--skip-welcome",
                 "--skip-release-notes", "--disable-gpu"],
  });
} catch (erreur) {
  console.error("Échec des tests dans VS Code :", erreur.message || erreur);
  process.exit(1);
}
