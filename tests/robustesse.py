"""Tests de robustesse (« fuzzing ») de K+.

Des programmes aléatoires ou abîmés sont donnés au moteur. Le seul
comportement accepté est : réussir, ou s'arrêter sur une erreur K+ claire.
Toute autre exception Python est un bogue de l'interpréteur.

Utilisation : python tests/robustesse.py [nombre] [graine]
"""

import io
import random
import re
import sys
import threading
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

import kplus  # noqa: E402
from kplus.erreurs import ErreurAnalyse, ErreurKPlus, Interruption, SignalQuitter  # noqa: E402

DUREE_MAX = 0.3            # secondes d'exécution par programme

MORCEAUX = [
    "variable", "constante", "fonction", "retourner", "si", "alors", "sinon",
    "fin", "tant", "que", "faire", "pour", "chaque", "dans", "de", "à", "pas",
    "arreter", "continuer", "essayer", "attraper", "lever", "et", "ou", "non",
    "vrai", "faux", "nul", "x", "y", "f", "afficher", "longueur", "texte",
    "entier", "decimal", "racine", "arrondir", "ajouter", "type", "absolu",
    "0", "1", "-1", "2", "3.5", "1e308", "0.0", "10_000", '"a"', '""',
    "“é”", "(", ")", "[", "]", ",", "=", "==", "!=", "<", "<=", ">", ">=",
    "+", "-", "*", "/", "%", "^", "\n", "\n", "\n", " ", "#", "/*", "*/",
    "\\", '"', "@", ";", ".", "\t", "\r\n", "﻿", "é", "_",
    "utiliser", "web", "utiliser web\n", "titre", "bouton", "champ", "valeur",
    "liste", "ajouter_ligne", "zone", "placer", "couleur", '"rouge"', "supprimer",
    "toutes_les", "quand_clic", "changer_texte", "lien", '"https://x.org"',
]

VALEURS = ["0", "1", "-3", "2.5", "0.0", "1e300", '"ab"', '""', "vrai", "faux",
           "nul", "[]", "[1, 2]", '["a"]', "afficher", "[[1]]", "10 ^ 20"]
OPERATEURS = ["+", "-", "*", "/", "%", "^", "==", "!=", "<", "<=", ">", ">=",
              "et", "ou"]
FONCTIONS = ["texte", "entier", "decimal", "type", "longueur", "absolu",
             "racine", "arrondir", "non", "-", "+"]


def programmes_de_reference():
    sources = [p.read_text(encoding="utf-8")
               for p in sorted((RACINE / "exemples").glob("*.kplus"))]
    sources += [p.read_text(encoding="utf-8")
                for p in sorted((RACINE / "tests" / "conformite").glob("*.kplus"))]
    specification_web = (RACINE / "docs" / "specification" / "kplus-web-0.2.md").read_text(encoding="utf-8")
    sources += re.findall(r"```kplus\n(.*?)```", specification_web, re.S)
    return sources


def muter(source, alea):
    """Abîme un programme : supprime, duplique, échange ou insère des éléments."""
    lignes = source.split("\n")
    for _ in range(alea.randint(1, 4)):
        choix = alea.randrange(6)
        if choix == 0 and lignes:
            del lignes[alea.randrange(len(lignes))]
        elif choix == 1 and lignes:
            i = alea.randrange(len(lignes))
            lignes.insert(i, lignes[i])
        elif choix == 2 and len(lignes) > 1:
            i, j = alea.randrange(len(lignes)), alea.randrange(len(lignes))
            lignes[i], lignes[j] = lignes[j], lignes[i]
        elif choix == 3 and lignes:
            i = alea.randrange(len(lignes))
            ligne = lignes[i]
            k = alea.randint(0, len(ligne))
            lignes[i] = ligne[:k] + alea.choice(MORCEAUX) + ligne[k:]
        elif choix == 4 and lignes:
            i = alea.randrange(len(lignes))
            ligne = lignes[i]
            if ligne:
                k = alea.randrange(len(ligne))
                lignes[i] = ligne[:k] + ligne[k + alea.randint(1, 3):]
        else:
            lignes.insert(alea.randint(0, len(lignes)),
                          " ".join(alea.choice(MORCEAUX) for _ in range(alea.randint(1, 6))))
    return "\n".join(lignes)


