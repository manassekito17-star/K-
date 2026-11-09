import unittest

from tests.outils import kplus
from kplus import ast
from kplus.erreurs import ErreurSyntaxe


def analyser(source):
    return kplus.analyser(source).instructions


def erreur_syntaxe(source):
    with unittest.TestCase().assertRaises(ErreurSyntaxe) as ctx:
        kplus.analyser(source)
    return ctx.exception


class TestParser(unittest.TestCase):
    def test_priorites(self):
        (i,) = analyser("variable x = 1 + 2 * 3")
        e = i.valeur
        self.assertIsInstance(e, ast.OperationBinaire)
        self.assertEqual(e.operateur, "+")
        self.assertEqual(e.droite.operateur, "*")

    def test_puissance_associative_a_droite(self):
        (i,) = analyser("variable x = 2 ^ 3 ^ 2")
        self.assertEqual(i.valeur.operateur, "^")
        self.assertEqual(i.valeur.droite.operateur, "^")

    def test_moins_unaire_et_puissance(self):
        (i,) = analyser("variable x = -2 ^ 2")
        self.assertIsInstance(i.valeur, ast.OperationUnaire)
        self.assertEqual(i.valeur.operande.operateur, "^")

    def test_non_et_comparaison(self):
        (i,) = analyser("variable x = non a == b et c")
        self.assertEqual(i.valeur.operateur, "et")
        self.assertEqual(i.valeur.gauche.operateur, "non")

    def test_si_sinon_si_sinon(self):
        (i,) = analyser("si a alors\nf()\nsinon si b alors\ng()\nsinon\nh()\nfin")
        self.assertIsInstance(i, ast.Si)
        self.assertEqual(len(i.branches), 2)
        self.assertEqual(len(i.sinon), 1)

    def test_boucles(self):
        p = analyser("pour i de 1 à 9 pas 2 faire\nfin\n"
                     "pour chaque x dans l faire\nfin\n"
                     "tant que vrai faire\nfin")
        self.assertIsInstance(p[0], ast.Pour)
        self.assertIsNotNone(p[0].pas)
        self.assertIsInstance(p[1], ast.PourChaque)
        self.assertIsInstance(p[2], ast.TantQue)

    def test_fonction(self):
        (i,) = analyser("fonction f(a, b)\nretourner a\nfin")
        self.assertEqual(i.parametres, ["a", "b"])
        self.assertIsInstance(i.corps[0], ast.Retourner)

    def test_affectation_indice(self):
        (i,) = analyser("m[1][2] = 3")
        self.assertIsInstance(i, ast.Affectation)
        self.assertIsInstance(i.cible, ast.AccesIndice)

    def test_essayer(self):
        (i,) = analyser("essayer\nf()\nattraper e\ng()\nfin")
        self.assertEqual(i.nom_erreur, "e")

    def test_erreurs_de_syntaxe(self):
        cas = {
            "si vrai alors\nf()": 1,               # fin manquant
            "fin": 1,
            "f()\nsinon": 2,
            "variable x": 1,
            "variable si = 1": 1,
            "1 < 2 < 3": 1,
            "f() = 3": 1,
            "si x = 1 alors\nfin": 1,
            "si vrai alors f()\nfin": 1,
            "pour i de 1 a 3 faire\nfin": 1,
            "fonction f(a, a)\nfin": 1,
            "f(1, 2": 1,
            "afficher(1) afficher(2)": 1,
            "essayer\nf()\nfin": 3,
            "si a alors\nsinon\nsinon\nfin": 3,
            "retourner 1": 1,
            "arreter": 1,
            "fonction f()\npour i de 1 à 2 faire\nfonction g()\narreter\nfin\nfin\nfin": 4,
            "x + 1": 1,
            "[1, 2]": 1,
        }
        for source, ligne in cas.items():
            with self.subTest(source=source):
                self.assertEqual(erreur_syntaxe(source).ligne, ligne)

    def test_conseils(self):
        self.assertIn("==", erreur_syntaxe("si x = 1 alors\nfin").conseil)
        self.assertIn("à", erreur_syntaxe("pour i de 1 a 3 faire\nfin").conseil)
        self.assertIn("et", erreur_syntaxe("f(1 < 2 < 3)").conseil)

    def test_incomplet(self):
        self.assertTrue(erreur_syntaxe("si vrai alors").incomplet)
        self.assertTrue(erreur_syntaxe("f(1,").incomplet)
        self.assertFalse(erreur_syntaxe("fin").incomplet)

    def test_mode_interactif_accepte_expression(self):
        kplus.analyser("1 + 2", interactif=True)


if __name__ == "__main__":
    unittest.main()
