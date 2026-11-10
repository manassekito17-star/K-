/*
 * Travailleur (Web Worker) de K+ Studio.
 *
 * Il fait tourner Pyodide (Python dans le navigateur) et le VRAI moteur K+
 * (fichiers kplus/*.py copiés par construire.py). Il tourne à part de la
 * page : un programme long ou infini ne fige pas l'interface, et le bouton
 * « Arrêter » peut le terminer à tout moment.
 *
 * Messages reçus :  { type: "verifier", id, source }
 *                   { type: "executer", source, entree }
 * Messages envoyés : { type: "pret", version } | { type: "echec", message }
 *                    { type: "verification", id, resultat }
 *                    { type: "flux", genre, texte } | { type: "fin", resultat }
 */
"use strict";

const VERSION_PYODIDE = "0.27.7";
const URL_PYODIDE = `https://cdn.jsdelivr.net/npm/pyodide@${VERSION_PYODIDE}/`;

let pont = null;
const file_attente = [];

async function lire_texte(chemin) {
  const reponse = await fetch(chemin, { cache: "no-cache" });
  if (!reponse.ok) throw new Error(`impossible de charger ${chemin} (${reponse.status})`);
  return reponse.text();
}

async function initialiser() {
  try {
    importScripts(URL_PYODIDE + "pyodide.js");
    const pyodide = await loadPyodide({ indexURL: URL_PYODIDE });
    const manifeste = JSON.parse(await lire_texte("manifeste.json"));
    pyodide.FS.mkdirTree("/kplus_studio/kplus");
    for (const fichier of manifeste.moteur) {
      pyodide.FS.writeFile(`/kplus_studio/kplus/${fichier}`, await lire_texte(`kplus/${fichier}`));
    }
    pyodide.FS.writeFile("/kplus_studio/pont.py", await lire_texte("pont.py"));
    pyodide.runPython("import sys; sys.path.insert(0, '/kplus_studio')");
    pont = pyodide.pyimport("pont");
    postMessage({ type: "pret", version: pont.version() });
    while (file_attente.length) traiter(file_attente.shift());
  } catch (erreur) {
    postMessage({ type: "echec", message: String(erreur && erreur.message || erreur) });
  }
}

function traiter(message) {
  if (message.type === "verifier") {
    const resultat = JSON.parse(pont.verifier(message.source));
    postMessage({ type: "verification", id: message.id, resultat });
  } else if (message.type === "executer") {
    const envoyer = (genre, texte) => postMessage({ type: "flux", genre, texte });
    let resultat;
    try {
      resultat = JSON.parse(pont.executer(message.source, message.entree, envoyer));
    } catch (erreur) {
      // Ne devrait jamais arriver : ce serait un bogue du moteur ou de Pyodide.
      resultat = { statut: "interne", message: String(erreur && erreur.message || erreur) };
    }
    postMessage({ type: "fin", resultat });
  } else if (message.type === "evenement") {
    // Clic, saisie ou minuterie sur une page K+ Web.
    const envoyer = (genre, texte) => postMessage({ type: "flux", genre, texte });
    let resultat;
    try {
      resultat = JSON.parse(pont.evenement(message.id, message.genre,
                                           JSON.stringify(message.valeurs || {}), envoyer));
    } catch (erreur) {
      resultat = { statut: "interne", commandes: [], texte_erreur: String(erreur && erreur.message || erreur) };
    }
    postMessage({ type: "evenement_fin", requete: message.requete, resultat });
  }
}

onmessage = (evenement) => {
  if (pont === null) file_attente.push(evenement.data);
  else traiter(evenement.data);
};

initialiser();
