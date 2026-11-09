/*
 * Coloration syntaxique du code K+ pour K+ Studio.
 *
 * Suit les règles lexicales de la spécification (§3). Les listes de mots-clés
 * et de fonctions natives sont comparées automatiquement à celles du moteur
 * (tests/test_studio.py) pour qu'elles ne divergent jamais.
 *
 * Utilisable dans le navigateur (window.KPlusColoration) et dans Node.js
 * (require("./coloration.js")) pour les tests.
 */
(function (racine) {
  "use strict";

  const MOTS_CLES = [
    "variable", "constante", "fonction", "retourner",
    "si", "alors", "sinon", "fin",
    "tant", "que", "faire", "pour", "chaque", "dans", "de", "à", "pas",
    "arreter", "arrêter", "continuer",
    "essayer", "attraper", "lever",
    "et", "ou", "non",
    "vrai", "faux", "nul",
    "utiliser",
  ];
  const VALEURS = new Set(["vrai", "faux", "nul"]);
  const NATIVES = [
    "afficher", "demander", "texte", "entier", "decimal", "décimal", "type",
    "longueur", "ajouter", "absolu", "racine", "arrondir", "quitter",
  ];
  const ENSEMBLE_MOTS_CLES = new Set(MOTS_CLES);
  const ENSEMBLE_NATIVES = new Set(NATIVES);

  const est_chiffre = (c) => c >= "0" && c <= "9";
  const est_debut_nom = (c) => c === "_" || /\p{L}/u.test(c);
  const est_suite_nom = (c) => c === "_" || est_chiffre(c) || /[\p{L}\p{M}]/u.test(c);

  /**
   * Découpe le texte en morceaux { type, texte }. Les types sont :
   * motcle, valeur, native, nom, nombre, texte, commentaire, symbole,
   * espace, inconnu. Ne lève jamais d'erreur : un texte non fermé est
   * coloré jusqu'à la fin de la ligne, comme le lexer le signalerait.
   */
  function decouper(source) {
    const morceaux = [];
    // Normalisation identique au moteur (NFC), sans changer les positions
    // visibles : on travaille caractère par caractère sur le texte NFC.
    const s = source.normalize("NFC");
    let i = 0;
    const n = s.length;
    const ajouter = (type, debut) => morceaux.push({ type, texte: s.slice(debut, i) });

    while (i < n) {
      const debut = i;
      const c = s[i];
      if (c === " " || c === "\t" || c === "\n" || c === "\r") {
        while (i < n && " \t\n\r".includes(s[i])) i++;
        ajouter("espace", debut);
      } else if (c === "#") {
        while (i < n && s[i] !== "\n") i++;
        ajouter("commentaire", debut);
      } else if (c === "/" && s[i + 1] === "*") {
        const fin = s.indexOf("*/", i + 2);
        i = fin === -1 ? n : fin + 2;
        ajouter("commentaire", debut);
      } else if (c === '"' || c === "“") {
        const fermant = c === '"' ? '"' : "”";
        i++;
        while (i < n && s[i] !== "\n") {
          if (s[i] === "\\" && i + 1 < n && s[i + 1] !== "\n") { i += 2; continue; }
          if (s[i] === fermant) { i++; break; }
          i++;
        }
        ajouter("texte", debut);
      } else if (est_chiffre(c)) {
        while (i < n && (est_chiffre(s[i]) || s[i] === "_")) i++;
        if (s[i] === "." && est_chiffre(s[i + 1] || "")) {
          i++;
          while (i < n && (est_chiffre(s[i]) || s[i] === "_")) i++;
        }
        if ((s[i] === "e" || s[i] === "E") &&
            (est_chiffre(s[i + 1] || "") ||
             ((s[i + 1] === "+" || s[i + 1] === "-") && est_chiffre(s[i + 2] || "")))) {
          i += 2;
          while (i < n && est_chiffre(s[i])) i++;
        }
        ajouter("nombre", debut);
      } else if (est_debut_nom(c)) {
        // Avancer par points de code (lettres hors du plan de base).
        while (i < n) {
          const cp = String.fromCodePoint(s.codePointAt(i));
          if (!est_suite_nom(cp)) break;
          i += cp.length;
        }
        const mot = s.slice(debut, i);
        let type = "nom";
        if (VALEURS.has(mot)) type = "valeur";
        else if (ENSEMBLE_MOTS_CLES.has(mot)) type = "motcle";
        else if (ENSEMBLE_NATIVES.has(mot)) type = "native";
        morceaux.push({ type, texte: mot });
      } else if ("()[],=+-*/%^<>!".includes(c)) {
        const deux = s.slice(i, i + 2);
        i += ["==", "!=", "<=", ">="].includes(deux) ? 2 : 1;
        ajouter("symbole", debut);
      } else {
        i += String.fromCodePoint(s.codePointAt(i)).length;
        ajouter("inconnu", debut);
      }
    }
    return morceaux;
  }

  function echapper(t) {
    return t.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  /**
   * Renvoie un tableau de lignes HTML colorées (une entrée par ligne du
   * source). Un morceau qui s'étend sur plusieurs lignes (commentaire /* *\/)
   * est découpé pour que chaque ligne reste un élément HTML complet.
   */
  function colorer_lignes(source) {
    const lignes = [""];
    for (const m of decouper(source)) {
      const parties = m.texte.split("\n");
      parties.forEach((partie, k) => {
        if (k > 0) lignes.push("");
        if (partie === "") return;
        const html = echapper(partie.replace(/\r/g, ""));
        lignes[lignes.length - 1] +=
          m.type === "espace" || m.type === "nom" ? html
            : `<span class="k-${m.type}">${html}</span>`;
      });
    }
    return lignes;
  }

  const api = { MOTS_CLES, NATIVES, decouper, colorer_lignes, echapper };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else racine.KPlusColoration = api;
})(typeof window !== "undefined" ? window : globalThis);
