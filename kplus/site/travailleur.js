/*
 * Moteur du site : Pyodide (Python dans le navigateur) + moteur K+ + programme,
 * tous décrits dans moteur.json. Reçoit les événements de la page.
 */
"use strict";
const URL_PYODIDE = "https://cdn.jsdelivr.net/npm/pyodide@__PYODIDE__/";
let pont = null;
const attente = [];
const envoyer = (genre, texte) => postMessage({ type: "sortie", genre, texte });

async function demarrer() {
  try {
    importScripts(URL_PYODIDE + "pyodide.js");
    const pyodide = await loadPyodide({ indexURL: URL_PYODIDE });
    const paquet = await (await fetch("moteur.json")).json();
    pyodide.FS.mkdirTree("/site/kplus");
    for (const [nom, contenu] of Object.entries(paquet.fichiers)) pyodide.FS.writeFile("/site/" + nom, contenu);
    pyodide.runPython("import sys; sys.path.insert(0, '/site')");
    pont = pyodide.pyimport("kplus.pont");
    const resultat = JSON.parse(pont.executer(paquet.programme, "", envoyer));
    postMessage({ type: "demarre", resultat });
    while (attente.length) traiter(attente.shift());
  } catch (erreur) {
    postMessage({ type: "echec", message: String(erreur && erreur.message || erreur) });
  }
}

function traiter(m) {
  const resultat = JSON.parse(pont.evenement(m.id, m.genre, JSON.stringify(m.valeurs || {}), envoyer));
  postMessage({ type: "evenement_fin", requete: m.requete, resultat });
}

onmessage = (e) => {
  if (e.data.type === "demarrer") demarrer();
  else if (pont === null) attente.push(e.data);
  else traiter(e.data);
};
