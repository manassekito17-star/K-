"""Pont entre le navigateur et le moteur K+.

Ce module est chargé dans Pyodide (Python dans le navigateur) par K+ Studio
(studio/travailleur.js), par les sites créés avec « kplus --site » et par UPL
Code Académie. Il n'utilise que le moteur K+ réel : rien n'est simulé.
Il est aussi testé sous Python normal (tests/test_studio.py, tests/test_web.py).

Les résultats sont renvoyés en JSON pour passer facilement vers JavaScript.
"""

import json
import time

import kplus
from kplus.erreurs import ErreurKPlus, SignalQuitter, formater_erreur

TAILLE_PAQUET = 4096          # caractères envoyés d'un coup au navigateur
DELAI_PAQUET = 0.05           # secondes maximum avant d'envoyer
SORTIE_MAX = 1_000_000        # au-delà, la sortie est tronquée


def version() -> str:
    return kplus.__version__


def decrire_erreur(erreur: ErreurKPlus, source: str) -> dict:
    return {
        "categorie": erreur.categorie,
        "nom": erreur.nom_affiche,
        "message": erreur.message,
        "ligne": erreur.ligne,
        "colonne": erreur.colonne,
        "conseil": erreur.conseil,
        "pile": [{"fonction": nom, "ligne": ligne} for nom, ligne in erreur.pile],
        "texte": formater_erreur(erreur, source),
    }


def verifier(source: str) -> str:
    """Analyse le programme sans l'exécuter."""
    try:
        kplus.analyser(source)
    except ErreurKPlus as e:
        return json.dumps({"ok": False, "erreur": decrire_erreur(e, source)})
    return json.dumps({"ok": True})


class SortieStudio:
    """Reçoit ce qu'affiche le programme et l'envoie au navigateur par paquets."""

    def __init__(self, envoyer):
        self.envoyer = envoyer
        self.tampon = []
        self.taille_tampon = 0
        self.dernier_envoi = time.monotonic()
        self.total = 0
        self.tronquee = False

    def _ajouter(self, genre, texte):
        if self.tronquee:
            return
        if self.total + len(texte) > SORTIE_MAX:
            self.vider()
            self.tronquee = True
            self.envoyer("systeme", "\n[Sortie tronquée : plus d'un million de "
                                    "caractères affichés.]\n")
            return
        self.total += len(texte)
        if self.tampon and self.tampon[-1][0] == genre:
            self.tampon[-1][1].append(texte)
        else:
            self.tampon.append((genre, [texte]))
        self.taille_tampon += len(texte)
        maintenant = time.monotonic()
        if (self.taille_tampon >= TAILLE_PAQUET
                or maintenant - self.dernier_envoi >= DELAI_PAQUET):
            self.vider()

    def write(self, texte):
        self._ajouter("sortie", texte)
        return len(texte)

    def ecrire_entree(self, texte):
        self._ajouter("entree", texte)

    def flush(self):
        pass

    def vider(self):
        for genre, morceaux in self.tampon:
            self.envoyer(genre, "".join(morceaux))
        self.tampon = []
        self.taille_tampon = 0
        self.dernier_envoi = time.monotonic()


class EntreeStudio:
    """Réponses préparées par l'utilisateur dans le panneau « Entrée clavier ».

    Chaque réponse utilisée est réaffichée dans la console, comme si elle
    avait été tapée au clavier."""

    def __init__(self, texte, sortie: SortieStudio):
        self.lignes = texte.split("\n") if texte else []
        if self.lignes and self.lignes[-1] == "":
            self.lignes.pop()
        self.sortie = sortie

    def readline(self):
        if not self.lignes:
            return ""                     # fin des entrées : demander() renvoie nul
        ligne = self.lignes.pop(0)
        self.sortie.ecrire_entree(ligne + "\n")
        return ligne + "\n"


# Programme web en cours (« utiliser web ») : il reste vivant entre deux
# événements (clics, saisies, minuteries) pour garder ses variables.
_session = None
# Site côté serveur en cours (« utiliser serveur ») : [application, cookie, source].
_serveur = None
REDIRECTIONS_MAX = 5


