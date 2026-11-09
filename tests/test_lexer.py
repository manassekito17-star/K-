import unittest

from tests.outils import kplus  # noqa: F401  (configure le chemin)
from kplus.erreurs import ErreurLexicale
from kplus.jetons import DECIMAL, ENTIER, FIN_FICHIER, IDENT, MOTCLE, NL, SYMBOLE, TEXTE
from kplus.lexer import analyser_lexique


def types_valeurs(source):
    return [(j.type, j.valeur) for j in analyser_lexique(source)
            if j.type not in (NL, FIN_FICHIER)]


class TestLexer(unittest.TestCase):
    def test_declaration(self):
        self.assertEqual(types_valeurs("variable x = 5"), [
            (MOTCLE, "variable"), (IDENT, "x"), (SYMBOLE, "="), (ENTIER, 5)])

    def test_nombres(self):
        self.assertEqual(types_valeurs("0 42 1_000 3.14 1.5e3 6e-2"), [
            (ENTIER, 0), (ENTIER, 42), (ENTIER, 1000), (DECIMAL, 3.14),
            (DECIMAL, 1500.0), (DECIMAL, 0.06)])

    def test_nombres_invalides(self):
        for source in ("007", "5.", "1__0", "1_", "12abc", "1e999"):
            with self.subTest(source=source):
                with self.assertRaises(ErreurLexicale):
                    analyser_lexique(source)

    def test_textes(self):
        self.assertEqual(types_valeurs('"a\\nb" “c\\"d”'), [
            (TEXTE, "a\nb"), (TEXTE, 'c"d')])
        self.assertEqual(types_valeurs('“dit "oui"”'), [(TEXTE, 'dit "oui"')])

    def test_texte_non_ferme(self):
        with self.assertRaises(ErreurLexicale) as ctx:
            analyser_lexique('x = "abc\ny')
        self.assertEqual((ctx.exception.ligne, ctx.exception.colonne), (1, 5))

    def test_echappement_inconnu(self):
        with self.assertRaises(ErreurLexicale):
            analyser_lexique('"a\\qb"')

    def test_mots_cles_et_alias(self):
        self.assertEqual(types_valeurs("arrêter arreter à a Si"), [
            (MOTCLE, "arreter"), (MOTCLE, "arreter"), (MOTCLE, "à"),
            (IDENT, "a"), (IDENT, "Si")])

    def test_identifiants_accentues(self):
        self.assertEqual(types_valeurs("âge prénom_2 _x"), [
            (IDENT, "âge"), (IDENT, "prénom_2"), (IDENT, "_x")])

    def test_normalisation_unicode(self):
        # « à » écrit avec un accent combinant devient le mot-clé « à ».
        self.assertEqual(types_valeurs("à"), [(MOTCLE, "à")])

    def test_symboles(self):
        self.assertEqual([v for _, v in types_valeurs("== != <= >= < > = + - * / % ^ ( ) [ ] ,")],
                         ["==", "!=", "<=", ">=", "<", ">", "=", "+", "-", "*",
                          "/", "%", "^", "(", ")", "[", "]", ","])

    def test_commentaires(self):
        self.assertEqual(types_valeurs("1 # deux\n/* trois\n quatre */ 5 /* 6 */ 7"),
                         [(ENTIER, 1), (ENTIER, 5), (ENTIER, 7)])

    def test_commentaire_non_ferme(self):
        with self.assertRaises(ErreurLexicale) as ctx:
            analyser_lexique("/* oups")
        self.assertTrue(ctx.exception.incomplet)

    def test_fins_de_ligne(self):
        jetons = analyser_lexique("a\n\n\nb\r\nc")
        self.assertEqual([j.type for j in jetons],
                         [IDENT, NL, IDENT, NL, IDENT, NL, FIN_FICHIER])

    def test_fin_de_ligne_ignoree_entre_parentheses(self):
        jetons = analyser_lexique("f(1,\n2)\n[3,\n4]")
        self.assertEqual(sum(1 for j in jetons if j.type == NL), 2)

    def test_positions(self):
        jetons = analyser_lexique("x = 1\n  y")
        y = jetons[4]
        self.assertEqual((y.valeur, y.ligne, y.colonne), ("y", 2, 3))

    def test_caractere_inconnu(self):
        with self.assertRaises(ErreurLexicale) as ctx:
            analyser_lexique("x = 5 @ 2")
        self.assertEqual((ctx.exception.ligne, ctx.exception.colonne), (1, 7))
        with self.assertRaises(ErreurLexicale) as ctx:
            analyser_lexique("x = 1;")
        self.assertIn("point-virgule", ctx.exception.conseil)

    def test_bom_ignore(self):
        self.assertEqual(types_valeurs("﻿x"), [(IDENT, "x")])


if __name__ == "__main__":
    unittest.main()
