"""Opérateurs de K+ : arithmétique, comparaisons, accès par indice.

Règles : spécification §5. Les erreurs sont levées sans position ;
l'interpréteur y ajoute la ligne et la colonne du nœud concerné.
"""

import math

from .erreurs import ErreurDivisionParZero, ErreurIndex, ErreurType, ErreurValeur
from .valeurs import decrire_type, egal, est_nombre

# Au-delà, « a ^ b » entre entiers est refusé (protection mémoire/temps).
LIMITE_BITS_PUISSANCE = 1_000_000


def verifier_decimal(x: float) -> float:
    if math.isinf(x) or math.isnan(x):
        raise ErreurValeur("résultat décimal hors limites (nombre trop grand)")
    return x


def _erreur_operandes(op, a, b):
    conseil = None
    if op == "+" and (type(a) is str) != (type(b) is str):
        autre = b if type(a) is str else a
        if est_nombre(autre) or type(autre) is bool or autre is None:
            conseil = "convertissez la valeur en texte avec texte(...)"
    return ErreurType(
        f"impossible d'utiliser {op} entre {decrire_type(a)} et "
        f"{decrire_type(b)}", conseil=conseil)


def binaire(op: str, a, b):
    if op == "==":
        return egal(a, b)
    if op == "!=":
        return not egal(a, b)
    if op in ("<", "<=", ">", ">="):
        return comparer(op, a, b)

    if op == "+":
        if type(a) is str and type(b) is str:
            return a + b
        if type(a) is list and type(b) is list:
            return a + b
    if not (est_nombre(a) and est_nombre(b)):
        raise _erreur_operandes(op, a, b)

    try:
        if op == "+":
            r = a + b
        elif op == "-":
            r = a - b
        elif op == "*":
            r = a * b
        elif op == "/":
            if b == 0:
                raise ErreurDivisionParZero("division par zéro")
            r = a / b
        elif op == "%":
            if b == 0:
                raise ErreurDivisionParZero("modulo par zéro")
            r = a % b
        elif op == "^":
            return puissance(a, b)
        else:  # pragma: no cover - bogue interne
            raise AssertionError(op)
    except OverflowError:
        raise ErreurValeur("résultat décimal hors limites (nombre trop grand)") from None
    if type(r) is float:
        verifier_decimal(r)
    return r


def puissance(a, b):
    if type(a) is int and type(b) is int:
        if b >= 0:
            if abs(a) > 1 and b * a.bit_length() > LIMITE_BITS_PUISSANCE:
                raise ErreurValeur("résultat de la puissance trop grand")
            return a ** b
        if a == 0:
            raise ErreurDivisionParZero(
                "zéro ne peut pas être élevé à une puissance négative")
        try:
            return verifier_decimal(float(a ** b))
        except OverflowError:
            raise ErreurValeur("résultat décimal hors limites") from None
    try:
        return verifier_decimal(math.pow(a, b))
    except OverflowError:
        raise ErreurValeur("résultat décimal hors limites") from None
    except ValueError:
        if a == 0:
            raise ErreurDivisionParZero(
                "zéro ne peut pas être élevé à une puissance négative") from None
        raise ErreurValeur(
            "puissance impossible dans les nombres réels "
            "(nombre négatif élevé à une puissance non entière)") from None


def comparer(op, a, b) -> bool:
    if not ((est_nombre(a) and est_nombre(b))
            or (type(a) is str and type(b) is str)):
        raise ErreurType(
            f"impossible de comparer {decrire_type(a)} et {decrire_type(b)} "
            f"avec {op}",
            conseil="seuls deux nombres ou deux textes peuvent être comparés "
                    "avec <, <=, >, >=")
    if op == "<":
        return a < b
    if op == "<=":
        return a <= b
    if op == ">":
        return a > b
    return a >= b


def unaire(op: str, v):
    if not est_nombre(v):
        raise ErreurType(f"impossible d'utiliser {op} devant {decrire_type(v)}")
    return -v if op == "-" else v


def _verifier_indice(objet, indice):
    if type(objet) not in (list, str):
        raise ErreurType(
            f"les crochets [ ] s'utilisent sur une liste ou un texte, "
            f"pas sur {decrire_type(objet)}")
    if type(indice) is not int:
        raise ErreurType(f"un indice doit être un entier, pas {decrire_type(indice)}")
    taille = len(objet)
    if indice < 0 or indice >= taille:
        quoi = "la liste" if type(objet) is list else "le texte"
        if taille == 0:
            conseil = f"{quoi} est vide"
        else:
            conseil = f"les indices valides vont de 0 à {taille - 1}"
        unite = "élément" if type(objet) is list else "caractère"
        raise ErreurIndex(
            f"l'indice {indice} est hors limites : {quoi} contient "
            f"{taille} {unite}{'s' if taille > 1 else ''}", conseil=conseil)


def lire_indice(objet, indice):
    _verifier_indice(objet, indice)
    return objet[indice]


def ecrire_indice(objet, indice, valeur):
    if type(objet) is str:
        raise ErreurType("un texte ne peut pas être modifié",
                         conseil="construisez un nouveau texte, par exemple avec +")
    _verifier_indice(objet, indice)
    objet[indice] = valeur
