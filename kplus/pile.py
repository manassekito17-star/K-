"""Exécution avec une grande pile.

L'analyseur et l'interpréteur sont récursifs : un appel de fonction K+ ou une
parenthèse imbriquée utilise plusieurs niveaux de la pile de Python. Pour
garantir les 1000 appels imbriqués promis par la spécification, le travail
est fait dans un fil d'exécution doté d'une grande pile.
"""

import sys
import threading

from .erreurs import Interruption

TAILLE_PILE = 256 * 1024 * 1024
LIMITE_RECURSION_PYTHON = 60_000

_local = threading.local()


def avec_grande_pile(fonction, interpreteur=None):
    """Exécute fonction() avec une grande pile et renvoie son résultat.

    Si Ctrl+C est pressé, l'interpréteur (s'il est fourni) est prié de
    s'arrêter et Interruption est levée.
    """
    if getattr(_local, "grande_pile", False):
        return fonction()                     # déjà dans un fil adapté

    resultat = {}

    def cible():
        _local.grande_pile = True
        try:
            resultat["valeur"] = fonction()
        except BaseException as exc:          # transmis au fil appelant
            resultat["exception"] = exc

    if sys.getrecursionlimit() < LIMITE_RECURSION_PYTHON:
        sys.setrecursionlimit(LIMITE_RECURSION_PYTHON)
    ancienne = threading.stack_size()
    try:
        threading.stack_size(TAILLE_PILE)
    except (ValueError, RuntimeError):
        pass
    try:
        fil = threading.Thread(target=cible, daemon=True)
        fil.start()
    finally:
        threading.stack_size(ancienne)

    try:
        while fil.is_alive():
            fil.join(0.05)
    except KeyboardInterrupt:
        if interpreteur is not None:
            interpreteur.interrompu = True
        fil.join(1.0)
        raise Interruption() from None

    if "exception" in resultat:
        raise resultat["exception"]
    return resultat.get("valeur")
