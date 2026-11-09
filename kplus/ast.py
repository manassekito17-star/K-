"""Arbre syntaxique abstrait (AST) de K+.

Le parser transforme les jetons en un arbre de nœuds. Chaque nœud représente
un élément du programme (une addition, un « si », un appel de fonction...) et
garde sa position (ligne, colonne) pour les messages d'erreur.

Cet arbre ne dépend pas de la façon dont il sera exécuté : l'interpréteur
actuel le parcourt, un futur compilateur natif pourra le traduire.
"""

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(eq=False)
class Noeud:
    ligne: int
    colonne: int


# --- Expressions (produisent une valeur) -----------------------------------

@dataclass(eq=False)
class Litteral(Noeud):
    valeur: Any                      # int, float, str, bool ou None


@dataclass(eq=False)
class Nom(Noeud):
    nom: str


@dataclass(eq=False)
class ListeLitterale(Noeud):
    elements: list


@dataclass(eq=False)
class OperationUnaire(Noeud):
    operateur: str                   # "-", "+" ou "non"
    operande: Noeud


@dataclass(eq=False)
class OperationBinaire(Noeud):
    operateur: str                   # + - * / % ^ == != < <= > >=
    gauche: Noeud
    droite: Noeud


@dataclass(eq=False)
class OperationLogique(Noeud):
    operateur: str                   # "et" ou "ou" (court-circuités)
    gauche: Noeud
    droite: Noeud


@dataclass(eq=False)
class Appel(Noeud):
    fonction: Noeud
    arguments: list


@dataclass(eq=False)
class AccesIndice(Noeud):
    objet: Noeud
    indice: Noeud


# --- Instructions -------------------------------------------------------------

@dataclass(eq=False)
class Declaration(Noeud):
    nom: str
    valeur: Noeud
    constante: bool


@dataclass(eq=False)
class Affectation(Noeud):
    cible: Noeud                     # Nom ou AccesIndice
    valeur: Noeud


@dataclass(eq=False)
class InstructionExpression(Noeud):
    expression: Noeud


@dataclass(eq=False)
class Si(Noeud):
    branches: list                   # liste de (condition, corps)
    sinon: Optional[list]


@dataclass(eq=False)
class TantQue(Noeud):
    condition: Noeud
    corps: list


@dataclass(eq=False)
class Pour(Noeud):
    variable: str
    debut: Noeud
    fin: Noeud
    pas: Optional[Noeud]
    corps: list


@dataclass(eq=False)
class PourChaque(Noeud):
    variable: str
    iterable: Noeud
    corps: list


@dataclass(eq=False)
class DefinitionFonction(Noeud):
    nom: str
    parametres: list
    corps: list


@dataclass(eq=False)
class Retourner(Noeud):
    valeur: Optional[Noeud]


@dataclass(eq=False)
class Arreter(Noeud):
    pass


@dataclass(eq=False)
class Continuer(Noeud):
    pass


@dataclass(eq=False)
class Essayer(Noeud):
    corps: list
    nom_erreur: Optional[str]
    gestionnaire: list


@dataclass(eq=False)
class Lever(Noeud):
    valeur: Noeud


@dataclass(eq=False)
class Programme(Noeud):
    instructions: list
