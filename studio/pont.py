"""Pont entre K+ Studio (navigateur) et le moteur K+.

Ce module est chargé dans Pyodide (Python dans le navigateur) par
travailleur.js. Il n'utilise que le moteur K+ réel : rien n'est simulé.
Il est aussi testé sous Python normal (tests/test_studio.py).

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


def executer(source: str, entree: str, envoyer) -> str:
    """Analyse puis exécute le programme. `envoyer(genre, texte)` reçoit la
    sortie au fur et à mesure (genre : "sortie", "entree" ou "systeme")."""
    debut = time.monotonic()
    sortie = SortieStudio(envoyer)
    resultat = {"statut": "ok"}
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
    resultat["duree_ms"] = round((time.monotonic() - debut) * 1000)
    return json.dumps(resultat)