def executer(source: str, entree: str, envoyer) -> str:
    """Analyse puis exécute le programme. `envoyer(genre, texte)` reçoit la
    sortie au fur et à mesure (genre : "sortie", "entree" ou "systeme").

    Pour un programme web, le résultat contient aussi "web": true et les
    "commandes" qui construisent la page (voir kplus/web.py)."""
    global _session, _serveur
    _session = None
    _serveur = None
    debut = time.monotonic()
    sortie = SortieStudio(envoyer)
    resultat = {"statut": "ok"}
    interpreteur = None
    try:
        programme = kplus.analyser(source)
        interpreteur = kplus.Interpreteur(sortie, EntreeStudio(entree, sortie))
        interpreteur.executer_programme(programme)
    except ErreurKPlus as e:
        resultat = {"statut": "erreur", "erreur": decrire_erreur(e, source)}
    except SignalQuitter:
        pass
    finally:
        sortie.vider()
    if interpreteur is not None and interpreteur.page is not None:
        resultat["web"] = True
        resultat["commandes"] = interpreteur.page.prendre_commandes()
        _session = (interpreteur, source)
    if interpreteur is not None and interpreteur.serveur is not None and resultat["statut"] == "ok":
        _serveur = [interpreteur.serveur, None, source]
        resultat["serveur"] = True
        resultat["pages"] = [r.adresse for r in interpreteur.serveur.pages]
        adresse = "/" if any(r.correspond("/") is not None for r in interpreteur.serveur.pages) \
            else (resultat["pages"] or ["/"])[0]
        resultat["visite"] = _visiter("GET", adresse, b"")
    resultat["duree_ms"] = round((time.monotonic() - debut) * 1000)
    return json.dumps(resultat)


def evenement(identifiant: str, genre: str, valeurs: str, envoyer) -> str:
    """Transmet un événement de la page (clic, change, minuterie) au programme
    web en cours. `valeurs` : JSON du contenu actuel des champs."""
    from kplus import web
    if _session is None:
        return json.dumps({"statut": "ok", "commandes": []})
    interpreteur, source = _session
    sortie = SortieStudio(envoyer)
    interpreteur.sortie = sortie
    try:
        erreur = web.declencher(interpreteur, identifiant, genre, json.loads(valeurs or "{}"), source)
    finally:
        sortie.vider()
    resultat = {"statut": "erreur" if erreur else "ok",
                "commandes": interpreteur.page.prendre_commandes()}
    if erreur:
        resultat["texte_erreur"] = erreur
    return json.dumps(resultat)


def _visiter(methode, adresse, corps):
    """Visite une adresse du site en cours, en gardant le cookie de session
    et en suivant les redirections. Renvoie {statut, adresse, html}."""
    app, cookie, _ = _serveur
    for _ in range(REDIRECTIONS_MAX + 1):
        entetes = {"Host": "kplus.local"}
        if cookie:
            entetes["Cookie"] = cookie
        if methode == "POST":
            entetes["Content-Type"] = "application/x-www-form-urlencoded"
        reponse = app.traiter(methode, adresse, entetes, corps)
        nouveau = reponse.entete("Set-Cookie")
        if nouveau:
            cookie = _serveur[1] = nouveau.split(";")[0]
        if reponse.statut == 303 and reponse.entete("Location"):
            methode, adresse, corps = "GET", reponse.entete("Location"), b""
            continue
        return {"statut": reponse.statut, "adresse": adresse, "html": reponse.corps.decode("utf-8")}
    return {"statut": 508, "adresse": adresse, "html": "<p>Trop de redirections.</p>"}


def serveur_requete(methode: str, adresse: str, champs: str, envoyer) -> str:
    """Visite d'une page du site côté serveur en cours (aperçu dans le
    navigateur). `champs` : JSON d'une liste de paires [nom, valeur] envoyées
    par un formulaire."""
    import urllib.parse
    if _serveur is None:
        return json.dumps({"statut": 410, "adresse": adresse,
                           "html": "<p>Le programme n'est plus en cours : exécutez-le à nouveau.</p>"})
    sortie = SortieStudio(envoyer)
    _serveur[0].interp.sortie = sortie
    corps = urllib.parse.urlencode([tuple(p) for p in json.loads(champs or "[]")]).encode("utf-8") if methode == "POST" else b""
    try:
        return json.dumps(_visiter(methode.upper(), adresse, corps))
    finally:
        sortie.vider()


def executer_test(source: str, entree: str) -> str:
    """Exécution d'un test d'exercice (UPL Code Académie) : sortie du programme,
    ou description de la page pour un programme web dont l'entrée est un
    scénario (voir kplus/scenario.py)."""
    from kplus.scenario import ErreurScenario, executer_test as executer
    debut = time.monotonic()
    try:
        sortie, erreur = executer(source, entree)
        resultat = {"statut": "ok", "sortie": sortie}
        if erreur is not None:
            resultat = {"statut": "erreur", "sortie": sortie, "erreur": decrire_erreur(erreur, source)}
    except ErreurKPlus as e:
        resultat = {"statut": "erreur", "sortie": "", "erreur": decrire_erreur(e, source)}
    except ErreurScenario as e:
        resultat = {"statut": "scenario", "sortie": "", "message": str(e)}
    except SignalQuitter:
        resultat = {"statut": "ok", "sortie": ""}
    resultat["duree_ms"] = round((time.monotonic() - debut) * 1000)
    return json.dumps(resultat)
