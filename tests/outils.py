"""Outils communs aux tests."""

import io
import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RACINE not in sys.path:
    sys.path.insert(0, RACINE)

import kplus  # noqa: E402


def executer(source, entree=""):
    """Exécute un programme K+ et renvoie ce qu'il a affiché."""
    sortie = io.StringIO()
    kplus.executer(source, sortie=sortie, entree=io.StringIO(entree))
    return sortie.getvalue()


def erreur_de(source):
    """Exécute un programme qui doit échouer et renvoie l'erreur K+."""
    try:
        executer(source)
    except kplus.ErreurKPlus as e:
        return e
    raise AssertionError("aucune erreur levée")
