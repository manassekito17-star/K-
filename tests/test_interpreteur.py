import unittest

from tests.outils import erreur_de, executer
from kplus.erreurs import (
    ErreurConstante, ErreurDivisionParZero, ErreurIndex, ErreurNom,
    ErreurRecursion, ErreurType, ErreurUtilisateur, ErreurValeur,
)


def valeur(expression):
    """Affiche une expression et renvoie le texte obtenu (sans fin de ligne)."""
    return executer(f"afficher({expression})")[:-1]


class TestArithmetique(unittest.TestCase):
    def test_resultats(self):
        cas = {
            "2 + 3 * 4": "14", "(2 + 3) * 4": "20", "7 / 2": "3.5",
            "10 / 2": "5.0", "7 % 3": "1", "-7 % 3": "2", "7 % -3": "-2",
            "7.5 % 2": "1.5", "2 ^ 10": "1024", "2 ^ -1": "0.5", "-2 ^ 2": "-4",
            "2 ^ 3 ^ 2": "512", "4 ^ 0.5": "2.0", "1 + 1.0": "2.0",
            "0.1 + 0.2": "0.30000000000000004", "1e16": "1e+16",
            "0.00001": "1e-05", "-(3)": "-3", "+3": "3",
            "10 ^ 30": "1000000000000000000000000000000",
        }
        for expression, attendu in cas.items():
            with self.subTest(expression=expression):
                self.assertEqual(valeur(expression), attendu)

    def test_erreurs(self):
        cas = {
            "1 / 0": ErreurDivisionParZero, "1 % 0": ErreurDivisionParZero,
            "1.0 / 0.0": ErreurDivisionParZero, "0 ^ -1": ErreurDivisionParZero,
            "0.0 ^ -1": ErreurDivisionParZero,
            "1e308 * 10": ErreurValeur, "(-8) ^ 0.5": ErreurValeur,
            "2 ^ 100000000": ErreurValeur, "10 ^ 400 * 1.0": ErreurValeur,
            '"a" + 1': ErreurType, "vrai + 1": ErreurType, "nul * 2": ErreurType,
            '-"a"': ErreurType, "[1] - [1]": ErreurType,
        }
        for expression, classe in cas.items():
            with self.subTest(expression=expression):
                self.assertIsInstance(erreur_de(f"afficher({expression})"), classe)

    def test_concatenations(self):
        self.assertEqual(valeur('"a" + "b"'), "ab")
        self.assertEqual(valeur("[1] + [2, 3]"), "[1, 2, 3]")


class TestComparaisonsEtLogique(unittest.TestCase):
    def test_egalite(self):
        cas = {
            "1 == 1.0": "vrai", '1 == "1"': "faux", "vrai == 1": "faux",
            "nul == nul": "vrai", "nul == faux": "faux",
            "[1, [2]] == [1, [2]]": "vrai", "[1] == [1.0]": "vrai",
            "afficher == afficher": "vrai", "afficher == texte": "faux",
            '"a" != "b"': "vrai",
        }
        for expression, attendu in cas.items():
            with self.subTest(expression=expression):
                self.assertEqual(valeur(expression), attendu)

    def test_ordre(self):
        self.assertEqual(valeur('"abc" < "abd", 2 <= 2.0, 3 > 4'), "vrai vrai faux")
        self.assertIsInstance(erreur_de('afficher(1 < "2")'), ErreurType)
        self.assertIsInstance(erreur_de("afficher([1] < [2])"), ErreurType)

    def test_logique(self):
        self.assertEqual(valeur("vrai et faux, vrai ou faux, non faux"),
                         "faux vrai vrai")
        self.assertEqual(valeur("faux et 1 / 0 == 0"), "faux")
        self.assertEqual(valeur("vrai ou 1 / 0 == 0"), "vrai")
        self.assertIsInstance(erreur_de("afficher(1 et vrai)"), ErreurType)
        self.assertIsInstance(erreur_de("afficher(vrai et 1)"), ErreurType)
        self.assertIsInstance(erreur_de("afficher(non 0)"), ErreurType)


