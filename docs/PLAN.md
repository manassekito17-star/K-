# Plan de travail K+

| Phase | Contenu | État |
|---|---|---|
| 1 | Spécification technique et grammaire | Terminée (décisions validées) |
| 2 | Développement du moteur (interpréteur Python) | **Terminée** |
| 3 | Tests et validation de K+ 0.1 | À faire |
| 4 | K+ Studio (éditeur) | À faire |
| 5 | Évolution multiplateforme (paquets, compilateur natif) | À faire |
| 6 | Bibliothèques avancées et intelligence artificielle | À faire |

---

## Phase 1 — Spécification (livrée)

| Fichier | Rôle |
|---|---|
| `docs/specification/specification-kplus-0.1.md` | Spécification officielle : règles lexicales, types, opérateurs, syntaxe, portée, fonctions natives, erreurs, ligne de commande. |
| `docs/specification/grammaire.ebnf` | Grammaire formelle en EBNF. |
| `tests/conformite/*.kplus` / `.sortie` / `.erreur` | 48 cas de test de conformité (48/48 réussis depuis la Phase 2). |
| `exemples/bonjour.kplus` | Le programme d'exemple du cahier des charges. |

### Décisions de conception (validées)

Ces choix ont été validés par le responsable du projet avant la Phase 2.

1. **Indices à partir de 0** (comme Python/C/JavaScript), pas de 1.
2. **Pas de conversion implicite** : `"Âge : " + 20` est une erreur ; on écrit
   `texte(20)`.
3. **Conditions strictement booléennes** : `si 1 alors` est refusé.
4. **`/` donne toujours un décimal** : `10 / 2` vaut `5.0`.
5. **Mot-clé `à` avec accent obligatoire** dans `pour i de 1 à 10`, pour que `a`
   reste un nom de variable possible.
6. **Portée par blocs** : une variable déclarée dans un `si` disparaît après
   son `fin`.
7. **Une fonction n'existe qu'à partir de sa ligne de déclaration.**
8. **Guillemets typographiques `“ ”` acceptés** en plus de `" "`.
9. **Commentaires** : `#` (une ligne) et `/* ... */` (plusieurs lignes).
10. **Puissance avec `^`**, modulo avec `%`.
11. **Une ligne avec une expression sans effet** (`x == 5`) est une erreur.

---

## Phase 2 — Moteur (livrée)

Interpréteur en Python ≥ 3.10, **bibliothèque standard uniquement**.
Détails : [`ARCHITECTURE.md`](ARCHITECTURE.md).

```
kplus/
├── __init__.py          analyser() et executer()
├── __main__.py          « python -m kplus programme.kplus »
├── jetons.py            types de jetons et mots-clés
├── lexer.py             analyse lexicale : texte → jetons
├── ast.py               nœuds de l'arbre syntaxique
├── parser.py            analyse syntaxique : jetons → AST
├── verificateur.py      contrôles statiques
├── valeurs.py           valeurs K+, affichage, égalité
├── operations.py        opérateurs (ajouté : voir ARCHITECTURE.md)
├── environnement.py     variables et portées
├── natives.py           fonctions natives
├── interpreteur.py      exécution de l'AST
├── erreurs.py           erreurs et messages
├── pile.py              grande pile pour la récursion (ajouté)
└── cli.py               commande « kplus » et mode interactif
pyproject.toml           installation de la commande « kplus »
```

Résultats de la Phase 2 :

- 48/48 cas de conformité réussis ;
- 82 tests unitaires et d'intégration réussis ;
- suite de tests réussie sous Python 3.10, 3.11, 3.12 et 3.13 (Linux) ;
- installation par `pip install .` vérifiée dans un environnement isolé.

Non vérifié à ce stade : exécution réelle sous Windows et macOS (prévu en
Phase 3 via l'intégration continue).

## Phase 3 — Tests prévus

Déjà en place depuis la Phase 2 : tests unitaires par composant et lanceur
des 48 cas de conformité. La Phase 3 ajoutera :

- **Programmes plus complets** (exemples réalistes : calculatrice, jeux de
  devinette, statistiques sur des listes) pour éprouver le langage ;
- **Tests de robustesse** : programmes malformés générés automatiquement, pour
  vérifier que K+ affiche toujours une erreur claire et jamais d'« erreur
  interne » ;
- **Intégration continue** : exécution des tests sur Windows, Linux et macOS
  (GitHub Actions) — à confirmer avec le responsable du projet.
