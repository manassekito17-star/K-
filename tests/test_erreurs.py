import unittest

from tests.outils import erreur_de
from kplus.erreurs import ErreurType, formater_erreur


class TestFormatErreurs(unittest.TestCase):
    def test_format_complet(self):
        source = 'variable age = 20\nafficher("Âge : " + age)'
        e = erreur_de(source)
        self.assertIsInstance(e, ErreurType)
        self.assertEqual(formater_erreur(e, source),
                         "Erreur de type (ligne 2, colonne 19) : impossible "
                         "d'utiliser + entre un texte et un entier\n"
                         '   2 | afficher("Âge : " + age)\n'
                         "     |                   ^\n"
                         "Conseil : convertissez la valeur en texte avec texte(...)")

    def test_tabulations_conservees(self):
        source = "si vrai alors\n\tafficher(x)\nfin"
        texte = formater_erreur(erreur_de(source), source)
        self.assertIn("     | \t         ^", texte)

    def test_pile_regroupee(self):
        source = "fonction f()\nretourner f()\nfin\nf()"
        texte = formater_erreur(erreur_de(source), source)
        self.assertIn("appelée ligne 2 (× 999)", texte)
        self.assertIn("appelée ligne 4", texte)

    def test_sans_source(self):
        e = erreur_de("afficher(1 / 0)")
        self.assertEqual(formater_erreur(e),
                         "Erreur de division par zéro (ligne 1, colonne 12) : "
                         "division par zéro")


if __name__ == "__main__":
    unittest.main()
