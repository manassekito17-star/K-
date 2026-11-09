/*
 * Suite exécutée À L'INTÉRIEUR de VS Code (voir lancer.mjs).
 * Chaque cas utilise l'éditeur comme une personne : ouvrir, taper, exécuter.
 */
"use strict";
const vscode = require("vscode");
const assert = require("assert");
const fs = require("fs");
const path = require("path");

const pause = (ms) => new Promise((r) => setTimeout(r, ms));

async function attendre(condition, description, delai = 30000) {
  const fin = Date.now() + delai;
  while (Date.now() < fin) {
    const valeur = await condition();
    if (valeur) return valeur;
    await pause(100);
  }
  throw new Error(`délai dépassé : ${description}`);
}

async function ouvrir(dossier, nom, contenu) {
  const fichier = path.join(dossier, nom);
  fs.writeFileSync(fichier, contenu, "utf8");
  const document = await vscode.workspace.openTextDocument(fichier);
  const editeur = await vscode.window.showTextDocument(document);
  return { document, editeur, fichier };
}

exports.run = async function () {
  const dossier = vscode.workspace.workspaceFolders[0].uri.fsPath;
  const resultats = [];
  async function cas(nom, fonction) {
    try {
      await fonction();
      resultats.push(true);
      console.log(`ok     ${nom}`);
    } catch (e) {
      resultats.push(false);
      console.log(`ÉCHEC  ${nom}  → ${e && e.message}`);
    }
  }
  const diagnostics = (document) => vscode.languages.getDiagnostics(document.uri);

  await cas("les fichiers .kplus sont reconnus comme du K+", async () => {
    const { document } = await ouvrir(dossier, "langage.kplus", "afficher(1)\n");
    assert.strictEqual(document.languageId, "kplus");
    const ext = vscode.extensions.getExtension("kplus-langage.kplus");
    await attendre(() => ext && ext.isActive, "activation de l'extension");
  });

  let essai;
  await cas("erreur de syntaxe soulignée pendant la saisie (bonne ligne)", async () => {
    essai = await ouvrir(dossier, "erreur.kplus", 'afficher("ok")\nsi vrai alors\n    afficher(1)\n');
    const [d] = await attendre(() => diagnostics(essai.document).length && diagnostics(essai.document),
                               "diagnostic d'erreur");
    assert.strictEqual(d.range.start.line, 1);
    assert.strictEqual(d.source, "K+");
    assert.strictEqual(d.code, "ErreurSyntaxe");
    assert.strictEqual(d.severity, vscode.DiagnosticSeverity.Error);
    assert.match(d.message, /jamais fermé par « fin »/);
  });

  await cas("le soulignement disparaît une fois l'erreur corrigée", async () => {
    await essai.editeur.edit((e) => e.insert(new vscode.Position(3, 0), "fin\n"));
    await attendre(() => diagnostics(essai.document).length === 0, "disparition du diagnostic");
  });

  await cas("l'erreur réapparaît si on la recrée en tapant", async () => {
    await essai.editeur.edit((e) => e.insert(new vscode.Position(0, 0), "variable x\n"));
    const [d] = await attendre(() => diagnostics(essai.document).length && diagnostics(essai.document),
                               "nouveau diagnostic");
    assert.strictEqual(d.range.start.line, 0);
    assert.match(d.message, /Conseil : exemple : variable x = nul/);
  });

  await cas("position exacte avec accents (UTF-8) et conseil", async () => {
    const { document } = await ouvrir(dossier, "accents.kplus", 'variable été = “à”\nafficher(été) ; afficher(1)\n');
    const [d] = await attendre(() => diagnostics(document).length && diagnostics(document), "diagnostic");
    assert.strictEqual(d.range.start.line, 1);
    assert.strictEqual(d.range.start.character, 14);
    assert.strictEqual(d.code, "ErreurLexicale");
    assert.match(d.message, /point-virgule/);
  });

  await cas("un programme correct n'est pas souligné (même s'il échouerait à l'exécution)", async () => {
    const { document } = await ouvrir(dossier, "correct.kplus", "afficher(1 / 0)\n");
    await pause(2500);
    assert.strictEqual(diagnostics(document).length, 0);
  });

  await cas("couleurs : mots-clés, textes, nombres, commentaires", async () => {
    const { document } = await ouvrir(dossier, "couleurs.kplus",
      'si age >= 18 alors # majeur\n    afficher("Tu es majeur", 42)\nfin\n');
    const jetons = await vscode.commands.executeCommand("_workbench.captureSyntaxTokens", document.uri);
    const portee = (texte) => {
      const j = jetons.find((x) => x.c.trim() === texte);
      return j ? j.t : `(introuvable : ${texte})`;
    };
    assert.match(portee("si"), /keyword\.control\.kplus/);
    assert.match(portee("alors"), /keyword\.control\.kplus/);
    assert.match(portee("afficher"), /support\.function\.builtin\.kplus/);
    assert.match(portee('"Tu es majeur"'), /string\.quoted\.double\.kplus/);
    assert.match(portee("42"), /constant\.numeric/);
    assert.match(portee("majeur"), /comment\.line/);
  });

  await cas("raccourcis d'écriture (snippets) proposés", async () => {
    const { document } = await ouvrir(dossier, "snippets.kplus", "si");
    const liste = await vscode.commands.executeCommand("vscode.executeCompletionItemProvider",
      document.uri, new vscode.Position(0, 2));
    const extraits = liste.items.filter((i) => i.kind === vscode.CompletionItemKind.Snippet)
      .map((i) => (typeof i.label === "string" ? i.label : i.label.label));
    for (const attendu of ["si", "sisinon"]) assert.ok(extraits.includes(attendu), extraits.join(", "));
  });

  await cas("retrait automatique après « alors »", async () => {
    const { document, editeur } = await ouvrir(dossier, "retrait.kplus", "si vrai alors");
    editeur.selection = new vscode.Selection(0, 13, 0, 13);
    await vscode.commands.executeCommand("type", { text: "\n" });
    assert.strictEqual(document.lineAt(1).text, "    ");
  });

  await cas("Ctrl+/ commente la ligne avec #", async () => {
    const { document, editeur } = await ouvrir(dossier, "commentaire.kplus", "afficher(1)\n");
    editeur.selection = new vscode.Selection(0, 0, 0, 0);
    await vscode.commands.executeCommand("editor.action.commentLine");
    assert.strictEqual(document.lineAt(0).text, "# afficher(1)");
  });

  await cas("bouton Exécuter : le programme tourne dans le terminal K+", async () => {
    const { fichier } = await ouvrir(dossier, "execution.kplus", "");
    fs.writeFileSync(fichier,
      'afficher("Bonjour depuis VS Code", 6 * 7)\n', "utf8");
    const document = await vscode.workspace.openTextDocument(fichier);
    await vscode.window.showTextDocument(document);
    const sorties = [];
    const ecoute = vscode.window.onDidStartTerminalShellExecution(async (e) => {
      let texte = "";
      for await (const morceau of e.execution.read()) texte += morceau;
      sorties.push(texte);
    });
    await vscode.commands.executeCommand("kplus.executer");
    const terminal = await attendre(() => vscode.window.terminals.find((t) => t.name === "K+"),
                                    "terminal K+");
    assert.ok(terminal);
    // Lecture de la sortie si l'intégration du terminal est disponible.
    try {
      await attendre(() => sorties.some((s) => s.includes("Bonjour depuis VS Code 42")),
                     "sortie du programme", 20000);
    } catch (e) {
      if (terminal.shellIntegration) throw e;
      console.log("       (intégration du terminal indisponible : sortie non lue, terminal créé)");
    } finally {
      ecoute.dispose();
    }
  });

  if (process.env.KPLUS_CAPTURE) {
    const { document, editeur } = await ouvrir(dossier, "demonstration.kplus", [
      "# Calcul d'une moyenne",
      "fonction moyenne(notes)",
      "    variable total = 0",
      "    pour chaque n dans notes faire",
      "        total = total + n",
      "    fin",
      "    retourner total / longueur(notes)",
      "fin",
      "",
      "variable notes = [12, 15, 18]",
      "si moyenne(notes) >= 10 alors",
      '    afficher("Admis avec", moyenne(notes))',
      "",
    ].join("\n"));
    await attendre(() => diagnostics(document).length, "diagnostic de démonstration");
    const d = diagnostics(document)[0];
    editeur.selection = new vscode.Selection(d.range.start, d.range.start);
    await vscode.commands.executeCommand("editor.action.showHover");
    await pause(2500);
    require("child_process").execFileSync("import", ["-window", "root", process.env.KPLUS_CAPTURE]);
    console.log("Capture enregistrée :", process.env.KPLUS_CAPTURE);
  }

  const echecs = resultats.filter((r) => !r).length;
  console.log(`\n${resultats.length - echecs}/${resultats.length} vérifications réussies dans VS Code.`);
  if (echecs) throw new Error(`${echecs} vérification(s) en échec`);
};
