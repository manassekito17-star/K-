/*
 * Extension K+ pour Visual Studio Code.
 *
 * - Couleurs : syntaxes/kplus.tmLanguage.json (aucun code nécessaire).
 * - Correction : les erreurs sont soulignées en rouge pendant la saisie.
 *   Elles viennent du VRAI moteur K+ (moteur/kplus), interrogé par
 *   moteur/serveur_verification.py, lancé avec le Python de l'ordinateur.
 * - Exécution : bouton ▶ (ou Ctrl+Entrée) qui lance le programme dans le
 *   terminal de VS Code.
 */
"use strict";

const vscode = require("vscode");
const { spawn, spawnSync } = require("child_process");
const path = require("path");

const VERSION_PYTHON_MIN = [3, 10];
let python = null;                 // { commande, arguments } une fois trouvé
let serveur = null;                // processus du serveur de vérification
let tamponServeur = "";
let prochainId = 1;
const enAttente = new Map();       // id -> { uri, version }
let diagnostics;
let barreEtat;
let sortieJournal;
const minuteurs = new Map();       // uri -> minuteur de vérification

// --- Python ----------------------------------------------------------------

function candidatsPython() {
  const reglage = vscode.workspace.getConfiguration("kplus").get("cheminPython", "").trim();
  if (reglage) return [{ commande: reglage, arguments: [] }];
  if (process.platform === "win32") {
    return [{ commande: "py", arguments: ["-3"] }, { commande: "python", arguments: [] },
            { commande: "python3", arguments: [] }];
  }
  return [{ commande: "python3", arguments: [] }, { commande: "python", arguments: [] }];
}

function trouverPython() {
  const test = `import sys; print(1 if sys.version_info[:2] >= (${VERSION_PYTHON_MIN.join(", ")}) else 0)`;
  for (const candidat of candidatsPython()) {
    try {
      const r = spawnSync(candidat.commande, [...candidat.arguments, "-c", test],
                          { encoding: "utf8", timeout: 10000, windowsHide: true });
      if (r.status === 0 && r.stdout.trim() === "1") return candidat;
    } catch (e) { /* candidat suivant */ }
  }
  return null;
}

function signalerPythonManquant() {
  barreEtat.text = "$(warning) K+ : Python introuvable";
  barreEtat.tooltip = "Installez Python 3.10 ou plus récent pour la correction et l'exécution.";
  vscode.window.showWarningMessage(
    "K+ : Python 3.10 (ou plus récent) est introuvable. Les couleurs fonctionnent, " +
    "mais la correction et l'exécution des programmes ont besoin de Python.",
    "Télécharger Python", "Indiquer le chemin de Python"
  ).then((choix) => {
    if (choix === "Télécharger Python") {
      vscode.env.openExternal(vscode.Uri.parse("https://www.python.org/downloads/"));
    } else if (choix === "Indiquer le chemin de Python") {
      vscode.commands.executeCommand("workbench.action.openSettings", "kplus.cheminPython");
    }
  });
}

// --- Serveur de vérification -------------------------------------------------

function dossierMoteur(contexte) {
  return path.join(contexte.extensionPath, "moteur");
}

function demarrerServeur(contexte) {
  if (!python) return;
  const script = path.join(dossierMoteur(contexte), "serveur_verification.py");
  serveur = spawn(python.commande, [...python.arguments, "-X", "utf8", script],
                  { windowsHide: true, env: { ...process.env, PYTHONIOENCODING: "utf-8" } });
  tamponServeur = "";
  serveur.stdout.setEncoding("utf8");
  serveur.stdout.on("data", (morceau) => {
    tamponServeur += morceau;
    let fin;
    while ((fin = tamponServeur.indexOf("\n")) >= 0) {
      const ligne = tamponServeur.slice(0, fin);
      tamponServeur = tamponServeur.slice(fin + 1);
      if (ligne.trim()) recevoir(JSON.parse(ligne));
    }
  });
  serveur.stderr.setEncoding("utf8");
  serveur.stderr.on("data", (t) => sortieJournal.append(t));
  serveur.on("exit", (code) => {
    sortieJournal.appendLine(`Serveur de vérification arrêté (code ${code}).`);
    serveur = null;
    enAttente.clear();
  });
}

function recevoir(message) {
  if (message.pret) {
    barreEtat.text = "$(check) K+";
    barreEtat.tooltip = `Moteur K+ ${message.version} : correction active`;
    return;
  }
  if (message.interne) sortieJournal.appendLine(`Erreur interne : ${message.interne}`);
  const demande = enAttente.get(message.id);
  if (!demande) return;
  enAttente.delete(message.id);
  const document = vscode.workspace.textDocuments.find((d) => d.uri.toString() === demande.uri);
  if (!document || document.version !== demande.version) return;   // texte déjà modifié
  diagnostics.set(document.uri, message.ok ? [] : [creerDiagnostic(document, message.erreur)]);
}

