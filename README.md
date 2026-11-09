# K+

**K+** est un langage de programmation généraliste dont les mots-clés sont en
français. Les fichiers K+ portent l'extension `.kplus`.

```kplus
afficher("Bienvenue dans K+")

variable age = 20
si age >= 18 alors
    afficher("Tu es majeur")
sinon
    afficher("Tu es mineur")
fin
```

## État du projet

**K+ 0.1 fonctionne et est validé** sur Windows, macOS et Linux :
l'interpréteur exécute réellement les programmes K+.
Les fonctionnalités de la version 0.1 sont toutes implémentées : affichage,
variables, constantes, types, calculs, conditions, boucles, fonctions,
commentaires et gestion des erreurs.

| Phase | État |
|---|---|
| 1. Spécification et grammaire | Terminée |
| 2. Moteur (interpréteur Python) | Terminée |
| 3. Tests et validation de K+ 0.1 | Terminée ([rapport](docs/VALIDATION-0.1.md)) |
| 4. K+ Studio (éditeur web) | Terminée ([guide](studio/README.md)) |
| 5. Multiplateforme | À faire |
| 6. Bibliothèques avancées et IA | À faire |

## Installation

Il faut Python 3.10 ou plus récent (Windows, Linux ou macOS). K+ n'a besoin
d'aucune autre bibliothèque.

```
git clone https://github.com/manassekito17-star/K-.git
cd K-
pip install .
```

## Utilisation

```
kplus exemples/bonjour.kplus            # exécuter un programme
kplus --verifier exemples/bonjour.kplus # vérifier sans exécuter
kplus                                   # mode interactif
kplus --aide
```

Sans installation, depuis le dossier du projet : `python -m kplus exemples/bonjour.kplus`.

## K+ Studio

L'éditeur officiel, dans le navigateur :

```
python studio/construire.py --servir
```

Voir [studio/README.md](studio/README.md).

En ligne, sans installation : **https://manassekito17-star.github.io/K-/**

K+ Studio peut aussi être **installé depuis le navigateur** (bouton
« ⬇ Installer ») : il devient une application avec son icône et fonctionne
sans Internet.

## Extension pour VS Code

Couleurs, erreurs soulignées pendant la saisie et bouton ▶ pour exécuter les
fichiers `.kplus` dans Visual Studio Code.

Téléchargement : **https://manassekito17-star.github.io/K-/telechargements/kplus-vscode.vsix**
(puis, dans VS Code : Extensions → `…` → `Install from VSIX...`).
Voir [vscode/README.md](vscode/README.md).

## Tests

```
python -m unittest                    # tous les tests
python tests/conformite_lanceur.py    # les 48 cas de conformité, avec détail
python tests/robustesse.py 30000      # campagne de robustesse longue
```

Des programmes d'exemple se trouvent dans [`exemples/`](exemples/) :
calculatrice, jeu de devinette, statistiques, nombres premiers, textes,
compte bancaire, grands nombres.

## Documentation

- [Spécification K+ 0.1](docs/specification/specification-kplus-0.1.md)
- [Grammaire formelle (EBNF)](docs/specification/grammaire.ebnf)
- [Cas de test de conformité](tests/conformite/README.md)
- [Architecture du moteur](docs/ARCHITECTURE.md)
- [Rapport de validation K+ 0.1](docs/VALIDATION-0.1.md)
- [Plan de travail](docs/PLAN.md)
- [Feuille de route des versions (proposition)](docs/FEUILLE-DE-ROUTE.md)