class TestVariablesEtPortee(unittest.TestCase):
    def test_declaration_et_affectation(self):
        self.assertEqual(executer("variable x = 1\nx = x + 1\nafficher(x)"), "2\n")

    def test_erreurs_de_nom(self):
        self.assertIsInstance(erreur_de("afficher(x)"), ErreurNom)
        self.assertIsInstance(erreur_de("x = 1"), ErreurNom)
        self.assertIsInstance(erreur_de("variable x = 1\nvariable x = 2"), ErreurNom)
        self.assertIsInstance(erreur_de("variable texte = 1"), ErreurNom)
        self.assertIsInstance(erreur_de("afficher = 1"), ErreurNom)
        self.assertIsInstance(erreur_de("fonction longueur()\nfin"), ErreurNom)
        self.assertIsInstance(erreur_de("fonction f(type)\nfin"), ErreurNom)

    def test_suggestion(self):
        e = erreur_de("variable compteur = 1\nafficher(compteure)")
        self.assertIn("compteur", e.conseil)

    def test_constante(self):
        e = erreur_de("constante PI = 3\nsi vrai alors\nPI = 4\nfin")
        self.assertIsInstance(e, ErreurConstante)
        self.assertEqual(e.ligne, 3)

    def test_portee_des_blocs(self):
        source = ("variable x = 1\nsi vrai alors\nvariable x = 2\nx = 3\n"
                  "afficher(x)\nfin\nafficher(x)")
        self.assertEqual(executer(source), "3\n1\n")

    def test_variable_redeclaree_a_chaque_tour(self):
        source = ("pour i de 1 à 2 faire\nvariable carre = i * i\n"
                  "afficher(carre)\nfin")
        self.assertEqual(executer(source), "1\n4\n")

    def test_listes_partagees(self):
        self.assertEqual(executer("variable a = [1]\nvariable b = a\nb[0] = 9\n"
                                  "afficher(a)"), "[9]\n")


class TestControle(unittest.TestCase):
    def test_condition_non_booleenne(self):
        for source in ("si 1 alors\nfin", "tant que nul faire\nfin",
                       'si "oui" alors\nfin'):
            with self.subTest(source=source):
                self.assertIsInstance(erreur_de(source), ErreurType)

    def test_pour(self):
        self.assertEqual(executer("pour i de 3 à 1 pas -1 faire\nafficher(i)\nfin"),
                         "3\n2\n1\n")
        self.assertEqual(executer("pour i de 1 à 0 faire\nafficher(i)\nfin"), "")
        self.assertIsInstance(erreur_de("pour i de 1 à 2.5 faire\nfin"), ErreurType)
        self.assertIsInstance(erreur_de("pour i de 1 à 2 pas 0 faire\nfin"), ErreurValeur)
        self.assertIsInstance(erreur_de("pour i de 1 à 2 faire\nfin\nafficher(i)"), ErreurNom)

    def test_bornes_evaluees_une_fois(self):
        source = ("variable n = 3\npour i de 1 à n faire\nn = 10\nafficher(i)\nfin")
        self.assertEqual(executer(source), "1\n2\n3\n")

    def test_pour_chaque(self):
        self.assertEqual(executer('pour chaque c dans "ab" faire\nafficher(c)\nfin'),
                         "a\nb\n")
        self.assertIsInstance(erreur_de("pour chaque x dans 5 faire\nfin"), ErreurType)

    def test_arreter_continuer_boucles_imbriquees(self):
        source = ("pour i de 1 à 2 faire\npour j de 1 à 3 faire\n"
                  "si j == 2 alors\narreter\nfin\nafficher(i, j)\nfin\nfin")
        self.assertEqual(executer(source), "1 1\n2 1\n")


