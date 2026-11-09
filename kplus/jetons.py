"""Jetons (tokens) de K+ : types, mots-clés et symboles.

Un jeton est le plus petit « mot » que le lexer reconnaît dans le code source :
un nombre, un texte, un nom, un mot-clé, un symbole ou une fin de ligne.
"""

import unicodedata
from dataclasses import dataclass

# Types de jetons
ENTIER = "ENTIER"
DECIMAL = "DECIMAL"
TEXTE = "TEXTE"
IDENT = "IDENT"
MOTCLE = "MOTCLE"
SYMBOLE = "SYMBOLE"
NL = "NL"
FIN_FICHIER = "FIN_FICHIER"

# Mots-clés réservés (forme officielle).
MOTS_CLES = frozenset({
    "variable", "constante", "fonction", "retourner",
    "si", "alors", "sinon", "fin",
    "tant", "que", "faire", "pour", "chaque", "dans", "de", "à", "pas",
    "arreter", "continuer",
    "essayer", "attraper", "lever",
    "et", "ou", "non",
    "vrai", "faux", "nul",
    "utiliser",
})

# Formes accentuées acceptées comme alias -> forme officielle.
ALIAS_MOTS_CLES = {"arrêter": "arreter"}

SYMBOLES_DOUBLES = frozenset({"==", "!=", "<=", ">="})
SYMBOLES_SIMPLES = frozenset("()[],=+-*/%^<>")
OPERATEURS_COMPARAISON = frozenset({"==", "!=", "<", "<=", ">", ">="})


@dataclass(frozen=True)
class Jeton:
    type: str
    valeur: object
    ligne: int
    colonne: int

    def decrire(self) -> str:
        """Description lisible du jeton, pour les messages d'erreur."""
        if self.type == NL:
            return "une fin de ligne"
        if self.type == FIN_FICHIER:
            return "la fin du programme"
        if self.type == MOTCLE:
            return f"le mot-clé « {self.valeur} »"
        if self.type == IDENT:
            return f"le nom « {self.valeur} »"
        if self.type == TEXTE:
            return "un texte"
        if self.type in (ENTIER, DECIMAL):
            return f"le nombre {self.valeur!r}"
        return f"« {self.valeur} »"


def preparer_source(source: str) -> str:
    """Prépare le texte source : retire le BOM, unifie les fins de ligne
    en « \\n » et normalise l'Unicode (NFC), pour que « à » soit toujours
    reconnu de la même façon quelle que soit la manière dont il a été tapé."""
    if source.startswith("﻿"):
        source = source[1:]
    source = source.replace("\r\n", "\n").replace("\r", "\n")
    return unicodedata.normalize("NFC", source)
