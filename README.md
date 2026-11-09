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

> ⚠️ **K+ n'est pas encore utilisable.** Seule la **Phase 1 (spécification)**
> est réalisée. Le moteur (interpréteur) n'a pas encore été écrit : aucun
> programme K+ ne peut être exécuté pour l'instant.

| Phase | État |
|---|---|
| 1. Spécification et grammaire | Terminée (en attente de validation) |
| 2. Moteur (interpréteur Python) | À faire |
| 3. Tests et validation de K+ 0.1 | À faire |
| 4. K+ Studio | À faire |
| 5. Multiplateforme | À faire |
| 6. Bibliothèques avancées et IA | À faire |

## Documentation

- [Spécification K+ 0.1](docs/specification/specification-kplus-0.1.md)
- [Grammaire formelle (EBNF)](docs/specification/grammaire.ebnf)
- [Cas de test de conformité](tests/conformite/README.md)
- [Plan de travail](docs/PLAN.md)