class TestFonctions(unittest.TestCase):
    def test_retour_et_nul(self):
        self.assertEqual(executer("fonction f()\nfin\nafficher(f())"), "nul\n")

    def test_retourner_dans_boucle(self):
        source = ("fonction premier_pair(l)\npour chaque x dans l faire\n"
                  "si x % 2 == 0 alors\nretourner x\nfin\nfin\nretourner nul\nfin\n"
                  "afficher(premier_pair([1, 3, 4, 6]))")
        self.assertEqual(executer(source), "4\n")

    def test_fermeture(self):
        source = ("fonction ajouteur(n)\nfonction f(x)\nretourner x + n\nfin\n"
                  "retourner f\nfin\nvariable plus5 = ajouteur(5)\n"
                  "afficher(plus5(1))")
        self.assertEqual(executer(source), "6\n")

    def test_recursion_mutuelle(self):
        source = ("fonction pair(n)\nsi n == 0 alors\nretourner vrai\nfin\n"
                  "retourner impair(n - 1)\nfin\n"
                  "fonction impair(n)\nsi n == 0 alors\nretourner faux\nfin\n"
                  "retourner pair(n - 1)\nfin\nafficher(pair(10))")
        self.assertEqual(executer(source), "vrai\n")

    def test_profondeur_maximale(self):
        source = ("fonction f(n)\nsi n == 0 alors\nretourner 0\nfin\n"
                  "retourner f(n - 1)\nfin\nafficher(f({}))")
        self.assertEqual(executer(source.format(999)), "0\n")
        e = erreur_de(source.format(1000))
        self.assertIsInstance(e, ErreurRecursion)
        self.assertEqual(len(e.pile), 1000)

    def test_appel_avant_declaration(self):
        self.assertIsInstance(erreur_de("f()\nfonction f()\nfin"), ErreurNom)

    def test_arite_et_appel_invalide(self):
        self.assertIsInstance(erreur_de("fonction f(a)\nfin\nf(1, 2)"), ErreurType)
        self.assertIsInstance(erreur_de("variable x = 5\nx()"), ErreurType)
        self.assertIsInstance(erreur_de("longueur()"), ErreurType)

    def test_pile_d_appels(self):
        source = "fonction f(x)\nretourner 1 / x\nfin\nfonction g()\nretourner f(0)\nfin\ng()"
        e = erreur_de(source)
        self.assertEqual(e.ligne, 2)
        self.assertEqual(e.pile, [("f", 5), ("g", 7)])


class TestErreursDansLeProgramme(unittest.TestCase):
    def test_attraper_message(self):
        source = "essayer\nafficher([1][5])\nattraper e\nafficher(e)\nfin"
        self.assertIn("hors limites", executer(source))

    def test_lever(self):
        e = erreur_de('lever "stop"')
        self.assertIsInstance(e, ErreurUtilisateur)
        self.assertEqual(e.message, "stop")
        self.assertIsInstance(erreur_de("lever 5"), ErreurType)

    def test_attraper_recursion(self):
        source = ("fonction f()\nretourner f()\nfin\nessayer\nf()\nattraper\n"
                  'afficher("attrapée")\nfin\nfonction g(n)\nsi n == 0 alors\n'
                  "retourner 0\nfin\nretourner g(n - 1)\nfin\nafficher(g(900))")
        self.assertEqual(executer(source), "attrapée\n0\n")

    def test_retourner_traverse_essayer(self):
        source = ("fonction f()\nessayer\nretourner 1\nattraper\nfin\nretourner 2\n"
                  "fin\nafficher(f())")
        self.assertEqual(executer(source), "1\n")

    def test_erreur_dans_attraper_se_propage(self):
        e = erreur_de('essayer\nlever "a"\nattraper\nlever "b"\nfin')
        self.assertEqual((e.message, e.ligne), ("b", 4))


