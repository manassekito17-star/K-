"""Fonctions natives de K+ (spécification §8).

Chaque fonction reçoit l'interpréteur et la liste des arguments déjà évalués.
"""

import math
import re
from decimal import ROUND_HALF_UP, Decimal, localcontext

from .erreurs import ErreurType, ErreurValeur, SignalQuitter
from .operations import verifier_decimal
from .valeurs import (
    FonctionNative, decrire_type, est_nombre, nom_type, representer,
)

MOTIF_ENTIER = re.compile(r"\s*[+-]?[0-9]+\s*")
MOTIF_DECIMAL = re.compile(r"\s*[+-]?[0-9]+(\.[0-9]+)?([eE][+-]?[0-9]+)?\s*")


def _exiger_nombre(nom, v, position="l'argument"):
    if not est_nombre(v):
        raise ErreurType(f"{nom}() attend un nombre comme {position}, "
                         f"pas {decrire_type(v)}")


def afficher(interp, args):
    interp.sortie.write(" ".join(representer(a) for a in args) + "\n")
    interp.sortie.flush()
    return None


def demander(interp, args):
    invite = ""
    if args:
        invite = args[0]
        if type(invite) is not str:
            raise ErreurType(f"demander() attend un texte comme invite, "
                             f"pas {decrire_type(invite)}")
    try:
        return interp.lire_ligne(invite)
    except EOFError:
        return None


def texte(interp, args):
    return representer(args[0])


def entier(interp, args):
    v = args[0]
    if type(v) is int:
        return v
    if type(v) is float:
        return int(v)                       # tronque vers zéro
    if type(v) is str:
        if MOTIF_ENTIER.fullmatch(v):
            return int(v.strip())
        conseil = None
        if MOTIF_DECIMAL.fullmatch(v):
            conseil = "pour un nombre à virgule, utilisez decimal(...) puis entier(...)"
        raise ErreurValeur(f"impossible de convertir le texte \"{v}\" en entier",
                           conseil=conseil)
    raise ErreurType(f"impossible de convertir {decrire_type(v)} en entier")


def decimal(interp, args):
    v = args[0]
    if type(v) is float:
        return v
    if type(v) is int:
        try:
            return float(v)
        except OverflowError:
            raise ErreurValeur("entier trop grand pour être converti en décimal") from None
    if type(v) is str:
        if MOTIF_DECIMAL.fullmatch(v):
            r = float(v.strip())
            if math.isinf(r):
                raise ErreurValeur(f"le nombre \"{v}\" est trop grand")
            return r
        conseil = None
        if re.fullmatch(r"\s*[+-]?[0-9]+,[0-9]+\s*", v):
            conseil = "le séparateur décimal est le point : 3.5"
        raise ErreurValeur(f"impossible de convertir le texte \"{v}\" en décimal",
                           conseil=conseil)
    raise ErreurType(f"impossible de convertir {decrire_type(v)} en décimal")


def type_(interp, args):
    return nom_type(args[0])


def longueur(interp, args):
    v = args[0]
    if type(v) in (str, list):
        return len(v)
    raise ErreurType(f"longueur() attend un texte ou une liste, pas {decrire_type(v)}")


def ajouter(interp, args):
    liste, valeur = args
    if type(liste) is not list:
        raise ErreurType(f"ajouter() attend une liste comme premier argument, "
                         f"pas {decrire_type(liste)}")
    liste.append(valeur)
    return None


def absolu(interp, args):
    _exiger_nombre("absolu", args[0])
    return abs(args[0])


def racine(interp, args):
    x = args[0]
    _exiger_nombre("racine", x)
    if x < 0:
        raise ErreurValeur("racine() d'un nombre négatif n'existe pas dans les "
                           "nombres réels")
    try:
        return math.sqrt(x)
    except OverflowError:
        return float(math.isqrt(x))


def _arrondir_decimal(x, chiffres):
    """Arrondi « au plus proche, les demis en s'éloignant de zéro »."""
    with localcontext() as ctx:
        ctx.prec = 1000
        d = Decimal(repr(x)) if type(x) is float else Decimal(x)
        return d.quantize(Decimal(1).scaleb(-chiffres), rounding=ROUND_HALF_UP)


def arrondir(interp, args):
    x = args[0]
    _exiger_nombre("arrondir", x, "premier argument")
    if len(args) == 1:
        if type(x) is int:
            return x
        return int(_arrondir_decimal(x, 0))
    n = args[1]
    if type(n) is not int:
        raise ErreurType(f"arrondir() attend un entier comme nombre de chiffres, "
                         f"pas {decrire_type(n)}")
    if n < 0:
        raise ErreurValeur("le nombre de chiffres après la virgule doit être ≥ 0")
    try:
        if n > 400:                         # au-delà de la précision d'un décimal
            return verifier_decimal(float(x))
        return verifier_decimal(float(_arrondir_decimal(x, n)))
    except OverflowError:
        raise ErreurValeur("nombre trop grand pour être converti en décimal") from None


def quitter(interp, args):
    raise SignalQuitter(0)


# nom -> (nombre minimal d'arguments, nombre maximal ou None, fonction)
NATIVES = {
    "afficher": (0, None, afficher),
    "demander": (0, 1, demander),
    "texte": (1, 1, texte),
    "entier": (1, 1, entier),
    "decimal": (1, 1, decimal),
    "décimal": (1, 1, decimal),
    "type": (1, 1, type_),
    "longueur": (1, 1, longueur),
    "ajouter": (2, 2, ajouter),
    "absolu": (1, 1, absolu),
    "racine": (1, 1, racine),
    "arrondir": (1, 2, arrondir),
    "quitter": (0, 0, quitter),
}

NOMS_NATIFS = frozenset(NATIVES)


def installer(environnement):
    for nom, (mini, maxi, fonction) in NATIVES.items():
        environnement.definir_native(nom, FonctionNative(nom, mini, maxi, fonction))