def programme_aleatoire(alea):
    return " ".join(alea.choice(MORCEAUX) for _ in range(alea.randint(1, 40)))


def expression_aleatoire(alea, profondeur=0):
    if profondeur > 3 or alea.random() < 0.3:
        return alea.choice(VALEURS)
    choix = alea.randrange(4)
    if choix == 0:
        return (f"({expression_aleatoire(alea, profondeur + 1)} {alea.choice(OPERATEURS)} "
                f"{expression_aleatoire(alea, profondeur + 1)})")
    if choix == 1:
        f = alea.choice(FONCTIONS)
        argument = expression_aleatoire(alea, profondeur + 1)
        if f in ("non", "-", "+"):
            return f"({f} {argument})"
        if f == "arrondir" and alea.random() < 0.5:
            return f"arrondir({argument}, {expression_aleatoire(alea, profondeur + 1)})"
        return f"{f}({argument})"
    if choix == 2:
        return (f"{expression_aleatoire(alea, profondeur + 1)}"
                f"[{expression_aleatoire(alea, profondeur + 1)}]")
    return f"[{expression_aleatoire(alea, profondeur + 1)}, {expression_aleatoire(alea, profondeur + 1)}]"


class Bogue(Exception):
    pass


def simuler_visiteur(interp, source, alea=random.Random(0)):
    """Clics, saisies et minuteries au hasard sur la page d'un programme web."""
    from kplus import web
    for _ in range(15):
        elements = list(interp.page.elements.values())
        if not elements:
            return
        e = alea.choice(elements)
        champs = {c.id: alea.choice(["", "42", "abc", "3.5", "<b>x</b>", "é" * 50])
                  for c in elements if c.genre == "champ"}
        web.declencher(interp, e.id, alea.choice(["clic", "change", "minuterie", "inconnu"]),
                       champs, source)
        interp.page.prendre_commandes()


def essayer_programme(source, executer=True):
    """Renvoie le résultat ('ok', 'erreur K+'...) ; lève Bogue sinon."""
    try:
        programme = kplus.analyser(source)
    except ErreurAnalyse as e:
        kplus.formater_erreur(e, source)      # le message doit se construire
        return "erreur d'analyse"
    except Exception as e:
        raise Bogue(f"analyse : {type(e).__name__}: {e}\n--- programme ---\n{source}") from e
    if not executer:
        return "ok"

    interp = kplus.Interpreteur(sortie=io.StringIO(), entree=io.StringIO("1\nabc\n"))
    minuteur = threading.Timer(DUREE_MAX, lambda: setattr(interp, "interrompu", True))
    minuteur.start()
    try:
        interp.executer_programme(programme)
        if interp.page is not None:
            simuler_visiteur(interp, source)
        return "ok"
    except ErreurKPlus as e:
        kplus.formater_erreur(e, source)
        return "erreur d'exécution"
    except (SignalQuitter, Interruption):
        return "arrêté"
    except Exception as e:
        raise Bogue(f"exécution : {type(e).__name__}: {e}\n--- programme ---\n{source}") from e
    finally:
        minuteur.cancel()


def campagne(nombre, graine=0):
    """Lance `nombre` essais de chaque sorte ; renvoie les statistiques."""
    alea = random.Random(graine)
    references = programmes_de_reference()
    stats = {}

    def compter(sorte, resultat):
        stats.setdefault(sorte, {}).setdefault(resultat, 0)
        stats[sorte][resultat] += 1

    for _ in range(nombre):
        compter("aléatoires", essayer_programme(programme_aleatoire(alea), executer=False))
        compter("mutations", essayer_programme(muter(alea.choice(references), alea)))
        compter("expressions", essayer_programme(f"afficher({expression_aleatoire(alea)})"))
    return stats


if __name__ == "__main__":
    nombre = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
    graine = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    try:
        resultats = campagne(nombre, graine)
    except Bogue as b:
        print("BOGUE TROUVÉ :", b)
        raise SystemExit(1)
    for sorte, compte in resultats.items():
        print(f"{sorte:12} : {compte}")
    print("Aucun bogue trouvé.")
