# Plan de travail K+

| Phase | Contenu | État |
|---|---|---|
| 1 | Spécification technique et grammaire | **Terminée — en attente de validation** |
| 2 | Développement du moteur (interpréteur Python) | À faire |
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
| `tests/conformite/*.kplus` / `.sortie` / `.erreur` | 48 cas de test de conformité (non exécutés : pas encore de moteur). |
| `exemples/bonjour.kplus` | Le programme d'exemple du cahier des charges. |

### Décisions de conception à valider

Ces choix ont été faits pour la 0.1. Ils peuvent être changés **maintenant**
facilement ; après la Phase 2, chaque changement coûtera du code et des tests.

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

## Phase 2 — Moteur (prévu, rien n'est encore écrit)

Langage d'implémentation : Python ≥ 3.10, **bibliothèque standard uniquement**
(aucune installation supplémentaire pour l'utilisateur).

Fichiers prévus :

```
kplus/
├── __init__.py          version du langage
├── __main__.py          permet « python -m kplus programme.kplus »
├── jetons.py            types de jetons et mots-clés
├── lexer.py             analyse lexicale : texte → jetons
├── ast.py               définition des nœuds de l'arbre syntaxique
├── parser.py            analyse syntaxique : jetons → AST
├── verificateur.py      contrôles statiques (retourner/arreter mal placés…)
├── valeurs.py           représentation des valeurs K+ (fonctions, listes…)
├── environnement.py     gestionnaire des variables et des portées
├── natives.py           fonctions natives (afficher, longueur…)
├── interpreteur.py      exécution de l'AST
├── erreurs.py           catégories d'erreurs et mise en forme des messages
└── cli.py               interface en ligne de commande et mode interactif
pyproject.toml           installation de la commande « kplus »
```

Pourquoi cette découpe : chaque étape (lexer → parser → AST → interpréteur) est
indépendante. Le futur compilateur natif pourra réutiliser `lexer`, `parser`,
`ast` et `verificateur` et remplacer uniquement `interpreteur`.

## Phase 3 — Tests prévus

- **Tests unitaires** (`unittest`, inclus dans Python) : un fichier par
  composant (`test_lexer.py`, `test_parser.py`, `test_interpreteur.py`,
  `test_erreurs.py`, `test_cli.py`).
- **Tests de conformité** : un lanceur exécute les 48 cas de
  `tests/conformite/` et compare sortie, code de sortie et erreur.
- **Intégration continue** : exécution des tests sur Windows, Linux et macOS
  (GitHub Actions) — à confirmer avec le responsable du projet.
