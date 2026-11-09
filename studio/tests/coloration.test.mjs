// Tests de la coloration syntaxique (node --test studio/tests/)
import { test } from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { decouper, colorer_lignes } = require("../coloration.js");

const types = (source) => decouper(source).filter((m) => m.type !== "espace")
  .map((m) => `${m.type}:${m.texte}`);

test("mots-clés, noms, nombres, valeurs", () => {
  assert.deepEqual(types("si âge >= 18 alors"),
    ["motcle:si", "nom:âge", "symbole:>=", "nombre:18", "motcle:alors"]);
  assert.deepEqual(types("vrai faux nul arrêter a à"),
    ["valeur:vrai", "valeur:faux", "valeur:nul", "motcle:arrêter", "nom:a", "motcle:à"]);
  assert.deepEqual(types("1_000 3.14 1.5e3 6e-2"),
    ["nombre:1_000", "nombre:3.14", "nombre:1.5e3", "nombre:6e-2"]);
});

test("textes et échappements", () => {
  assert.deepEqual(types('afficher("a\\"b # pas commentaire")'),
    ["native:afficher", "symbole:(", 'texte:"a\\"b # pas commentaire"', "symbole:)"]);
  assert.deepEqual(types("“dit \"oui\"”"), ['texte:“dit "oui"”']);
  assert.deepEqual(types('"non fermé\nx'), ['texte:"non fermé', "nom:x"]);
});

test("commentaires", () => {
  assert.deepEqual(types("x # fin\ny"), ["nom:x", "commentaire:# fin", "nom:y"]);
  assert.deepEqual(colorer_lignes("x /* a\nb */ y"),
    ['x <span class="k-commentaire">/* a</span>', '<span class="k-commentaire">b */</span> y']);
});

test("une ligne HTML par ligne de code, HTML échappé", () => {
  const lignes = colorer_lignes('si a < b alors\n\nafficher("<b>")\n');
  assert.equal(lignes.length, 4);
  assert.equal(lignes[1], "");
  assert.ok(lignes[2].includes("&lt;b&gt;"));
  assert.ok(!lignes[2].includes("<b>"));
});

test("caractère inconnu signalé", () => {
  assert.deepEqual(types("x @ 2"), ["nom:x", "inconnu:@", "nombre:2"]);
});
