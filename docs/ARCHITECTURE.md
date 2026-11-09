# Architecture de l'interpréteur K+ 0.1

Ce document explique comment le moteur K+ transforme un fichier `.kplus` en
résultat. Il s'adresse aux personnes qui veulent comprendre ou modifier le
moteur.

## Vue d'ensemble

```
 texte source ──► lexer ──► jetons ──► parser ──► AST ──► vérificateur ──► interpréteur ──► résultat
 (.kplus)       lexer.py             parser.py   ast.py   verificateur.py   interpreteur.py
```

1. **Lexer** (`lexer.py`) : découpe le texte en jetons (`variable`, `x`, `=`,
   `5`...). Il ignore les espaces et les commentaires, et signale les
   caractères inconnus (`ErreurLexicale`).
2. **Parser** (`parser.py`) : vérifie que les jetons respectent la grammaire
   (`docs/specification/grammaire.ebnf`) et construit l'arbre syntaxique.
   Chaque règle de la grammaire correspond à une méthode (descente récursive).
3. **AST** (`ast.py`) : l'arbre syntaxique. Chaque nœud (`Si`, `Pour`,
   `OperationBinaire`...) garde sa ligne et sa colonne.
4. **Vérificateur** (`verificateur.py`) : contrôles faits avant l'exécution
   (`retourner` hors fonction, `arreter` hors boucle, expression sans effet).
5. **Interpréteur** (`interpreteur.py`) : parcourt l'arbre et exécute chaque
   nœud.

Les étapes 1 à 4 sont terminées **avant** la première instruction exécutée :
une erreur de syntaxe à la ligne 50 empêche d'exécuter la ligne 1.

## Modules

| Module | Rôle |
|---|---|
| `jetons.py` | Types de jetons, mots-clés, symboles, préparation du texte (BOM, fins de ligne, Unicode NFC). |
| `lexer.py` | Analyse lexicale. |
| `ast.py` | Définition des nœuds de l'arbre. |
| `parser.py` | Analyse syntaxique. |
| `verificateur.py` | Contrôles statiques. |
| `valeurs.py` | Représentation des valeurs K+, `type()`, affichage, égalité. |
| `operations.py` | Opérateurs : `+ - * / % ^`, comparaisons, accès `[ ]`. |
| `environnement.py` | Gestionnaire des variables : portées imbriquées, constantes. |
| `natives.py` | Fonctions natives (`afficher`, `longueur`...). |
| `interpreteur.py` | Exécution de l'arbre, appels de fonctions, pile d'appels. |
| `erreurs.py` | Catégories d'erreurs, signaux de contrôle, mise en forme des messages. |
| `pile.py` | Exécution avec une grande pile (voir plus bas). |
| `cli.py` | Commande `kplus` et mode interactif. |
| `__init__.py` | Fonctions publiques `analyser()` et `executer()`. |

`operations.py` et `pile.py` n'étaient pas dans le plan initial :
`operations.py` sépare les règles de calcul de l'interpréteur pour les tester
et les réutiliser (futur compilateur) ; `pile.py` corrige un problème réel
découvert pendant les tests (voir « Récursion »).

## Correspondance des types

| Type K+ | Représentation Python |
|---|---|
| entier | `int` (précision illimitée) |
| décimal | `float` (IEEE 754 double) |
| texte | `str` |
| booléen | `bool` |
| nul | `None` |
| liste | `list` |
| fonction | `FonctionUtilisateur` / `FonctionNative` |

En Python, `bool` est un sous-type de `int` (`True == 1`). Le moteur teste
donc toujours `type(v) is int`, jamais `isinstance(v, int)`, pour que
`vrai + 1` reste une erreur comme le veut la spécification.

## Portées

Chaque bloc crée un `Environnement` dont le parent est le bloc englobant.
Une fonction garde l'environnement où elle a été définie (`fermeture`) : c'est
ce qui permet les compteurs de la spécification §7. Les boucles créent un
nouvel environnement à chaque tour, ce qui permet `variable x = ...` dans le
corps d'une boucle.

## Erreurs et positions

Les erreurs d'exécution sont des exceptions Python (`ErreurType`,
`ErreurNom`...). Une opération qui échoue (par exemple dans `operations.py`)
lève l'erreur sans position ; la méthode `evaluer` ou `executer` du nœud le
plus proche y ajoute sa ligne et sa colonne. Quand une erreur traverse un
appel de fonction, l'appel est ajouté à `erreur.pile`.

`retourner`, `arreter`, `continuer` et `quitter()` utilisent aussi des
exceptions (`SignalRetour`...), mais ce ne sont **pas** des erreurs :
`essayer ... attraper` ne les intercepte pas.

## Récursion

L'interpréteur est récursif : un appel de fonction K+ utilise environ 7
niveaux de la pile Python, une parenthèse imbriquée environ 12. La limite
par défaut de Python (1000 niveaux) aurait donc limité K+ à environ 140 appels
imbriqués au lieu des 1000 promis. `pile.py` exécute l'analyse et l'exécution
dans un fil doté d'une grande pile (255, 128 ou 64 Mio selon ce que le
système accepte : Windows refuse 256 Mio) et relève la limite de Python
pendant l'exécution. Si aucune grande pile n'est possible, une récursion trop
profonde donne une `ErreurRecursion`, jamais un plantage. Environ 1000
niveaux de parenthèses imbriquées sont garantis. La limite
K+ (1000 appels) est contrôlée séparément par l'interpréteur et produit une
`ErreurRecursion` claire.

Ctrl+C : le fil principal reçoit l'interruption et demande à l'interpréteur de
s'arrêter. L'interpréteur vérifie cette demande avant chaque instruction et à
chaque tour de boucle.

## Sécurité

- Pas d'accès aux fichiers, au réseau ni au système en K+ 0.1 : le seul canal
  d'entrée-sortie est `afficher` / `demander`.
- `a ^ b` entre entiers est refusé si le résultat dépasse environ un million de
  bits (protection contre l'épuisement de la mémoire).
- Les décimaux infinis ou indéfinis (`inf`, `NaN`) sont refusés.

## Vers un compilateur natif

Le lexer, le parser, l'AST et le vérificateur ne dépendent pas de
l'interpréteur. Un futur compilateur (bytecode, C, LLVM...) pourra réutiliser
ces quatre étapes et remplacer seulement `interpreteur.py`. Point d'attention :
les entiers de précision illimitée devront être fournis par une bibliothèque de
grands entiers.

## Tests

| Fichier | Contenu |
|---|---|
| `tests/test_lexer.py` | Jetons, nombres, textes, commentaires, positions. |
| `tests/test_parser.py` | Priorités, blocs, erreurs de syntaxe et leurs lignes. |
| `tests/test_interpreteur.py` | Calculs, portées, boucles, fonctions, natives, erreurs. |
| `tests/test_erreurs.py` | Format exact des messages d'erreur. |
| `tests/test_cli.py` | Commande `kplus` : codes de sortie, mode interactif. |
| `tests/test_conformite.py` | Les 48 cas de `tests/conformite/`. |

Lancer tous les tests : `python -m unittest` (à la racine du projet).
