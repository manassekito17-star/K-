# Rapport de validation — K+ 0.1

Ce rapport résume la Phase 3 : ce qui a été vérifié, comment, et ce qui
reste limité dans la version 0.1.

## 1. Résultat

**K+ 0.1 est validé** sur Windows, macOS et Linux, avec Python 3.10 et 3.13
(intégration continue GitHub Actions), et localement avec Python 3.10 à 3.13.

Les dix fonctionnalités du cahier des charges sont implémentées et testées.

## 2. Méthodes de vérification

| Méthode | Quantité | Ce qu'elle vérifie |
|---|---|---|
| Cas de conformité (`tests/conformite/`) | 48 cas | Chaque règle de la spécification : sortie exacte, catégorie d'erreur et numéro de ligne. |
| Tests unitaires et d'intégration | 88 tests (des centaines de vérifications) | Chaque composant : lexer, parser, interpréteur, erreurs, ligne de commande. |
| Programmes d'exemple (`exemples/`) | 8 programmes, 9 scénarios | Programmes réalistes ; résultats recalculés indépendamment en Python avant d'être figés. |
| Robustesse (`tests/robustesse.py`) | plus de 300 000 programmes aléatoires ou abîmés (dont 60 000 sous Python 3.10) | K+ ne plante jamais : il réussit ou affiche une erreur K+ claire. |
| Comparaison avec Python | 53 000 calculs aléatoires | Les calculs numériques de K+ donnent exactement le même résultat que Python (mêmes règles pour `%`, `/`, `^`, les décimaux). |
| Intégration continue | 6 configurations, toutes réussies | Windows, macOS, Linux × Python 3.10 et 3.13, à chaque envoi de code. |

Les testeurs eux-mêmes ont été vérifiés : une panne simulée du moteur et un
résultat attendu volontairement faux ont bien été détectés.

## 3. Fonctionnalités du cahier des charges

| # | Fonctionnalité | État | Preuves principales |
|---|---|---|---|
| 1 | Affichage | Validé | cas 001–004, 048 |
| 2 | Variables | Validé | cas 005, 008, 009, 043, 044 |
| 3 | Constantes | Validé | cas 006, 007 |
| 4 | Types de données | Validé | cas 010–012, 038, 039, 047 |
| 5 | Opérations mathématiques | Validé | cas 013–017, 041 ; comparaison avec Python |
| 6 | Conditions | Validé | cas 018–021, 042 |
| 7 | Boucles | Validé | cas 022–025, 045, 046 |
| 8 | Fonctions | Validé | cas 026–031, 037 ; récursion jusqu'à 999 appels |
| 9 | Commentaires | Validé | cas 032 |
| 10 | Gestion des erreurs | Validé | cas 033–036 et tous les cas `.erreur` |

## 4. Problèmes trouvés pendant la Phase 3

| Problème | Gravité | Statut |
|---|---|---|
| **Plantage sous Windows + Python 3.10** lors d'une récursion profonde : la pile de 256 Mio demandée était refusée en silence par Windows. | Élevée | **Corrigé** : plusieurs tailles de pile sont essayées ; une récursion trop profonde donne toujours une `ErreurRecursion`, jamais un plantage. Test ajouté qui simule la limite de Windows. |
| La limite de récursion de Python n'était pas restaurée après une exécution. | Moyenne | **Corrigé**, test ajouté. |
| Pas d'opérateur de division entière : `t[n / 2]` est refusé car `n / 2` est un décimal. Il faut écrire `entier(n / 2)`. Découvert en écrivant `exemples/statistiques.kplus`. | Confort | Conforme à la spécification. **Proposition pour K+ 0.2** : un opérateur de division entière. |

## 5. Limites connues de K+ 0.1

- Les expressions peuvent être imbriquées sur environ 1000 niveaux de
  parenthèses ; au-delà, `ErreurRecursion` (jamais de plantage).
- `entier(n / 2)` passe par un décimal : pour des entiers plus grands
  que 2⁵³ (environ 9 millions de milliards), le résultat peut être imprécis.
- Pas de nombres aléatoires, de fichiers, de date ni de dictionnaires
  (spécification §11).
- `demander()` ne propose pas l'édition de ligne (flèches, historique).
- Vitesse indicative : une boucle de 300 000 tours avec un calcul prend
  environ 0,4 seconde. C'est suffisant pour apprendre et pour de petits
  programmes, pas pour du calcul intensif (prévu avec le compilateur, Phase 5).

## 6. Reproduire la validation

```
python -m unittest                       # tous les tests (environ 10 secondes)
python tests/conformite_lanceur.py       # détail des 48 cas de conformité
python tests/robustesse.py 30000 1       # campagne de robustesse longue
```
