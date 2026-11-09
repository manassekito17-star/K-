"""Exécution avec une grande pile.

L'analyseur et l'interpréteur sont récursifs : un appel de fonction K+ ou une
parenthèse imbriquée utilise plusieurs niveaux de la pile de Python. Pour
garantir les 1000 appels imbriqués promis par la spécification, le travail
est fait dans un fil d'exécution doté d'une grande pile.

Chaque système a ses propres limites (Windows refuse une pile de 256 Mio ou
plus, par exemple) : plusieurs tailles sont donc essayées. En dernier
recours, le travail est fait sans grande pile ; une récursion trop profonde
donne alors une ErreurRecursion claire, jamais un plantage.
"""

import sys
import threading

from .erreurs import ErreurRecursion, Interruption

MIO = 1024 * 1024
TAILLES_PILE = [255 * MIO, 128 * MIO, 64 * MIO]
# Limite de récursion de Python pendant l'exécution K+. Elle tient même dans
# la plus petite pile essayée (64 Mio / 16 384 = 4 Kio par niveau, largement
# assez), et suffit pour 1000 appels K+ imbriqués (environ 7 niveaux chacun).
LIMITE_RECURSION = 16_384

_local = threading.local()


def _demarrer_fil(cible):
    """Démarre cible() dans un fil à grande pile. Renvoie le fil, ou None."""
    ancienne = threading.stack_size()
    try:
        for taille in TAILLES_PILE:
            try:
                threading.stack_size(taille)
            except (ValueError, RuntimeError):
                continue                       # taille refusée : plus petite
            fil = threading.Thread(target=cible, daemon=True)
            try:
                fil.start()
            except RuntimeError:
                continue                       # mémoire insuffisante : plus petite
            return fil
        return None
    finally:
        threading.stack_size(ancienne)


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
        except RecursionError:
            resultat["exception"] = ErreurRecursion(
                "programme trop profondément imbriqué (limite de la pile atteinte)")
        except BaseException as exc:          # transmis au fil appelant
            resultat["exception"] = exc
        finally:
            _local.grande_pile = False

    ancienne_limite = sys.getrecursionlimit()
    try:
        sys.setrecursionlimit(max(ancienne_limite, LIMITE_RECURSION))
        fil = _demarrer_fil(cible)
        if fil is None:
            # Aucune grande pile possible : on garde la limite d'origine, sûre.
            sys.setrecursionlimit(ancienne_limite)
            cible()
        else:
            try:
                while fil.is_alive():
                    fil.join(0.05)
            except KeyboardInterrupt:
                if interpreteur is not None:
                    interpreteur.interrompu = True
                fil.join(1.0)
                raise Interruption() from None
    finally:
        sys.setrecursionlimit(ancienne_limite)

    if "exception" in resultat:
        raise resultat["exception"]
    return resultat.get("valeur")
