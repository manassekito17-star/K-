"""Analyse lexicale : transforme le texte source en une liste de jetons.

Exemple : « variable x = 5 » devient
    MOTCLE(variable)  IDENT(x)  SYMBOLE(=)  ENTIER(5)
"""

import math
import unicodedata

from .erreurs import ErreurLexicale
from .jetons import (
    ALIAS_MOTS_CLES, DECIMAL, ENTIER, FIN_FICHIER, IDENT, MOTCLE, MOTS_CLES,
    NL, SYMBOLE, SYMBOLES_DOUBLES, SYMBOLES_SIMPLES, TEXTE, Jeton,
    preparer_source,
)

CHIFFRES = "0123456789"
ECHAPPEMENTS = {"n": "\n", "t": "\t", '"': '"', "\\": "\\"}

# Conseils pour les caractères inconnus les plus fréquents.
CONSEILS_CARACTERES = {
    ";": "K+ n'utilise pas de point-virgule : écrivez une instruction par ligne.",
    "'": 'les textes s\'écrivent entre guillemets doubles : "Bonjour".',
    "!": "pour « différent de », écrivez != ; pour la négation, écrivez non.",
    "{": "les blocs K+ se terminent par le mot-clé fin, pas par des accolades.",
    "}": "les blocs K+ se terminent par le mot-clé fin, pas par des accolades.",
    "&": "pour le « et » logique, écrivez et.",
    "|": "pour le « ou » logique, écrivez ou.",
    ".": "un nombre décimal s'écrit avec un chiffre avant le point : 0.5.",
    "”": "ce guillemet fermant n'a pas de guillemet ouvrant “ correspondant.",
    "«": 'les textes s\'écrivent entre guillemets "..." ou “...”.',
    "»": 'les textes s\'écrivent entre guillemets "..." ou “...”.',
}


def est_debut_nom(c: str) -> bool:
    return c == "_" or c.isalpha()


def est_suite_nom(c: str) -> bool:
    return (c == "_" or c.isalpha() or c in CHIFFRES
            or unicodedata.category(c).startswith("M"))


