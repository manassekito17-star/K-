"""Interface en ligne de commande « kplus » (spécification §10)."""

import sys
import traceback

from . import __version__, analyser
from .erreurs import ErreurKPlus, Interruption, SignalQuitter, formater_erreur
from .interpreteur import Interpreteur
from .valeurs import representer

# Codes de sortie
SUCCES = 0
ERREUR_KPLUS = 1
ERREUR_UTILISATION = 2
ERREUR_INTERNE = 3
INTERRUPTION = 130

AIDE = f"""K+ {__version__} — langage de programmation en français

Utilisation :
  kplus programme.kplus             exécute un programme
  kplus --verifier programme.kplus  vérifie un programme sans l'exécuter
  kplus                             lance le mode interactif
  kplus --version                   affiche la version
  kplus --aide                      affiche cette aide

Codes de sortie : 0 succès, 1 erreur dans le programme K+,
2 mauvaise utilisation de la commande, 3 erreur interne, 130 interruption."""


def ecrire_erreur(texte):
    sys.stdout.flush()
    print(texte, file=sys.stderr)
    sys.stderr.flush()


def configurer_flux():
    """Évite un plantage si la console ne sait pas afficher un caractère."""
    for flux in (sys.stdout, sys.stderr):
        try:
            flux.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass


def lire_fichier(chemin):
    """Renvoie (source, None) ou (None, message d'erreur)."""
    try:
        with open(chemin, encoding="utf-8") as f:
            return f.read(), None
    except FileNotFoundError:
        return None, f"Erreur : fichier introuvable : {chemin}"
    except IsADirectoryError:
        return None, f"Erreur : {chemin} est un dossier, pas un fichier"
    except PermissionError:
        return None, f"Erreur : accès refusé au fichier {chemin}"
    except UnicodeDecodeError:
        return None, (f"Erreur : le fichier {chemin} n'est pas encodé en UTF-8. "
                      f"Enregistrez-le en UTF-8 dans votre éditeur.")
    except OSError as e:
        return None, f"Erreur : impossible de lire {chemin} ({e.strerror})"


def erreur_interne(exc):
    ecrire_erreur(
        "Erreur interne de K+ : ceci est un bogue de l'interpréteur, pas de "
        "votre programme. Merci de le signaler avec le message ci-dessous.\n"
        + "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
    return ERREUR_INTERNE


def verifier_fichier(chemin):
    source, probleme = lire_fichier(chemin)
    if probleme:
        ecrire_erreur(probleme)
        return ERREUR_UTILISATION
    try:
        analyser(source)
    except ErreurKPlus as e:
        ecrire_erreur(formater_erreur(e, source))
        return ERREUR_KPLUS
    print("Aucune erreur détectée.")
    return SUCCES


def executer_fichier(chemin):
    source, probleme = lire_fichier(chemin)
    if probleme:
        ecrire_erreur(probleme)
        return ERREUR_UTILISATION
    interpreteur = Interpreteur()

    try:
        programme = analyser(source)
        interpreteur.executer_programme(programme)
    except ErreurKPlus as e:
        ecrire_erreur(formater_erreur(e, source))
        return ERREUR_KPLUS
    except SignalQuitter as q:
        sys.stdout.flush()
        return q.code
    except Interruption:
        ecrire_erreur("\nProgramme interrompu.")
        return INTERRUPTION
    except RecursionError:
        ecrire_erreur("Erreur de récursion : le programme est trop profondément "
                      "imbriqué pour être analysé ou exécuté.")
        return ERREUR_KPLUS
    except Exception as exc:  # bogue de l'interpréteur
        return erreur_interne(exc)
    sys.stdout.flush()
    if interpreteur.page is not None:
        visibles = sum(1 for e in interpreteur.page.elements.values()
                       if e.genre != "minuterie" and not e.supprime)
        ecrire_erreur(
            f"Ce programme crée une page web ({visibles} élément(s)) : un terminal ne peut pas "
            f"l'afficher.\nPour la voir : ouvrez-la dans K+ Studio, ou créez le site avec "
            f"« kplus --site {chemin} ».")
    return SUCCES


def mode_interactif():
    print(f"K+ {__version__} — mode interactif. Tapez quitter() pour sortir.")
    interpreteur = Interpreteur()
    tampon = []
    while True:
        try:
            ligne = input("... " if tampon else "k+> ")
        except EOFError:
            print()
            return SUCCES
        except KeyboardInterrupt:
            print("\n(saisie annulée)")
            tampon = []
            continue

        tampon.append(ligne)
        source = "\n".join(tampon)
        if not source.strip():
            tampon = []
            continue
        try:
            programme = analyser(source, interactif=True)
        except ErreurKPlus as e:
            if getattr(e, "incomplet", False):
                continue                     # bloc pas encore terminé
            ecrire_erreur(formater_erreur(e, source))
            tampon = []
            continue
        tampon = []

        try:
            valeur = interpreteur.executer_programme(programme)
        except ErreurKPlus as e:
            ecrire_erreur(formater_erreur(e, source))
            continue
        except SignalQuitter as q:
            return q.code
        except Interruption:
            ecrire_erreur("Interrompu.")
            interpreteur.interrompu = False
            interpreteur.profondeur = 0
            continue
        except RecursionError:
            ecrire_erreur("Erreur de récursion : instruction trop profondément imbriquée.")
            continue
        except Exception as exc:
            erreur_interne(exc)
            continue

        derniere = programme.instructions[-1] if programme.instructions else None
        if valeur is not None and derniere is not None and \
                type(derniere).__name__ == "InstructionExpression":
            print(representer(valeur, imbrique=True))


def principal(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    configurer_flux()
    if not argv:
        return mode_interactif()
    premier = argv[0]
    if premier in ("--version", "-v"):
        print(f"K+ {__version__}")
        return SUCCES
    if premier in ("--aide", "--help", "-h"):
        print(AIDE)
        return SUCCES
    if premier == "--verifier":
        if len(argv) != 2:
            ecrire_erreur("Erreur : --verifier attend exactement un fichier.\n"
                          "Exemple : kplus --verifier programme.kplus")
            return ERREUR_UTILISATION
        return verifier_fichier(argv[1])
    if premier.startswith("-"):
        ecrire_erreur(f"Erreur : option inconnue « {premier} ». "
                      f"Tapez kplus --aide pour l'aide.")
        return ERREUR_UTILISATION
    if len(argv) > 1:
        ecrire_erreur("Erreur : un seul fichier à la fois. "
                      "Tapez kplus --aide pour l'aide.")
        return ERREUR_UTILISATION
    return executer_fichier(premier)
