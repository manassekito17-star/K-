"""Robustesse (programmes aléatoires) et justesse des calculs (comparaison avec Python)."""

import io
import random
import unittest

from tests import robustesse
from tests.outils import kplus
from kplus.erreurs import ErreurDivisionParZero
from kplus.valeurs import representer


def expression_numerique(alea, profondeur=0):
    """Expression numérique aléatoire, écrite à la fois en K+ et en Python.
    Pas de booléens : en Python, vrai vaut 1, ce qui est interdit en K+."""
    if profondeur > 3 or alea.random() < 0.3:
        if alea.random() < 0.7:
            n = alea.randint(-20, 20)
        else:
            n = round(alea.uniform(-50, 50), alea.randint(0, 3))
        texte = repr(n)
        return f"({texte})", f"({texte})"
    op = alea.choice(["+", "-", "*", "/", "%", "^"])
    gk, gp = expression_numerique(alea, profondeur + 1)
    if op == "^":
        # Exposant entier petit : évite les nombres démesurés.
        e = alea.randint(-3, 4)
        return f"({gk} ^ ({e}))", f"({gp} ** ({e}))"
    dk, dp = expression_numerique(alea, profondeur + 1)
    return f"({gk} {op} {dk})", f"({gp} {op} {dp})"


def valeur_python(expression):
    """Calcule avec Python, en appliquant les règles de K+ (spécification §5)."""
    try:
        r = eval(expression, {"__builtins__": {}})
    except ZeroDivisionError:
        return "division par zéro"
    except OverflowError:
        return "hors limites"
    if isinstance(r, complex):
        return "non réel"
    if isinstance(r, float) and (r != r or r in (float("inf"), float("-inf"))):
        return "hors limites"
    if isinstance(r, bool):
        return "vrai" if r else "faux"
    return representer(r)


def valeur_kplus(expression):
    sortie = io.StringIO()
    try:
        kplus.executer(f"afficher({expression})", sortie=sortie)
    except ErreurDivisionParZero:
        return "division par zéro"
    except kplus.ErreurKPlus as e:
        if "réels" in e.message:
            return "non réel"
        if "hors limites" in e.message or "trop grand" in e.message:
            return "hors limites"
        raise
    return sortie.getvalue()[:-1]


class TestRobustesse(unittest.TestCase):
    def test_aucun_plantage_interne(self):
        try:
            stats = robustesse.campagne(1500, graine=2026)
        except robustesse.Bogue as b:
            self.fail(str(b))
        self.assertGreater(stats["mutations"].get("ok", 0), 0)

    def test_calculs_identiques_a_python(self):
        alea = random.Random(7)
        verifies = 0
        for _ in range(3000):
            ek, ep = expression_numerique(alea)
            if alea.random() < 0.3:          # comparaison, uniquement au sommet
                op = alea.choice(["<", "<=", ">", ">=", "==", "!="])
                dk, dp = expression_numerique(alea)
                ek, ep = f"{ek} {op} {dk}", f"{ep} {op} {dp}"
            attendu = valeur_python(ep)
            with self.subTest(expression=ek):
                self.assertEqual(valeur_kplus(ek), attendu)
            verifies += 1
        self.assertEqual(verifies, 3000)


if __name__ == "__main__":
    unittest.main()
