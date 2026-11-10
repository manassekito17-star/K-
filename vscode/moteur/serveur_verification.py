"""Serveur de vérification K+ pour l'extension VS Code.

L'extension lance ce programme une fois, puis lui envoie le texte du fichier
à chaque modification. Il répond avec les erreurs trouvées par le VRAI moteur
K+ (copié à côté, dans moteur/kplus/), sans exécuter le programme.

Protocole : une ligne JSON par message, en UTF-8.
    entrée  : {"id": 3, "source": "afficher(1"}
    sortie  : {"id": 3, "ok": false, "erreur": {...}}   ou   {"id": 3, "ok": true}
Au démarrage, le serveur écrit {"pret": true, "version": "0.2.0"}.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import kplus  # noqa: E402  (le moteur copié dans moteur/kplus)
from kplus.erreurs import ErreurKPlus  # noqa: E402


def decrire(erreur: ErreurKPlus) -> dict:
    return {
        "categorie": erreur.categorie,
        "nom": erreur.nom_affiche,
        "message": erreur.message,
        "ligne": erreur.ligne,
        "colonne": erreur.colonne,
        "conseil": erreur.conseil,
    }


def verifier(source: str) -> dict:
    try:
        kplus.analyser(source)
    except ErreurKPlus as e:
        return {"ok": False, "erreur": decrire(e)}
    return {"ok": True}


def principal(entree=None, sortie=None):
    entree = entree or sys.stdin
    sortie = sortie or sys.stdout
    # Windows utilise parfois un autre encodage par défaut : on impose UTF-8.
    for flux in (entree, sortie):
        if hasattr(flux, "reconfigure"):
            flux.reconfigure(encoding="utf-8")

    def repondre(message):
        sortie.write(json.dumps(message, ensure_ascii=False) + "\n")
        sortie.flush()

    repondre({"pret": True, "version": kplus.__version__})
    for ligne in entree:
        ligne = ligne.strip()
        if not ligne:
            continue
        try:
            demande = json.loads(ligne)
            reponse = verifier(demande["source"])
            reponse["id"] = demande.get("id")
        except Exception as exc:  # message mal formé ou bogue : on continue
            reponse = {"id": None, "ok": True, "interne": f"{type(exc).__name__}: {exc}"}
        repondre(reponse)


if __name__ == "__main__":
    principal()
