"""Scénarios de test des pages K+ Web.

Un scénario simule un visiteur, puis décrit la page obtenue sous forme de
texte. Il permet de corriger automatiquement un exercice de site web (UPL
Code Académie) et de tester un site sans navigateur (« kplus --scenario »).

Actions, une par ligne :
    saisir "Étiquette du champ" "texte tapé"
    cliquer "Texte affiché"          (bouton, ligne, paragraphe… qui réagit au clic)
    minuterie 3                      (3 tours de toutes les minuteries actives)
    # commentaire

Description de la page, un élément par ligne, dans l'ordre d'affichage
(les éléments placés dans une liste ou une zone sont décalés de 2 espaces) :
    titre: Mes tâches
    champ: Nouvelle tâche = ""
    liste:
      ligne: Réviser
"""

import io
import re
import shlex

from . import analyser, web
from .erreurs import ErreurKPlus
from .interpreteur import Interpreteur
from .valeurs import representer


class ErreurScenario(Exception):
    """Action de scénario incorrecte (message destiné à l'auteur du scénario)."""


def _visibles(page):
    return [e for e in page.elements.values() if not e.supprime and e.genre != "minuterie"]


def decrire_page(page) -> str:
    """Description textuelle de la page, dans l'ordre d'affichage."""
    lignes = []

    def decrire(e, profondeur):
        retrait = "  " * profondeur
        if e.genre == "champ":
            lignes.append(f"{retrait}champ: {e.etiquette} = {representer(e.valeur, True)}")
        elif e.genre == "image":
            lignes.append(f"{retrait}image: {e.description}")
        elif e.genre == "lien":
            lignes.append(f"{retrait}lien: {e.texte} -> {e.adresse}")
        elif e.genre in ("liste", "zone"):
            lignes.append(f"{retrait}{e.genre}:")
        else:
            lignes.append(f"{retrait}{e.genre}: {e.texte}")
        for enfant in e.enfants:
            if not enfant.supprime:
                decrire(enfant, profondeur + 1)

    for e in _visibles(page):
        if e.parent is None:
            decrire(e, 0)
    return "\n".join(lignes) + ("\n" if lignes else "")


def _actions(scenario: str):
    for numero, ligne in enumerate(scenario.replace("\r\n", "\n").split("\n"), start=1):
        texte = ligne.strip()
        if not texte or texte.startswith("#"):
            continue
        try:
            morceaux = shlex.split(texte)
        except ValueError:
            raise ErreurScenario(f"scénario, ligne {numero} : guillemets mal fermés") from None
        yield numero, morceaux


def jouer(source: str, scenario: str, programme=None) -> str:
    """Exécute le programme, joue le scénario, renvoie la description finale de la page.

    Les erreurs K+ au démarrage sont levées normalement ; une erreur dans une
    action est ajoutée à la description (« erreur: … »), comme le bandeau
    rouge de la page.
    """
    interp = Interpreteur(io.StringIO(), io.StringIO(""))
    interp.executer_programme(programme or analyser(source))
    page = interp.page
    if page is None:
        raise ErreurScenario("ce programme ne crée pas de page web (« utiliser web » manquant)")
    erreurs = []

    def declencher(element, evenement):
        valeurs = {e.id: e.valeur for e in _visibles(page) if e.genre == "champ"}
        message = web.declencher(interp, element.id, evenement, valeurs)
        if message:
            erreurs.append(message.split("\n")[0])

    for numero, action in _actions(scenario):
        nom = action[0].lower()
        if nom == "saisir" and len(action) == 3:
            champs = [e for e in _visibles(page) if e.genre == "champ" and e.etiquette == action[1]]
            if not champs:
                raise ErreurScenario(f"scénario, ligne {numero} : aucun champ « {action[1]} »")
            champs[0].valeur = action[2]
            if "change" in champs[0].actions:
                declencher(champs[0], "change")
        elif nom == "cliquer" and len(action) == 2:
            cibles = [e for e in _visibles(page) if "clic" in e.actions and e.texte == action[1]]
            if not cibles:
                raise ErreurScenario(f"scénario, ligne {numero} : rien à cliquer avec le texte « {action[1]} »")
            declencher(cibles[0], "clic")
        elif nom == "minuterie" and len(action) == 2 and action[1].isdigit():
            for _ in range(int(action[1])):
                for e in [m for m in page.elements.values()
                          if m.genre == "minuterie" and not m.supprime]:
                    declencher(e, "minuterie")
        else:
            raise ErreurScenario(f"scénario, ligne {numero} : action inconnue « {' '.join(action)} » "
                                 f"(actions : saisir, cliquer, minuterie)")
    page.prendre_commandes()
    texte = decrire_page(page)
    for message in erreurs:
        texte += f"erreur: {message}\n"
    return texte


def executer_test(source: str, entree: str) -> tuple[str, ErreurKPlus | None]:
    """Exécution d'un test d'exercice : un programme web reçoit l'entrée comme
    scénario et renvoie la description de sa page ; un programme ordinaire est
    exécuté normalement avec l'entrée. Renvoie (sortie, erreur K+ éventuelle)."""
    programme = analyser(source)
    from . import ast
    if any(isinstance(i, ast.Utiliser) and i.bibliotheque == "web" for i in programme.instructions):
        return jouer(source, entree, programme), None
    sortie = io.StringIO()
    interp = Interpreteur(sortie, io.StringIO(entree))
    try:
        interp.executer_programme(programme)
    except ErreurKPlus as e:
        return sortie.getvalue(), e
    return sortie.getvalue(), None