function creerDiagnostic(document, erreur) {
  const ligne = Math.min(Math.max((erreur.ligne || 1) - 1, 0), document.lineCount - 1);
  const texteLigne = document.lineAt(ligne).text;
  const colonne = Math.min(Math.max((erreur.colonne || 1) - 1, 0), texteLigne.length);
  const position = new vscode.Position(ligne, colonne);
  let etendue = document.getWordRangeAtPosition(position);
  if (!etendue) {
    const fin = Math.min(colonne + 1, texteLigne.length);
    etendue = new vscode.Range(ligne, colonne, ligne, fin > colonne ? fin : colonne);
  }
  let texte = `${erreur.nom} : ${erreur.message}`;
  if (erreur.conseil) texte += `\nConseil : ${erreur.conseil}`;
  const d = new vscode.Diagnostic(etendue, texte, vscode.DiagnosticSeverity.Error);
  d.source = "K+";
  d.code = erreur.categorie;
  return d;
}

function verifier(document) {
  if (document.languageId !== "kplus") return;
  if (!vscode.workspace.getConfiguration("kplus").get("correctionPendantSaisie", true)) {
    diagnostics.delete(document.uri);
    return;
  }
  if (!serveur) return;
  const id = prochainId++;
  enAttente.set(id, { uri: document.uri.toString(), version: document.version });
  serveur.stdin.write(JSON.stringify({ id, source: document.getText() }) + "\n");
}

function verifierPlusTard(document, delai = 300) {
  const cle = document.uri.toString();
  clearTimeout(minuteurs.get(cle));
  minuteurs.set(cle, setTimeout(() => verifier(document), delai));
}

// --- Exécution dans le terminal ------------------------------------------------

function citer(texte) {
  return `"${texte.replace(/"/g, '\\"')}"`;
}

async function executer(contexte, uri) {
  const editeur = vscode.window.activeTextEditor;
  const document = uri
    ? await vscode.workspace.openTextDocument(uri)
    : editeur && editeur.document;
  if (!document || document.languageId !== "kplus") {
    vscode.window.showInformationMessage("Ouvrez un fichier .kplus pour l'exécuter.");
    return;
  }
  if (!python) { signalerPythonManquant(); return; }
  if (document.isUntitled) {
    const enregistre = await document.save();
    if (!enregistre || document.isUntitled) {
      vscode.window.showInformationMessage("Enregistrez d'abord le fichier (extension .kplus).");
      return;
    }
  } else if (document.isDirty) {
    await document.save();
  }

  const nom = "K+";
  let terminal = vscode.window.terminals.find((t) => t.name === nom);
  if (!terminal) {
    terminal = vscode.window.createTerminal({
      name: nom,
      env: { PYTHONPATH: dossierMoteur(contexte), PYTHONIOENCODING: "utf-8" },
    });
  }
  terminal.show(true);
  const commande = [python.commande, ...python.arguments, "-m", "kplus", document.uri.fsPath]
    .map((partie) => (/[\s"'$&;|()`]/.test(partie) ? citer(partie) : partie))
    .join(" ");
  // PowerShell exige « & » devant une commande entre guillemets.
  const prefixe = process.platform === "win32" && /\s/.test(python.commande) ? "& " : "";
  terminal.sendText(prefixe + commande);
}

// --- Activation ------------------------------------------------------------------

function activate(contexte) {
  diagnostics = vscode.languages.createDiagnosticCollection("kplus");
  sortieJournal = vscode.window.createOutputChannel("K+");
  barreEtat = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
  barreEtat.text = "$(sync~spin) K+";
  barreEtat.command = "kplus.verifier";
  barreEtat.show();
  contexte.subscriptions.push(diagnostics, sortieJournal, barreEtat);

  python = trouverPython();
  if (python) {
    sortieJournal.appendLine(`Python trouvé : ${python.commande} ${python.arguments.join(" ")}`);
    demarrerServeur(contexte);
  } else {
    signalerPythonManquant();
  }

  contexte.subscriptions.push(
    vscode.commands.registerCommand("kplus.executer", (uri) => executer(contexte, uri)),
    vscode.commands.registerCommand("kplus.verifier", () => {
      const editeur = vscode.window.activeTextEditor;
      if (editeur) verifier(editeur.document);
    }),
    vscode.workspace.onDidOpenTextDocument((d) => verifier(d)),
    vscode.workspace.onDidChangeTextDocument((e) => verifierPlusTard(e.document)),
    vscode.workspace.onDidCloseTextDocument((d) => diagnostics.delete(d.uri)),
    vscode.workspace.onDidChangeConfiguration((e) => {
      if (e.affectsConfiguration("kplus.cheminPython")) {
        if (serveur) serveur.kill();
        python = trouverPython();
        if (python) demarrerServeur(contexte); else signalerPythonManquant();
        const terminal = vscode.window.terminals.find((t) => t.name === "K+");
        if (terminal) terminal.dispose();
      }
      if (e.affectsConfiguration("kplus")) vscode.workspace.textDocuments.forEach(verifier);
    }),
    { dispose: () => { if (serveur) serveur.kill(); } },
  );

  // Fichiers déjà ouverts au démarrage.
  setTimeout(() => vscode.workspace.textDocuments.forEach(verifier), 200);
}

function deactivate() {
  if (serveur) serveur.kill();
}

module.exports = { activate, deactivate, _pourTests: { creerDiagnostic, candidatsPython } };
