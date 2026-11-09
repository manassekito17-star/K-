/*
 * K+ Studio — interface.
 *
 * L'exécution réelle est faite par le moteur K+ dans travailleur.js ;
 * ce fichier gère l'éditeur, la console et les boutons.
 */
(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const code = $("code");
  const coloration = $("coloration");
  const numeros = $("numeros");
  const consoleSortie = $("console");
  const diagnostic = $("diagnostic");
  const etatMoteur = $("etat-moteur");
  const position = $("position");
  const nomFichier = $("nom-fichier");
  const entrees = $("entrees");
  const blocEntrees = $("bloc-entrees");
  const boutonExecuter = $("bouton-executer");
  const boutonArreter = $("bouton-arreter");
  const choixExemple = $("choix-exemple");
  const fichier = $("fichier");

  const HAUTEUR_LIGNE = 21;
  const CONSOLE_MAX = 500000;          // caractères affichés au maximum
  const CLES = { code: "kplus-studio-code", nom: "kplus-studio-nom", entrees: "kplus-studio-entrees" };

  const PROGRAMME_ACCUEIL = [
    "# Bienvenue dans K+ Studio !",
    "# Écrivez votre programme, puis cliquez sur « Exécuter » (ou Ctrl+Entrée).",
    "",
    'afficher("Bienvenue dans K+")',
    "",
    'variable nom = "Manassé"',
    "variable age = 20",
    "",
    "si age >= 18 alors",
    '    afficher("Tu es majeur")',
    "sinon",
    '    afficher("Tu es mineur")',
    "fin",
    "",
    "fonction additionner(a, b)",
    "    retourner a + b",
    "fin",
    "",
    "variable resultat = additionner(10, 20)",
    "afficher(resultat)",
    "",
  ].join("\n");

  let travailleur = null;
  let pret = false;
  let enCours = false;
  let ligneErreur = null;
  let numeroVerification = 0;
  let minuteurVerification = null;
  let minuteurSauvegarde = null;
  let contenuReference = "";           // dernier contenu ouvert ou enregistré
  let caracteresConsole = 0;
  let consoleTronquee = false;
  let manifeste = { exemples: [] };

  // --- Stockage local (facultatif : peut être indisponible) -----------------

  function lireStockage(cle) {
    try { return window.localStorage.getItem(cle); } catch (e) { return null; }
  }
  function ecrireStockage(cle, valeur) {
    try { window.localStorage.setItem(cle, valeur); } catch (e) { /* ignoré */ }
  }
  function sauvegarderPlusTard() {
    clearTimeout(minuteurSauvegarde);
    minuteurSauvegarde = setTimeout(() => {
      ecrireStockage(CLES.code, code.value);
      ecrireStockage(CLES.nom, nomFichier.textContent);
      ecrireStockage(CLES.entrees, entrees.value);
    }, 300);
  }

  // --- Éditeur ----------------------------------------------------------------

  function rendre() {
    const lignes = KPlusColoration.colorer_lignes(code.value);
    coloration.innerHTML = lignes
      .map((html, i) => `<span class="ligne${i + 1 === ligneErreur ? " erreur" : ""}">${html}</span>`)
      .join("") + '<span class="ligne" style="height:50vh"></span>';
    const numerosHtml = [];
    for (let i = 1; i <= lignes.length; i++) {
      numerosHtml.push(i === ligneErreur ? `<span class="erreur">${i}</span>` : String(i));
    }
    numeros.innerHTML = numerosHtml.join("\n") + "\n" + "\n".repeat(40);
    synchroniserDefilement();
  }

  function synchroniserDefilement() {
    coloration.scrollTop = code.scrollTop;
    coloration.scrollLeft = code.scrollLeft;
    numeros.scrollTop = code.scrollTop;
  }

  function mettreAJourPosition() {
    const avant = code.value.slice(0, code.selectionStart);
    const ligne = avant.split("\n").length;
    const colonne = avant.length - avant.lastIndexOf("\n");
    position.textContent = `Ligne ${ligne}, colonne ${colonne}`;
  }

  function inserer(texte) {
    // execCommand conserve l'historique d'annulation (Ctrl+Z) du navigateur.
    if (!document.execCommand || !document.execCommand("insertText", false, texte)) {
      code.setRangeText(texte, code.selectionStart, code.selectionEnd, "end");
      surModification();
    }
  }

  const OUVRE_UN_BLOC = /(^|\s)(alors|faire|sinon|essayer)\s*$|^\s*attraper(\s+\S+)?\s*$|^\s*fonction\s.*\)\s*$/;

  function retraitApres(ligne) {
    const sansCommentaire = ligne.replace(/#.*$/, "");
    const retrait = ligne.match(/^[ \t]*/)[0];
    return OUVRE_UN_BLOC.test(sansCommentaire) ? retrait + "    " : retrait;
  }

  let tabulationLibre = false;         // après Échap, Tab quitte l'éditeur

  code.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      executer();
      return;
    }
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") {
      e.preventDefault();
      enregistrer();
      return;
    }
    if (e.key === "Escape") { tabulationLibre = true; return; }
    if (e.key === "Tab" && !tabulationLibre && !e.ctrlKey && !e.altKey) {
      e.preventDefault();
      const debut = code.value.lastIndexOf("\n", code.selectionStart - 1) + 1;
      if (e.shiftKey) {
        const retrait = code.value.slice(debut).match(/^ {1,4}/);
        if (retrait) {
          code.setSelectionRange(debut, debut + retrait[0].length);
          inserer("");
        }
      } else {
        inserer("    ");
      }
      return;
    }
    tabulationLibre = false;
    if (e.key === "Enter" && !e.shiftKey && !e.altKey) {
      e.preventDefault();
      const debut = code.value.lastIndexOf("\n", code.selectionStart - 1) + 1;
      inserer("\n" + retraitApres(code.value.slice(debut, code.selectionStart)));
    }
  });

  function surModification() {
    rendre();
    mettreAJourPosition();
    programmerVerification(350);
    sauvegarderPlusTard();
  }

  code.addEventListener("input", surModification);
  code.addEventListener("scroll", synchroniserDefilement);
  ["keyup", "click", "select"].forEach((t) => code.addEventListener(t, mettreAJourPosition));
  entrees.addEventListener("input", sauvegarderPlusTard);

  function allerALigne(numero) {
    const lignes = code.value.split("\n");
    if (numero < 1 || numero > lignes.length) return;
    let debut = 0;
    for (let i = 0; i < numero - 1; i++) debut += lignes[i].length + 1;
    code.focus();
    code.setSelectionRange(debut, debut + lignes[numero - 1].length);
    code.scrollTop = Math.max(0, (numero - 1) * HAUTEUR_LIGNE - code.clientHeight / 2);
    synchroniserDefilement();
    mettreAJourPosition();
  }

  function remplacerProgramme(texte, nom) {
    code.value = texte;
    nomFichier.textContent = nom;
    contenuReference = texte;
    ligneErreur = null;
    code.scrollTop = 0;
    code.setSelectionRange(0, 0);
    surModification();
  }

  function modifie() {
    return code.value !== contenuReference && code.value.trim() !== "";
  }

  // --- Vérification pendant la saisie --------------------------------------------

  function programmerVerification(delai) {
    clearTimeout(minuteurVerification);
    minuteurVerification = setTimeout(() => {
      if (!pret || enCours) return;
      numeroVerification += 1;
      travailleur.postMessage({ type: "verifier", id: numeroVerification, source: code.value });
    }, delai);
  }

  function afficherVerification(resultat) {
    if (resultat.ok) {
      diagnostic.textContent = "✓ Aucune erreur de syntaxe";
      diagnostic.className = "diagnostic ok";
      diagnostic.title = "";
      diagnostic.onclick = null;
      ligneErreur = null;
    } else {
      const e = resultat.erreur;
      diagnostic.textContent = `${e.nom}, ligne ${e.ligne} : ${e.message}`;
      diagnostic.className = "diagnostic erreur";
      diagnostic.title = e.texte;
      diagnostic.onclick = () => allerALigne(e.ligne);
      ligneErreur = e.ligne;
    }
    rendre();
  }

  // --- Console --------------------------------------------------------------------

  function ajouterConsole(texte, genre) {
    if (consoleTronquee) return;
    if (caracteresConsole + texte.length > CONSOLE_MAX) {
      consoleTronquee = true;
      texte = "\n[Affichage limité : la console ne montre que les 500 000 premiers caractères.]\n";
      genre = "systeme";
    }
    caracteresConsole += texte.length;
    const enBas = consoleSortie.scrollHeight - consoleSortie.scrollTop - consoleSortie.clientHeight < 40;
    const dernier = consoleSortie.lastChild;
    if (dernier && dernier.dataset && dernier.dataset.genre === genre && genre !== "erreur") {
      dernier.textContent += texte;
    } else {
      const span = document.createElement("span");
      span.className = genre;
      span.dataset.genre = genre;
      span.textContent = texte;
      consoleSortie.appendChild(span);
    }
    if (enBas) consoleSortie.scrollTop = consoleSortie.scrollHeight;
  }

  function ajouterLigneSysteme(texte) {
    const fin = consoleSortie.textContent;
    ajouterConsole((fin && !fin.endsWith("\n") ? "\n" : "") + texte + "\n", "systeme");
  }

  function afficherErreur(erreur) {
    const fin = consoleSortie.textContent;
    if (fin && !fin.endsWith("\n")) ajouterConsole("\n", "sortie");
    ajouterConsole(erreur.texte + "\n", "erreur");
    if (erreur.ligne) {
      const bouton = document.createElement("button");
      bouton.type = "button";
      bouton.className = "lien-ligne";
      bouton.textContent = `→ Aller à la ligne ${erreur.ligne}`;
      bouton.addEventListener("click", () => allerALigne(erreur.ligne));
      consoleSortie.appendChild(bouton);
      consoleSortie.appendChild(document.createTextNode("\n"));
    }
  }

  function viderConsole() {
    consoleSortie.textContent = "";
    caracteresConsole = 0;
    consoleTronquee = false;
  }

  // --- Moteur (travailleur) ---------------------------------------------------------

  function changerEtat(texte, classe) {
    etatMoteur.textContent = texte;
    etatMoteur.className = classe || "";
  }

  function mettreAJourBoutons() {
    boutonExecuter.disabled = !pret || enCours;
    boutonArreter.disabled = !enCours;
  }

  function demarrerMoteur() {
    pret = false;
    mettreAJourBoutons();
    changerEtat("Chargement du moteur K+… (le premier lancement télécharge Python, environ 10 Mo)", "occupe");
    travailleur = new Worker("travailleur.js");
    travailleur.onmessage = (e) => recevoir(e.data);
    travailleur.onerror = (e) => {
      changerEtat(`Erreur du moteur : ${e.message || "inconnue"}`, "echec");
    };
  }

  function recevoir(message) {
    switch (message.type) {
      case "pret":
        pret = true;
        changerEtat(`Moteur K+ ${message.version} prêt`, "pret");
        mettreAJourBoutons();
        programmerVerification(0);
        break;
      case "echec":
        changerEtat(`Impossible de charger le moteur K+ : ${message.message}. ` +
                    "Vérifiez la connexion Internet, puis rechargez la page.", "echec");
        break;
      case "verification":
        if (message.id === numeroVerification) afficherVerification(message.resultat);
        break;
      case "flux":
        ajouterConsole(message.texte, message.genre);
        break;
      case "fin":
        terminerExecution(message.resultat);
        break;
    }
  }

  function executer() {
    if (!pret || enCours) return;
    viderConsole();
    enCours = true;
    ligneErreur = null;
    rendre();
    mettreAJourBoutons();
    changerEtat("Exécution en cours…", "occupe");
    travailleur.postMessage({ type: "executer", source: code.value, entree: entrees.value });
  }

  function terminerExecution(resultat) {
    enCours = false;
    mettreAJourBoutons();
    if (resultat.statut === "erreur") {
      afficherErreur(resultat.erreur);
      ligneErreur = resultat.erreur.ligne;
      rendre();
      ajouterLigneSysteme(`Programme arrêté par une erreur (${resultat.duree_ms} ms).`);
    } else if (resultat.statut === "interne") {
      ajouterLigneSysteme(`Erreur interne de K+ (bogue à signaler) : ${resultat.message}`);
    } else {
      ajouterLigneSysteme(`Programme terminé (${resultat.duree_ms} ms).`);
    }
    changerEtat("Moteur K+ prêt", "pret");
  }

  function arreter() {
    if (!enCours) return;
    travailleur.terminate();
    enCours = false;
    ajouterLigneSysteme("Programme arrêté par l'utilisateur.");
    demarrerMoteur();
  }

  // --- Fichiers et exemples ------------------------------------------------------------

  function nouveau() {
    if (modifie() && !window.confirm("Effacer le programme actuel ?")) return;
    remplacerProgramme("", "programme.kplus");
    code.focus();
  }

  function enregistrer() {
    let nom = window.prompt("Nom du fichier :", nomFichier.textContent);
    if (nom === null) return;
    nom = nom.trim() || "programme.kplus";
    if (!nom.toLowerCase().endsWith(".kplus")) nom += ".kplus";
    const lien = document.createElement("a");
    lien.href = URL.createObjectURL(new Blob([code.value], { type: "text/plain;charset=utf-8" }));
    lien.download = nom;
    document.body.appendChild(lien);
    lien.click();
    lien.remove();
    setTimeout(() => URL.revokeObjectURL(lien.href), 1000);
    nomFichier.textContent = nom;
    contenuReference = code.value;
    sauvegarderPlusTard();
  }

  fichier.addEventListener("change", async () => {
    const choisi = fichier.files[0];
    fichier.value = "";
    if (!choisi) return;
    if (modifie() && !window.confirm("Remplacer le programme actuel ?")) return;
    remplacerProgramme(await choisi.text(), choisi.name);
  });

  async function chargerManifeste() {
    try {
      const reponse = await fetch("manifeste.json", { cache: "no-cache" });
      manifeste = await reponse.json();
      for (const exemple of manifeste.exemples) {
        const option = document.createElement("option");
        option.value = exemple.nom;
        option.textContent = exemple.titre;
        choixExemple.appendChild(option);
      }
    } catch (e) {
      choixExemple.disabled = true;
    }
  }

  choixExemple.addEventListener("change", async () => {
    const nom = choixExemple.value;
    choixExemple.value = "";
    if (!nom) return;
    if (modifie() && !window.confirm("Remplacer le programme actuel par l'exemple ?")) return;
    const exemple = manifeste.exemples.find((x) => x.nom === nom);
    const reponse = await fetch(`exemples/${nom}.kplus`, { cache: "no-cache" });
    remplacerProgramme(await reponse.text(), `${nom}.kplus`);
    if (exemple && exemple.entree) {
      entrees.value = exemple.entree;
      blocEntrees.open = true;
      sauvegarderPlusTard();
    }
  });

  // --- Boutons ----------------------------------------------------------------------------

  boutonExecuter.addEventListener("click", executer);
  boutonArreter.addEventListener("click", arreter);
  $("bouton-nouveau").addEventListener("click", nouveau);
  $("bouton-ouvrir").addEventListener("click", () => fichier.click());
  $("bouton-enregistrer").addEventListener("click", enregistrer);
  $("bouton-effacer").addEventListener("click", viderConsole);

  // --- Démarrage --------------------------------------------------------------------------

  const codeSauvegarde = lireStockage(CLES.code);
  code.value = codeSauvegarde !== null ? codeSauvegarde : PROGRAMME_ACCUEIL;
  nomFichier.textContent = lireStockage(CLES.nom) || "programme.kplus";
  entrees.value = lireStockage(CLES.entrees) || "";
  if (entrees.value) blocEntrees.open = true;
  contenuReference = code.value;
  rendre();
  mettreAJourPosition();
  chargerManifeste();
  demarrerMoteur();
})();
