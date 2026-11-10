/*
 * Affichage des pages K+ Web dans le navigateur.
 *
 * Le moteur K+ (kplus/web.py) produit des COMMANDES ; ce fichier les applique
 * à la page et renvoie les événements (clics, saisies, minuteries). Il est
 * utilisé par K+ Studio (onglet Page) et par les sites créés avec
 * « kplus --site ».
 *
 * Sécurité : les textes sont toujours insérés avec textContent (jamais comme
 * du HTML) ; les adresses et les couleurs ont déjà été vérifiées par le moteur.
 */
(function (racine) {
  "use strict";

  const BALISES = {
    titre: "h1", sous_titre: "h2", paragraphe: "p", bouton: "button",
    liste: "ul", ligne: "li", image: "img", lien: "a", zone: "div",
  };
  const PROPRIETES_STYLE = new Set(["color", "background-color"]);

  const STYLES = `
.kp-page { font: 16px/1.5 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  color: #1d2330; background: #ffffff; padding: 16px; box-sizing: border-box;
  overflow-wrap: anywhere; }
.kp-page h1 { font-size: 1.6em; margin: 0 0 .5em; }
.kp-page h2 { font-size: 1.25em; margin: 1em 0 .4em; }
.kp-page p { margin: .4em 0; }
.kp-page button { font: inherit; padding: .4em 1em; margin: .3em .3em .3em 0; border-radius: 6px;
  border: 1px solid #2f5bd3; background: #2f5bd3; color: #fff; cursor: pointer; }
.kp-page button:hover { filter: brightness(1.1); }
.kp-page .kp-champ { display: flex; flex-direction: column; gap: .2em; margin: .5em 0; max-width: 420px; }
.kp-page .kp-champ input { font: inherit; padding: .4em .5em; border: 1px solid #b8bfcc; border-radius: 6px; }
.kp-page ul { padding-left: 1.4em; }
.kp-page li[data-kp-clic] { cursor: pointer; }
.kp-page img { max-width: 100%; height: auto; }
.kp-page a { color: #2f5bd3; }
.kp-page .kp-zone { border: 1px dashed #c8cfdb; border-radius: 8px; padding: .5em .8em; margin: .5em 0; }
.kp-page [data-kp-clic]:not(button) { cursor: pointer; }
.kp-page .kp-erreur { white-space: pre-wrap; font: 13px/1.4 ui-monospace, Menlo, Consolas, monospace;
  background: #fde8e7; color: #9b1c13; border: 1px solid #f1a39d; border-radius: 6px;
  padding: .5em .8em; margin: 0 0 .8em; }
`;

  function installerStyles(doc) {
    if (doc.getElementById("kp-styles")) return;
    const style = doc.createElement("style");
    style.id = "kp-styles";
    style.textContent = STYLES;
    doc.head.appendChild(style);
  }

  /**
   * Crée un afficheur dans `conteneur`.
   * options.surEvenement(id, genre, valeurs) : appelé à chaque événement ;
   *   peut renvoyer une promesse (une minuterie n'est pas relancée tant que
   *   son tour précédent n'est pas terminé).
   * options.surTitre(texte) : titre de la page (onglet du navigateur).
   */
  function creerRendu(conteneur, options = {}) {
    const doc = conteneur.ownerDocument;
    installerStyles(doc);
    conteneur.classList.add("kp-page");
    const noeuds = new Map();       // id -> élément affiché
    const champs = new Map();       // id -> <input>
    const minuteries = new Map();   // id -> identifiant setInterval
    const enCours = new Set();      // minuteries dont le tour n'est pas fini
    let bandeau = null;

    function valeursChamps() {
      const valeurs = {};
      for (const [id, entree] of champs) valeurs[id] = entree.value;
      return valeurs;
    }

    function signaler(id, genre) {
      if (!options.surEvenement) return;
      if (genre === "minuterie") {
        if (enCours.has(id)) return;
        enCours.add(id);
      }
      Promise.resolve(options.surEvenement(id, genre, valeursChamps()))
        .finally(() => enCours.delete(id));
    }

    function oublier(noeud) {
      for (const [id, n] of noeuds) {
        if (n === noeud || noeud.contains(n)) {
          noeuds.delete(id);
          champs.delete(id);
        }
      }
    }

    function creer(c) {
      let noeud;
      if (c.genre === "champ") {
        noeud = doc.createElement("label");
        noeud.className = "kp-champ";
        const etiquette = doc.createElement("span");
        etiquette.textContent = c.etiquette || "";
        const entree = doc.createElement("input");
        entree.type = "text";
        noeud.append(etiquette, entree);
        champs.set(c.id, entree);
      } else {
        noeud = doc.createElement(BALISES[c.genre] || "div");
        if (c.genre === "bouton") noeud.type = "button";
        if (c.genre === "zone") noeud.className = "kp-zone";
        if (c.genre === "image") {
          noeud.src = c.adresse;
          noeud.alt = c.description || "";
        } else {
          noeud.textContent = c.texte || "";
        }
        if (c.genre === "lien") {
          noeud.href = c.adresse;
          noeud.target = "_blank";
          noeud.rel = "noopener noreferrer";
        }
      }
      noeud.dataset.kp = c.id;
      noeuds.set(c.id, noeud);
      const parent = c.parent ? noeuds.get(c.parent) : null;
      (parent || conteneur).appendChild(noeud);
    }

    function appliquer(commandes) {
      for (const c of commandes) {
        const noeud = c.id ? noeuds.get(c.id) : null;
        switch (c.op) {
          case "creer": creer(c); break;
          case "texte": if (noeud) noeud.textContent = c.texte; break;
          case "valeur": if (champs.get(c.id)) champs.get(c.id).value = c.valeur; break;
          case "deplacer": {
            const parent = noeuds.get(c.parent);
            if (noeud && parent) parent.appendChild(noeud);
            break;
          }
          case "supprimer": if (noeud) { oublier(noeud); noeud.remove(); } break;
          case "vider":
            if (noeud) {
              for (const enfant of Array.from(noeud.children)) oublier(enfant);
              noeud.replaceChildren();
            }
            break;
          case "visible": if (noeud) noeud.hidden = !c.visible; break;
          case "style":
            if (noeud && PROPRIETES_STYLE.has(c.propriete)) noeud.style.setProperty(c.propriete, c.valeur);
            break;
          case "titre_page": if (options.surTitre) options.surTitre(c.texte); break;
          case "ecouter":
            if (!noeud) break;
            if (c.evenement === "clic") {
              noeud.dataset.kpClic = "1";
              noeud.addEventListener("click", (e) => {
                if (noeud.tagName === "A") return;           // un lien s'ouvre normalement
                e.stopPropagation();
                signaler(c.id, "clic");
              });
            } else if (c.evenement === "change" && champs.get(c.id)) {
              champs.get(c.id).addEventListener("input", () => signaler(c.id, "change"));
            }
            break;
          case "minuterie":
            minuteries.set(c.id, setInterval(() => signaler(c.id, "minuterie"), c.intervalle));
            break;
          case "arreter_minuterie":
            clearInterval(minuteries.get(c.id));
            minuteries.delete(c.id);
            break;
          case "erreur":
            if (!bandeau) {
              bandeau = doc.createElement("div");
              bandeau.className = "kp-erreur";
              bandeau.setAttribute("role", "alert");
            }
            bandeau.textContent = c.texte;
            conteneur.prepend(bandeau);
            break;
        }
      }
    }

    function arreterMinuteries() {
      for (const id of minuteries.values()) clearInterval(id);
      minuteries.clear();
      enCours.clear();
    }

    function vider() {
      arreterMinuteries();
      noeuds.clear();
      champs.clear();
      bandeau = null;
      conteneur.replaceChildren();
    }

    return { appliquer, vider, arreterMinuteries, valeursChamps, minuteriesActives: () => minuteries.size };
  }

  const api = { creerRendu };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else racine.KPlusRendu = api;
})(typeof window !== "undefined" ? window : globalThis);
