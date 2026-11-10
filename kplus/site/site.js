/*
 * Site créé avec le langage K+ (« kplus --site »).
 * Le programme K+ tourne dans travailleur.js (moteur K+ + Pyodide) ;
 * ce fichier affiche la page (rendu_web.js) et transmet les événements.
 */
(function () {
  "use strict";
  const chargement = document.getElementById("kp-chargement");
  const travailleur = new Worker("travailleur.js");
  let requete = 0;
  const enAttente = new Map();

  const rendu = KPlusRendu.creerRendu(document.getElementById("kp-page"), {
    surTitre: (t) => { document.title = t; },
    surEvenement: (id, genre, valeurs) => new Promise((fin) => {
      requete += 1;
      enAttente.set(requete, fin);
      travailleur.postMessage({ type: "evenement", id, genre, valeurs, requete });
    }),
  });

  travailleur.onmessage = (e) => {
    const m = e.data;
    if (m.type === "sortie") {
      console.log(m.texte.replace(/\n$/, ""));
    } else if (m.type === "demarre") {
      chargement.remove();
      rendu.appliquer(m.resultat.commandes || []);
      if (m.resultat.erreur) {
        rendu.appliquer([{ op: "erreur", texte: m.resultat.erreur.texte }]);
        console.error(m.resultat.erreur.texte);
      }
    } else if (m.type === "evenement_fin") {
      rendu.appliquer(m.resultat.commandes || []);
      if (m.resultat.texte_erreur) console.error(m.resultat.texte_erreur);
      const fin = enAttente.get(m.requete);
      enAttente.delete(m.requete);
      if (fin) fin();
    } else if (m.type === "echec") {
      chargement.textContent = "Impossible de charger le site : " + m.message +
        ". Vérifiez la connexion Internet, puis rechargez la page.";
    }
  };
  travailleur.postMessage({ type: "demarrer" });
})();
