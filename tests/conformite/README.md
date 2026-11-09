# Cas de test de conformité K+ 0.1

> **Statut : non exécutés.** Ces cas décrivent le comportement attendu défini par
> la [spécification](../../docs/specification/specification-kplus-0.1.md).
> Ils seront lancés automatiquement en Phase 3, quand le moteur existera.

## Format

Chaque cas `NNN_nom` est composé de :

| Fichier | Contenu | Obligatoire |
|---|---|---|
| `NNN_nom.kplus` | Le programme K+ à exécuter. | oui |
| `NNN_nom.sortie` | La sortie standard **exacte** attendue (peut être vide). | oui |
| `NNN_nom.erreur` | Une seule ligne : `<Catégorie> ligne <N>`. Présent seulement si le programme doit s'arrêter sur une erreur. | non |

Règles de validation qu'appliquera le lanceur de tests :

1. Exécuter `kplus NNN_nom.kplus` sans entrée clavier.
2. La sortie standard doit être **identique** au contenu de `.sortie`.
3. Sans fichier `.erreur` : le code de sortie doit être `0` et la sortie
   d'erreur vide.
4. Avec un fichier `.erreur` : le code de sortie doit être `1`, et la sortie
   d'erreur doit contenir le nom affiché de la catégorie
   (ex. `Erreur de type`) et `(ligne N,`.
5. Les fichiers sont en UTF-8 avec des fins de ligne `\n`.

## Liste des cas

| Cas | Vérifie | Résultat attendu |
|---|---|---|
| 001 | `afficher` d'un texte | succès |
| 002 | `afficher` de plusieurs valeurs, ligne vide, liste | succès |
| 003 | guillemets typographiques `“ ”` | succès |
| 004 | séquences `\n \t \" \\` | succès |
| 005 | variables, accents, sensibilité à la casse | succès |
| 006 | constantes (contenu de liste modifiable) | succès |
| 007 | réaffectation de constante | ErreurConstante l.3 |
| 008 | variable non déclarée | ErreurNom l.2 |
| 009 | redéclaration dans la même portée | ErreurNom l.2 |
| 010 | `type()` sur chaque type | succès |
| 011 | conversions `texte`, `entier`, `decimal` | succès |
| 012 | conversion impossible | ErreurValeur l.2 |
| 013 | priorités, division, modulo, puissance, grands entiers | succès |
| 014 | division par zéro | ErreurDivisionParZero l.2 |
| 015 | concaténation de textes et de listes | succès |
| 016 | texte + entier interdit | ErreurType l.2 |
| 017 | comparaisons | succès |
| 018 | `et` / `ou` / `non`, court-circuit | succès |
| 019 | condition non booléenne | ErreurType l.2 |
| 020 | `si` / `sinon` | succès |
| 021 | `sinon si` | succès |
| 022 | `tant que` | succès |
| 023 | `pour` (pas, sens, zéro tour, variable de boucle) | succès |
| 024 | `pour chaque` sur liste et texte, copie | succès |
| 025 | `arreter`, `arrêter`, `continuer` | succès |
| 026 | fonctions, fonctions en argument | succès |
| 027 | récursivité | succès |
| 028 | fonction sans `retourner` → `nul` | succès |
| 029 | portée des blocs, masquage, fermetures | ErreurNom l.21 |
| 030 | mauvais nombre d'arguments | ErreurType l.4 |
| 031 | récursion infinie | ErreurRecursion l.2 |
| 032 | commentaires `#` et `/* */` | succès |
| 033 | `essayer` / `attraper` / `lever` | succès |
| 034 | `lever` non attrapé | ErreurUtilisateur l.2 |
| 035 | `fin` manquant (rien ne s'exécute) | ErreurSyntaxe l.2 |
| 036 | caractère inconnu | ErreurLexicale l.2 |
| 037 | `retourner` hors fonction | ErreurSyntaxe l.2 |
| 038 | listes : indices, modification, références | succès |
| 039 | indice hors limites | ErreurIndex l.3 |
| 040 | programme complet du cahier des charges | succès |
| 041 | `absolu`, `racine`, `arrondir` | succès |
| 042 | comparaison enchaînée `1 < 2 < 3` | ErreurSyntaxe l.2 |
| 043 | expression sans effet `x == 5` | ErreurSyntaxe l.2 |
| 044 | nom de fonction native protégé | ErreurNom l.1 |
| 045 | `pas 0` | ErreurValeur l.1 |
| 046 | `arreter` hors boucle | ErreurSyntaxe l.2 |
| 047 | texte non fermé | ErreurLexicale l.2 |
| 048 | expression sur plusieurs lignes, virgule finale | succès |