class Lexer:
    def __init__(self, source: str):
        self.src = preparer_source(source)
        self.pos = 0
        self.ligne = 1
        self.colonne = 1
        self.profondeur = 0          # nombre de ( et [ ouverts
        self.jetons: list[Jeton] = []

    # --- outils -------------------------------------------------------------

    def car(self, decalage: int = 0) -> str:
        i = self.pos + decalage
        return self.src[i] if i < len(self.src) else ""

    def avancer(self) -> str:
        c = self.src[self.pos]
        self.pos += 1
        if c == "\n":
            self.ligne += 1
            self.colonne = 1
        else:
            self.colonne += 1
        return c

    def ajouter(self, type_, valeur, ligne, colonne):
        self.jetons.append(Jeton(type_, valeur, ligne, colonne))

    def ajouter_fin_ligne(self, ligne, colonne):
        # Pas de fin de ligne entre parenthèses/crochets, ni en double.
        if self.profondeur > 0:
            return
        if self.jetons and self.jetons[-1].type != NL:
            self.ajouter(NL, "\n", ligne, colonne)

    def erreur(self, message, ligne, colonne, conseil=None, incomplet=False):
        return ErreurLexicale(message, ligne, colonne, conseil, incomplet)

    # --- boucle principale ----------------------------------------------------

    def analyser(self) -> list[Jeton]:
        while self.pos < len(self.src):
            c = self.car()
            ligne, colonne = self.ligne, self.colonne

            if c in " \t":
                self.avancer()
            elif c == "\n":
                self.ajouter_fin_ligne(ligne, colonne)
                self.avancer()
            elif c == "#":
                while self.pos < len(self.src) and self.car() != "\n":
                    self.avancer()
            elif c == "/" and self.car(1) == "*":
                self.commentaire_bloc(ligne, colonne)
            elif c in CHIFFRES:
                self.nombre(ligne, colonne)
            elif est_debut_nom(c):
                self.nom(ligne, colonne)
            elif c in ('"', "“"):
                self.texte(ligne, colonne)
            elif c + self.car(1) in SYMBOLES_DOUBLES:
                self.avancer()
                self.avancer()
                self.ajouter(SYMBOLE, c + self.src[self.pos - 1], ligne, colonne)
            elif c in SYMBOLES_SIMPLES:
                self.avancer()
                if c in "([":
                    self.profondeur += 1
                elif c in ")]" and self.profondeur > 0:
                    self.profondeur -= 1
                self.ajouter(SYMBOLE, c, ligne, colonne)
            else:
                nom = unicodedata.name(c, "")
                description = f"« {c} »" if c.isprintable() else f"U+{ord(c):04X}"
                if nom and c.isprintable():
                    description += f" ({nom.lower()})"
                raise self.erreur(
                    f"caractère inattendu {description}", ligne, colonne,
                    CONSEILS_CARACTERES.get(c))

        self.ajouter_fin_ligne(self.ligne, self.colonne)
        self.ajouter(FIN_FICHIER, None, self.ligne, self.colonne)
        return self.jetons

    # --- éléments -------------------------------------------------------------

    def commentaire_bloc(self, ligne, colonne):
        self.avancer()
        self.avancer()
        contient_fin_ligne = False
        while True:
            if self.pos >= len(self.src):
                raise self.erreur(
                    "commentaire « /* » jamais fermé", ligne, colonne,
                    "terminez le commentaire par */", incomplet=True)
            if self.car() == "*" and self.car(1) == "/":
                self.avancer()
                self.avancer()
                break
            if self.car() == "\n":
                contient_fin_ligne = True
            self.avancer()
        if contient_fin_ligne:
            self.ajouter_fin_ligne(ligne, colonne)

    def lire_chiffres(self) -> str:
        """Lit des chiffres, éventuellement séparés par « _ » (1_000)."""
        resultat = [self.avancer()]
        while True:
            c = self.car()
            if c and c in CHIFFRES:
                resultat.append(self.avancer())
            elif c == "_":
                if self.car(1) and self.car(1) in CHIFFRES:
                    self.avancer()
                else:
                    raise self.erreur(
                        "« _ » doit être placé entre deux chiffres",
                        self.ligne, self.colonne, "exemple : 1_000_000")
            else:
                return "".join(resultat)

    def nombre(self, ligne, colonne):
        partie_entiere = self.lire_chiffres()
        if len(partie_entiere) > 1 and partie_entiere[0] == "0":
            raise self.erreur(
                "un nombre ne peut pas commencer par 0", ligne, colonne,
                f"écrivez {partie_entiere.lstrip('0') or '0'}")
        texte = partie_entiere
        est_decimal = False

        if self.car() == ".":
            if self.car(1) and self.car(1) in CHIFFRES:
                self.avancer()
                texte += "." + self.lire_chiffres()
                est_decimal = True
            else:
                raise self.erreur(
                    "chiffre attendu après le point décimal",
                    self.ligne, self.colonne,
                    f"écrivez {partie_entiere}.0")

        if self.car() in ("e", "E") and self.car():
            suivant = self.car(1)
            if (suivant and suivant in CHIFFRES) or (
                    suivant in ("+", "-") and suivant
                    and self.car(2) and self.car(2) in CHIFFRES):
                self.avancer()
                exposant = "e"
                if self.car() in ("+", "-"):
                    exposant += self.avancer()
                texte += exposant + self.lire_chiffres()
                est_decimal = True

        c = self.car()
        if c and est_suite_nom(c):
            raise self.erreur(
                "nombre mal formé : un nom ne peut pas commencer par un chiffre",
                ligne, colonne)

        if est_decimal:
            valeur = float(texte)
            if math.isinf(valeur):
                raise self.erreur("nombre décimal trop grand", ligne, colonne)
            self.ajouter(DECIMAL, valeur, ligne, colonne)
        else:
            self.ajouter(ENTIER, int(texte), ligne, colonne)

    def nom(self, ligne, colonne):
        debut = self.pos
        self.avancer()
        while self.pos < len(self.src) and est_suite_nom(self.car()):
            self.avancer()
        mot = self.src[debut:self.pos]
        mot = ALIAS_MOTS_CLES.get(mot, mot)
        if mot in MOTS_CLES:
            self.ajouter(MOTCLE, mot, ligne, colonne)
        else:
            self.ajouter(IDENT, mot, ligne, colonne)

    def texte(self, ligne, colonne):
        ouvrant = self.avancer()
        fermant = '"' if ouvrant == '"' else "”"
        morceaux = []
        while True:
            c = self.car()
            if c == "" or c == "\n":
                raise self.erreur(
                    "texte non fermé", ligne, colonne,
                    f"ajoutez {fermant} à la fin du texte (un texte tient sur une ligne)")
            if c == fermant:
                self.avancer()
                break
            if c == "\\":
                l_echap, c_echap = self.ligne, self.colonne
                self.avancer()
                code = self.car()
                if code in ECHAPPEMENTS and code:
                    morceaux.append(ECHAPPEMENTS[self.avancer()])
                    continue
                if code == "" or code == "\n":
                    raise self.erreur(
                        "texte non fermé", ligne, colonne,
                        f"ajoutez {fermant} à la fin du texte")
                raise self.erreur(
                    f"séquence d'échappement inconnue « \\{code} »",
                    l_echap, c_echap,
                    "séquences permises : \\n, \\t, \\\", \\\\ "
                    "(pour écrire une barre oblique inverse : \\\\)")
            morceaux.append(self.avancer())
        self.ajouter(TEXTE, "".join(morceaux), ligne, colonne)


def analyser_lexique(source: str) -> list[Jeton]:
    return Lexer(source).analyser()
