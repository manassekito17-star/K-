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
  kplus --scenario site.kplus visite.txt
                                    simule un visiteur et décrit la page obtenue
  kplus --site programme.kplus [dossier]
                                    crée un site web à partir d'un programme K+ Web
  kplus --serveur programme.kplus [--port 8000] [--production]
                                    lance un site côté serveur (« utiliser serveur »)
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
    if interpreteur.serveur is not None:
        ecrire_erreur(
            f"Ce programme est un site côté serveur ({len(interpreteur.serveur.pages)} page(s)) : "
            f"pour l'ouvrir, lancez « kplus --serveur {chemin} ».")
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


def jouer_scenario(chemin, chemin_scenario):
    from .scenario import ErreurScenario, jouer
    source, probleme = lire_fichier(chemin)
    scenario, probleme2 = lire_fichier(chemin_scenario)
    if probleme or probleme2:
        ecrire_erreur(probleme or probleme2)
        return ERREUR_UTILISATION
    try:
        print(jouer(source, scenario), end="")
    except ErreurKPlus as e:
        ecrire_erreur(formater_erreur(e, source))
        return ERREUR_KPLUS
    except ErreurScenario as e:
        ecrire_erreur(f"Erreur : {e}")
        return ERREUR_KPLUS
    return SUCCES


def creer_site_web(chemin, dossier):
    from pathlib import Path
    from .site import ErreurSite, creer_site
    source, probleme = lire_fichier(chemin)
    if probleme:
        ecrire_erreur(probleme)
        return ERREUR_UTILISATION
    programme = Path(chemin)
    cible = Path(dossier) if dossier else programme.with_name(programme.stem + "_site")
    try:
        creer_site(source, cible, titre=programme.stem.replace("_", " "))
    except ErreurKPlus as e:
        ecrire_erreur(formater_erreur(e, source))
        return ERREUR_KPLUS
    except ErreurSite as e:
        ecrire_erreur(f"Erreur : {e}")
        return ERREUR_UTILISATION
    print(f"Site créé dans le dossier : {cible}")
    print("Pour l'essayer sur cet ordinateur :")
    print(f"    python -m http.server --directory \"{cible}\"")
    print("puis ouvrez http://localhost:8000 dans le navigateur.")
    print("Pour le publier : envoyez le contenu du dossier chez un hébergeur de sites statiques "
          "(GitHub Pages, Netlify…). Les visiteurs ont besoin d'Internet au premier chargement.")
    return SUCCES


def lancer_serveur(argv):
    """kplus --serveur programme.kplus [--port N] [--production]"""
    import os
    from pathlib import Path
    from .serveur import lancer
    chemin, port, production = None, None, False
    restants = list(argv)
    while restants:
        option = restants.pop(0)
        if option == "--production":
            production = True
        elif option == "--port":
            if not restants or not restants[0].isdigit() or not 1 <= int(restants[0]) <= 65535:
                ecrire_erreur("Erreur : --port attend un numéro entre 1 et 65535. Exemple : --port 5000")
                return ERREUR_UTILISATION
            port = int(restants.pop(0))
        elif option.startswith("-") or chemin is not None:
            ecrire_erreur(f"Erreur : option inattendue « {option} ».\n"
                          "Exemple : kplus --serveur site.kplus --port 5000")
            return ERREUR_UTILISATION
        else:
            chemin = option
    if chemin is None:
        ecrire_erreur("Erreur : --serveur attend un programme. Exemple : kplus --serveur site.kplus")
        return ERREUR_UTILISATION
    source, probleme = lire_fichier(chemin)
    if probleme:
        ecrire_erreur(probleme)
        return ERREUR_UTILISATION
    if port is None:
        port = int(os.environ.get("PORT", "8000")) if production else 8000
    hote = "0.0.0.0" if production else "127.0.0.1"
    interpreteur = Interpreteur()
    interpreteur.source = source
    interpreteur.production = production
    interpreteur.fichier_donnees = str(Path(chemin).with_suffix(".donnees"))
    try:
        interpreteur.executer_programme(analyser(source))
    except ErreurKPlus as e:
        ecrire_erreur(formater_erreur(e, source))
        return ERREUR_KPLUS
    except SignalQuitter as q:
        return q.code
    except Interruption:
        ecrire_erreur("\nProgramme interrompu.")
        return INTERRUPTION
    app = interpreteur.serveur
    if app is None:
        ecrire_erreur("Erreur : ce programme n'est pas un site côté serveur : "
                      "ajoutez « utiliser serveur » au début du programme.")
        return ERREUR_KPLUS
    if not app.pages:
        ecrire_erreur("Erreur : ce site n'a aucune page. Déclarez-en une, par exemple : "
                      "page(\"/\", accueil)")
        return ERREUR_KPLUS

    def pret(_):
        adresse = f"http://localhost:{port}"
        print(f"Site K+ en ligne : {adresse}" + ("  (mode production)" if production else ""))
        print(f"Données enregistrées dans : {interpreteur.fichier_donnees}")
        print("Pages : " + ", ".join(r.adresse for r in app.pages))
        print("Arrêter le serveur : Ctrl+C")
        sys.stdout.flush()

    try:
        lancer(app, hote, port, pret=pret)
    except OSError as e:
        ecrire_erreur(f"Erreur : impossible d'ouvrir le port {port} ({e.strerror}). "
                      f"Essayez un autre port : --port 5000")
        return ERREUR_UTILISATION
    except KeyboardInterrupt:
        print("\nServeur arrêté.")
    finally:
        app.donnees.fermer()
    return SUCCES


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
    if premier == "--scenario":
        if len(argv) != 3:
            ecrire_erreur("Erreur : --scenario attend un programme web et un fichier de scénario.\n"
                          "Exemple : kplus --scenario site.kplus visite.txt")
            return ERREUR_UTILISATION
        return jouer_scenario(argv[1], argv[2])
    if premier == "--site":
        if len(argv) not in (2, 3):
            ecrire_erreur("Erreur : --site attend un programme, et éventuellement un dossier.\n"
                          "Exemple : kplus --site mon_site.kplus")
            return ERREUR_UTILISATION
        return creer_site_web(argv[1], argv[2] if len(argv) == 3 else None)
    if premier == "--serveur":
        return lancer_serveur(argv[1:])
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
