# K+ pour Visual Studio Code

Extension officielle du langage **K+**, le langage de programmation en
français.

## Fonctionnalités

- **Couleurs** : mots-clés (`si`, `alors`, `fin`…), fonctions, textes,
  nombres, commentaires.
- **Correction pendant la saisie** : les erreurs sont soulignées en rouge ;
  le message et le conseil de K+ s'affichent au survol et dans l'onglet
  **Problèmes**. Les erreurs viennent du vrai moteur K+ : ce sont exactement
  celles que la commande `kplus` afficherait.
- **Exécution** : bouton **▶** en haut à droite de l'éditeur (ou
  **Ctrl+Entrée**) ; le programme tourne dans le terminal **K+** de VS Code,
  où `demander()` fonctionne normalement.
- **Raccourcis d'écriture** : tapez `si`, `sisinon`, `tantque`, `pour`,
  `pourchaque`, `fonction`, `essayer`… puis **Tab**.
- **Confort** : retrait automatique après `alors` / `faire`, **Ctrl+/** pour
  commenter avec `#`, parenthèses et guillemets fermés automatiquement.

## Installation

1. Téléchargez le fichier de l'extension :
   **https://manassekito17-star.github.io/K-/telechargements/kplus-vscode.vsix**
2. Dans VS Code, ouvrez la vue **Extensions** (icône des carrés à gauche, ou
   **Ctrl+Maj+X**).
3. Cliquez sur **`…`** en haut de cette vue, puis sur **`Install from VSIX...`**
   et choisissez le fichier téléchargé.

Ou, dans un terminal : `code --install-extension kplus-vscode.vsix`

### Python est nécessaire

La correction et l'exécution utilisent **Python 3.10 ou plus récent**
(https://www.python.org/downloads/ ; sous Windows, cochez « Add Python to
PATH » pendant l'installation). Sans Python, les couleurs fonctionnent et
l'extension explique comment l'installer.

L'extension trouve Python toute seule (`py -3`, `python3` ou `python`). Sinon,
indiquez son chemin dans le réglage **K+ › Chemin Python**.

## Réglages

| Réglage | Rôle |
|---|---|
| `kplus.cheminPython` | chemin de Python (vide = automatique) |
| `kplus.correctionPendantSaisie` | souligner les erreurs pendant la saisie (activé par défaut) |

## Ce que la correction détecte

Pendant la saisie, l'extension signale les erreurs **lexicales** et de
**syntaxe** (par exemple un `fin` manquant, un caractère interdit, `x == 5`
seul sur une ligne), sans exécuter le programme. Les erreurs qui dépendent des
valeurs (division par zéro, variable inconnue…) apparaissent à l'exécution,
dans le terminal, avec leur numéro de ligne.

## Liens

- K+ Studio en ligne : https://manassekito17-star.github.io/K-/
- Code source et documentation : https://github.com/manassekito17-star/K-