class TestNatives(unittest.TestCase):
    def test_conversions(self):
        cas = {
            'entier("  +12 ")': "12", "entier(-2.7)": "-2", 'decimal("1e3")': "1000.0",
            'décimal("-0.5")': "-0.5", "texte(nul)": "nul", "texte(1.0)": "1.0",
            "type(type)": "fonction", 'longueur("")': "0", "longueur([[]])": "1",
            "absolu(-0.5)": "0.5", "racine(2)": "1.4142135623730951",
            "arrondir(0.5)": "1", "arrondir(1.005, 2)": "1.01",
            "arrondir(-1.5)": "-2", "arrondir(7)": "7", "arrondir(7, 1)": "7.0",
            "texte(afficher)": "<fonction afficher>",
        }
        for expression, attendu in cas.items():
            with self.subTest(expression=expression):
                self.assertEqual(valeur(expression), attendu)

    def test_erreurs(self):
        cas = {
            'entier("3.5")': ErreurValeur, 'entier("")': ErreurValeur,
            "entier(vrai)": ErreurType, 'decimal("3,5")': ErreurValeur,
            'decimal("1e999")': ErreurValeur, "longueur(5)": ErreurType,
            "ajouter(5, 1)": ErreurType, "racine(-1)": ErreurValeur,
            'absolu("a")': ErreurType, "arrondir(1.5, -1)": ErreurValeur,
            "arrondir(1.5, 1.0)": ErreurType, "demander(5)": ErreurType,
        }
        for expression, classe in cas.items():
            with self.subTest(expression=expression):
                self.assertIsInstance(erreur_de(f"afficher({expression})"), classe)

    def test_conseil_virgule(self):
        self.assertIn("point", erreur_de('afficher(decimal("3,5"))').conseil)

    def test_demander(self):
        self.assertEqual(executer('afficher(demander("? "))', entree="Awa\n"),
                         "? Awa\n")
        self.assertEqual(executer("afficher(demander())", entree=""), "nul\n")

    def test_liste_qui_se_contient(self):
        self.assertEqual(executer("variable l = [1]\najouter(l, l)\nafficher(l)"),
                         "[1, [...]]\n")

    def test_affichage_textes_dans_liste(self):
        self.assertEqual(valeur('["a\\"b", "c\\nd"]'), '["a\\"b", "c\\nd"]')


if __name__ == "__main__":
    unittest.main()


class TestGrandePile(unittest.TestCase):
    """Reproduit la limite de Windows (pile de 256 Mio refusée)."""

    def test_taille_refusee_par_le_systeme(self):
        from unittest import mock

        from kplus import pile
        vraie = pile.threading.stack_size
        demandees = []

        def stack_size_type_windows(*taille):
            if taille and taille[0] >= 256 * 1024 * 1024:
                demandees.append(taille[0])
                raise ValueError("size not valid")
            if taille:
                demandees.append(taille[0])
            return vraie(*taille)

        with mock.patch.object(pile.threading, "stack_size", stack_size_type_windows):
            source = ("fonction f(n)\nsi n == 0 alors\nretourner 0\nfin\n"
                      "retourner f(n - 1)\nfin\nafficher(f(999))")
            self.assertEqual(executer(source), "0\n")
        self.assertIn(255 * 1024 * 1024, demandees)

    def test_sans_grande_pile_jamais_de_plantage(self):
        from unittest import mock

        from kplus import pile
        with mock.patch.object(pile, "_demarrer_fil", lambda cible: None):
            self.assertEqual(executer("afficher(1 + 1)"), "2\n")
            source = ("fonction f(n)\nsi n == 0 alors\nretourner 0\nfin\n"
                      "retourner f(n - 1)\nfin\nafficher(f(999))")
            self.assertIsInstance(erreur_de(source), ErreurRecursion)

    def test_parentheses_tres_imbriquees(self):
        self.assertEqual(executer("afficher(" + "(" * 1000 + "1" + ")" * 1000 + ")"), "1\n")
        e = erreur_de("afficher(" + "(" * 5000 + "1" + ")" * 5000 + ")")
        self.assertIsInstance(e, ErreurRecursion)
