// Tests des couleurs (grammaire TextMate) avec le moteur de coloration de VS Code.
// Utilisation : node --test vscode/tests/grammaire.test.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";

const require = createRequire(import.meta.url);
const vsctm = require("vscode-textmate");
const oniguruma = require("vscode-oniguruma");

const ICI = path.dirname(new URL(import.meta.url).pathname);
const wasm = readFileSync(require.resolve("vscode-oniguruma/release/onig.wasm")).buffer;
await oniguruma.loadWASM(wasm);

const registre = new vsctm.Registry({
  onigLib: Promise.resolve({
    createOnigScanner: (s) => new oniguruma.OnigScanner(s),
    createOnigString: (s) => new oniguruma.OnigString(s),
  }),
  loadGrammar: async () => vsctm.parseRawGrammar(
    readFileSync(path.join(ICI, "../syntaxes/kplus.tmLanguage.json"), "utf8"), "kplus.tmLanguage.json"),
});
const grammaire = await registre.loadGrammar("source.kplus");

/** Renvoie [[texte, portée la plus précise], ...] pour chaque morceau non blanc. */
function colorer(source) {
  let pile = vsctm.INITIAL;
  const resultat = [];
  for (const ligne of source.split("\n")) {
    const r = grammaire.tokenizeLine(ligne, pile);
    for (const j of r.tokens) {
      const texte = ligne.slice(j.startIndex, j.endIndex);
      if (texte.trim()) resultat.push([texte.trim(), j.scopes[j.scopes.length - 1]]);
    }
    pile = r.ruleStack;
  }
  return resultat;
}
const portee = (source, morceau) => {
  const trouve = colorer(source).find(([t]) => t === morceau);
  return trouve && trouve[1];
};

test("mots-clés et déclarations", () => {
  const s = "si age >= 18 alors\nsinon\nfin\nvariable x = 1\nconstante PI = 3.14";
  assert.equal(portee(s, "si"), "keyword.control.kplus");
  assert.equal(portee(s, "alors"), "keyword.control.kplus");
  assert.equal(portee(s, "fin"), "keyword.control.kplus");
  assert.equal(portee(s, "variable"), "storage.type.kplus");
  assert.equal(portee(s, "constante"), "storage.type.kplus");
  assert.equal(portee(s, ">="), "keyword.operator.comparison.kplus");
});

test("noms accentués : pas de faux mot-clé", () => {
  // « année » contient « an » ; « finale » commence par « fin » ; « sinon_x » par « sinon ».
  for (const nom of ["finale", "sinon_x", "année", "désir", "àpropos", "pass"]) {
    const morceaux = colorer(`variable ${nom} = 1`);
    assert.ok(morceaux.some(([t, p]) => t === nom && p === "source.kplus"), `${nom} : ${JSON.stringify(morceaux)}`);
  }
  assert.equal(portee("pour i de 1 à 3 faire", "à"), "keyword.control.kplus");
  assert.equal(portee("arrêter", "arrêter"), "keyword.control.kplus");
});

test("fonctions", () => {
  const s = "fonction additionner(a, b)\n    retourner a + b\nfin\nafficher(additionner(1, 2))";
  assert.equal(portee(s, "fonction"), "storage.type.function.kplus");
  assert.equal(portee(s, "additionner"), "entity.name.function.kplus");
  assert.equal(portee(s, "retourner"), "keyword.control.kplus");
  assert.equal(portee(s, "afficher"), "support.function.builtin.kplus");
  assert.equal(portee("variable r = maFonction(2)", "maFonction"), "entity.name.function.call.kplus");
});

test("valeurs et nombres", () => {
  const s = "variable v = [vrai, faux, nul, 42, 3.14, 1_000, 1.5e3]";
  assert.equal(portee(s, "vrai"), "constant.language.kplus");
  assert.equal(portee(s, "nul"), "constant.language.kplus");
  assert.equal(portee(s, "42"), "constant.numeric.integer.kplus");
  assert.equal(portee(s, "3.14"), "constant.numeric.decimal.kplus");
  assert.equal(portee(s, "1_000"), "constant.numeric.integer.kplus");
  assert.equal(portee(s, "1.5e3"), "constant.numeric.decimal.kplus");
});

test("textes, échappements, guillemets typographiques", () => {
  const morceaux = colorer('afficher("a\\nb # pas commentaire", “dit "oui"”)');
  assert.ok(morceaux.some(([t, p]) => t === "\\n" && p === "constant.character.escape.kplus"));
  assert.ok(morceaux.some(([t, p]) => t.includes("# pas commentaire") && p === "string.quoted.double.kplus"));
  assert.ok(morceaux.some(([t, p]) => t.includes('dit "oui"') && p === "string.quoted.other.typographic.kplus"));
  assert.ok(!morceaux.some(([, p]) => p.startsWith("comment")));
});

test("commentaires sur une et plusieurs lignes", () => {
  const s = "x = 1 # fin de ligne\n/* bloc\nsi alors fin\n*/ afficher(x)";
  const m = colorer(s);
  assert.ok(m.some(([t, p]) => t === "fin de ligne" && p === "comment.line.number-sign.kplus"));
  assert.ok(m.some(([t, p]) => t === "si alors fin" && p === "comment.block.kplus"));
  assert.equal(m.find(([t]) => t === "afficher")[1], "support.function.builtin.kplus");
});

test("caractères interdits signalés", () => {
  assert.equal(portee("x = 5 @ 2", "@"), "invalid.illegal.character.kplus");
  assert.equal(portee("x = 1;", ";"), "invalid.illegal.character.kplus");
});
