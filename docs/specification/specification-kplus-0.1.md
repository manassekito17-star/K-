# Spécification technique officielle — K+ 0.1

> **Statut : PROJET DE SPÉCIFICATION (Phase 1).**
> Ce document décrit ce que K+ 0.1 *devra* faire. **Aucun moteur K+ n'existe
> encore** : rien de ce qui est écrit ici n'est exécutable tant que la Phase 2
> (développement de l'interpréteur) et la Phase 3 (tests) ne sont pas terminées.

| Élément | Valeur |
|---|---|
| Nom du langage | K+ |
| Version spécifiée | 0.1 |
| Extension des fichiers | `.kplus` |
| Encodage des fichiers | UTF-8 (un BOM éventuel est ignoré) |
| Langue des mots-clés | Français |
| Implémentation de référence prévue | Interpréteur en Python ≥ 3.10, sans dépendance externe |
| Plateformes visées | Windows, Linux, macOS |

Documents associés :

- [`grammaire.ebnf`](grammaire.ebnf) — grammaire formelle (EBNF).
- [`../../tests/conformite/`](../../tests/conformite/) — cas de test de conformité.
- [`../PLAN.md`](../PLAN.md) — plan de travail par phases.

---

## Sommaire

1. [Principes de conception](#1-principes-de-conception)
2. [Structure d'un programme](#2-structure-dun-programme)
3. [Règles lexicales](#3-règles-lexicales)
4. [Types de données](#4-types-de-données)
5. [Opérateurs](#5-opérateurs)
6. [Instructions et règles de syntaxe](#6-instructions-et-règles-de-syntaxe)
7. [Portée des noms](#7-portée-des-noms)
8. [Fonctions natives](#8-fonctions-natives)
9. [Gestion des erreurs](#9-gestion-des-erreurs)
10. [Interface en ligne de commande](#10-interface-en-ligne-de-commande)
11. [Hors du périmètre de K+ 0.1](#11-hors-du-périmètre-de-k-01)
12. [Cas de test](#12-cas-de-test)

---

## 1. Principes de conception

Ces principes servent d'arbitre quand un choix de conception se présente.

1. **Lisible en français.** Un programme K+ doit pouvoir être lu à voix haute
   par un francophone : `si age >= 18 alors`, `tant que x < 10 faire`.
2. **Pas de surprise.** K+ préfère signaler une erreur claire plutôt que
   deviner. Exemples : `"Âge : " + 20` est une erreur (pas de conversion
   cachée) ; une condition doit être un vrai booléen.
3. **Erreurs utiles.** Chaque erreur indique sa catégorie, la ligne, la colonne,
   la ligne de code fautive et, si possible, un conseil.
4. **Tout ou rien à l'analyse.** Le fichier entier est analysé avant
   l'exécution : une erreur de syntaxe empêche l'exécution de *toute* ligne.
5. **Évolutif.** L'implémentation sépare clairement analyse lexicale, analyse
   syntaxique, arbre syntaxique (AST) et exécution, pour permettre plus tard un
   compilateur natif qui réutilise le même AST.

---

## 2. Structure d'un programme

- Un programme est un fichier texte `.kplus` contenant une suite
  d'**instructions**, exécutées de haut en bas.
- **Une instruction par ligne.** La fin de ligne termine l'instruction.
- Les **blocs** (`si`, `tant que`, `pour`, `fonction`, `essayer`) se terminent
  par le mot-clé **`fin`**.
- L'**indentation n'a pas de signification** : elle est recommandée (4 espaces)
  pour la lisibilité, mais le moteur l'ignore.
- Les lignes vides et les commentaires sont autorisés partout.
- Il n'y a pas de fonction « principale » : le fichier est le programme.

Exemple de référence (tiré du cahier des charges) :

```kplus
afficher("Bienvenue dans K+")

variable nom = "Manassé"
variable age = 20

si age >= 18 alors
    afficher("Tu es majeur")
sinon
    afficher("Tu es mineur")
fin

fonction additionner(a, b)
    retourner a + b
fin

variable resultat = additionner(10, 20)
afficher(resultat)
```

Sortie attendue :

```
Bienvenue dans K+
Tu es majeur
30
```

---

## 3. Règles lexicales

L'analyse lexicale (le *lexer*) découpe le texte source en **jetons**
(*tokens*). Avant tout traitement, le texte est normalisé en Unicode **NFC** :
ainsi `à` tapé comme un seul caractère ou comme `a` + accent combinant est
reconnu de la même façon.

### 3.1 Espaces et fins de ligne

| Élément | Règle |
|---|---|
| Espace, tabulation | Séparent les jetons, sinon ignorés. |
| Fin de ligne (`\n`, `\r\n`, `\r`) | Produit un jeton `NL` (fin d'instruction). |
| Fin de ligne **à l'intérieur** de `( )` ou `[ ]` | Ignorée : une expression peut s'étaler sur plusieurs lignes entre parenthèses ou crochets. |
| Plusieurs `NL` consécutifs | Équivalents à un seul. |

### 3.2 Commentaires

```kplus
# Commentaire jusqu'à la fin de la ligne

/* Commentaire
   sur plusieurs lignes */
```

- `#` commence un commentaire qui va jusqu'à la fin de la ligne.
- `/* ... */` délimite un commentaire multiligne. Les commentaires multilignes
  **ne s'imbriquent pas**. Un `/*` jamais fermé est une `ErreurLexicale`.
- Un `#` ou `/*` à l'intérieur d'un texte (`"..."`) ne commence pas un
  commentaire.

### 3.3 Identifiants (noms)

```
identifiant = (lettre | "_") , { lettre | chiffre | "_" }
```

- `lettre` désigne toute lettre Unicode : `âge`, `prénom`, `résultat` sont
  valides.
- Les identifiants sont **sensibles à la casse** : `Nom` et `nom` sont deux noms
  différents.
- Un identifiant ne peut pas être un mot-clé réservé.

### 3.4 Mots-clés réservés

| Catégorie | Mots-clés |
|---|---|
| Déclarations | `variable`, `constante`, `fonction` |
| Conditions | `si`, `alors`, `sinon`, `fin` |
| Boucles | `tant`, `que`, `faire`, `pour`, `chaque`, `dans`, `de`, `à`, `pas`, `arreter` (alias `arrêter`), `continuer` |
| Fonctions | `retourner` |
| Erreurs | `essayer`, `attraper`, `lever` |
| Logique | `et`, `ou`, `non` |
| Valeurs | `vrai`, `faux`, `nul` |

Remarques :

- Les mots-clés s'écrivent **en minuscules**. `Si` ou `FIN` sont des
  identifiants ordinaires, pas des mots-clés.
- **Accents** : lorsqu'un mot français s'écrit avec un accent, la forme avec
  accent est acceptée comme alias de la forme sans accent (`arrêter` = `arreter`).
- **Exception `à`** : dans `pour i de 1 à 10`, le mot-clé est `à` **avec
  accent obligatoire**, car `a` sans accent doit rester utilisable comme nom de
  variable (exemple : `fonction additionner(a, b)`).

### 3.5 Littéraux

#### Entiers

```
entier = chiffre , { chiffre | "_" chiffre }
```

Exemples : `0`, `42`, `1_000_000`. Le `_` sert uniquement à la lisibilité.
Les zéros initiaux (`007`) sont interdits (`ErreurLexicale`), sauf `0` seul.

#### Décimaux

```
décimal = entier , "." , chiffres , [ exposant ]
        | entier , exposant
exposant = ("e" | "E") , [ "+" | "-" ] , chiffres
```

Exemples : `3.14`, `0.5`, `2.0`, `1.5e3`, `6e-2`.

- Le séparateur décimal est le **point** (`3.14`), car la virgule sépare les
  arguments : `f(3,14)` appelle `f` avec deux arguments `3` et `14`.
- `.5` et `5.` sont invalides : il faut écrire `0.5` et `5.0`.
- Un nombre négatif s'écrit avec l'opérateur `-` : `-3` est l'opérateur `-`
  appliqué à `3`.

#### Textes (chaînes de caractères)

```kplus
"Bonjour"
“Bonjour”        # guillemets typographiques acceptés
```

- Délimiteurs acceptés : `"` ... `"`, ou `“` ... `”` (guillemets
  typographiques, fréquents quand on copie depuis un traitement de texte ou un
  téléphone). Le texte doit se fermer avec le délimiteur correspondant à
  l'ouverture.
- Un texte tient sur **une seule ligne**. Une fin de ligne avant le guillemet
  fermant est une `ErreurLexicale` (« texte non fermé »).
- Séquences d'échappement :

| Séquence | Signification |
|---|---|
| `\n` | fin de ligne |
| `\t` | tabulation |
| `\"` | guillemet droit |
| `\\` | barre oblique inverse |

  Toute autre séquence `\x` est une `ErreurLexicale`.

#### Booléens et nul

`vrai`, `faux`, `nul` (voir §4).

### 3.6 Symboles

| Symbole | Rôle |
|---|---|
| `(` `)` | groupement, appel de fonction |
| `[` `]` | liste, accès par indice |
| `,` | séparateur |
| `=` | affectation |
| `+` `-` `*` `/` `%` `^` | arithmétique |
| `==` `!=` `<` `<=` `>` `>=` | comparaison |

Tout autre caractère hors texte et commentaire (par exemple `@`, `$`, `;`, `&`)
provoque une `ErreurLexicale` indiquant la ligne et la colonne.

---

## 4. Types de données

K+ est **typé dynamiquement** (une variable peut recevoir une valeur de
n'importe quel type) mais **fortement** (aucune conversion implicite entre
types incompatibles).

| Type (nom renvoyé par `type()`) | Exemples | Description |
|---|---|---|
| `entier` | `0`, `-12`, `1_000_000` | Nombre entier de **précision illimitée** en 0.1. |
| `décimal` | `3.14`, `2.0`, `1e-3` | Nombre à virgule flottante IEEE 754 double précision. |
| `texte` | `"Bonjour"` | Suite de caractères Unicode, **non modifiable**. |
| `booléen` | `vrai`, `faux` | Valeur logique. |
| `nul` | `nul` | Absence de valeur. Seule valeur de son type. |
| `liste` | `[1, "deux", 3.0]` | Suite ordonnée et **modifiable** de valeurs de tout type. |
| `fonction` | `additionner` | Fonction définie par l'utilisateur ou native. |

### 4.1 Règles importantes

- **Indices à partir de 0** : le premier élément de `[10, 20, 30]` est à
  l'indice `0`. Ce choix suit la convention des langages internationaux
  (Python, C, JavaScript) et facilitera l'interopérabilité future (données, IA).
- Un indice négatif ou ≥ longueur provoque une `ErreurIndex`.
- Les textes ne sont pas modifiables : `t[0] = "x"` provoque une `ErreurType`.
  En revanche `t[0]` (lecture) renvoie un texte d'un caractère.
- Les listes sont partagées par référence : après `variable b = a`, modifier
  `b[0]` modifie aussi `a[0]`.
- Les décimaux suivent IEEE 754 : `0.1 + 0.2` vaut `0.30000000000000004`.
  K+ ne cache pas cette réalité.
- Un résultat décimal infini ou indéfini (dépassement, `NaN`) provoque une
  `ErreurValeur` : K+ 0.1 ne manipule jamais `inf` ni `NaN`.
- *Note pour le futur compilateur natif* : la précision illimitée des entiers
  devra être conservée (bibliothèque de grands entiers) ou une décision
  explicite devra être prise en version ultérieure.

### 4.2 Représentation textuelle (utilisée par `afficher` et `texte`)

| Valeur | Affichage |
|---|---|
| entier | chiffres en base 10, signe `-` si négatif : `-42` |
| décimal | forme la plus courte qui redonne exactement la même valeur, toujours avec un point ou un exposant : `5.0`, `3.5`, `0.30000000000000004`. Notation scientifique si l'exposant décimal est < −4 ou ≥ 16 : `1e+16`, `1.5e-05`. |
| texte | le texte lui-même, sans guillemets |
| booléen | `vrai` ou `faux` |
| nul | `nul` |
| liste | `[` éléments séparés par `, ` `]` ; les textes **dans** une liste sont entre guillemets droits : `[1, "a", vrai]` |
| fonction | `<fonction nom>` |

---

## 5. Opérateurs

### 5.1 Priorité et associativité

Du **moins prioritaire** au **plus prioritaire** :

| Niveau | Opérateurs | Associativité |
|---|---|---|
| 1 | `ou` | gauche |
| 2 | `et` | gauche |
| 3 | `non` (unaire) | — |
| 4 | `==` `!=` `<` `<=` `>` `>=` | **non associatif** |
| 5 | `+` `-` | gauche |
| 6 | `*` `/` `%` | gauche |
| 7 | `-` `+` (unaires) | — |
| 8 | `^` (puissance) | **droite** |
| 9 | appel `f(...)`, indice `x[...]` | gauche |

Conséquences :

- `2 + 3 * 4` vaut `14` ; `(2 + 3) * 4` vaut `20`.
- `2 ^ 3 ^ 2` vaut `2 ^ 9` = `512` (associativité à droite).
- `-2 ^ 2` vaut `-(2 ^ 2)` = `-4` (comme en mathématiques).
- `a < b < c` est une **`ErreurSyntaxe`** : il faut écrire `a < b et b < c`.
- `non a == b` signifie `non (a == b)`.

### 5.2 Opérateurs arithmétiques

| Opération | entier, entier | avec au moins un décimal | autres |
|---|---|---|---|
| `a + b` | entier | décimal | texte + texte → concaténation ; liste + liste → nouvelle liste concaténée ; sinon `ErreurType` |
| `a - b` | entier | décimal | `ErreurType` |
| `a * b` | entier | décimal | `ErreurType` |
| `a / b` | **décimal** (toujours) | décimal | `ErreurType` |
| `a % b` | entier | décimal | `ErreurType` |
| `a ^ b` | entier si `b ≥ 0`, décimal si `b < 0` | décimal | `ErreurType` |
| `-a`, `+a` | entier | décimal | `ErreurType` |

- `10 / 2` vaut `5.0` (décimal). Pour une partie entière : `entier(7 / 2)` → `3`.
- **Modulo** : le résultat a le signe du diviseur (`-7 % 3` vaut `2`,
  `7 % -3` vaut `-2`), de sorte que `a == b * plancher(a / b) + a % b`.
- Division ou modulo par zéro (`0` ou `0.0`) : `ErreurDivisionParZero`.
- `0 ^ -1` : `ErreurDivisionParZero`.
- Les booléens **ne sont pas** des nombres : `vrai + 1` est une `ErreurType`.

### 5.3 Opérateurs de comparaison

- `==` et `!=` acceptent **tous** les types et ne provoquent jamais d'erreur :
  - deux nombres (entier ou décimal) se comparent par valeur : `1 == 1.0` → `vrai` ;
  - deux valeurs de types différents (hors nombres) sont différentes :
    `1 == "1"` → `faux` ;
  - deux listes sont égales si elles ont la même longueur et des éléments égaux
    deux à deux ;
  - deux fonctions sont égales seulement s'il s'agit de la même fonction.
- `<`, `<=`, `>`, `>=` acceptent :
  - deux nombres ;
  - deux textes (ordre des points de code Unicode, caractère par caractère).
  Tout autre mélange est une `ErreurType`.
- Le résultat est toujours un `booléen`.

### 5.4 Opérateurs logiques

- `et`, `ou`, `non` n'acceptent **que des booléens** ; sinon `ErreurType`.
- `et` et `ou` sont **court-circuités** : `faux et X` n'évalue pas `X` ;
  `vrai ou X` n'évalue pas `X`.

---

## 6. Instructions et règles de syntaxe

La grammaire formelle complète se trouve dans [`grammaire.ebnf`](grammaire.ebnf).

### 6.1 Déclaration de variable

```kplus
variable nom = "Manassé"
variable age = 20
age = age + 1          # réaffectation : le mot « variable » n'est plus écrit
```

- Une variable **doit être déclarée** avec `variable` avant d'être lue ou
  réaffectée ; sinon `ErreurNom`.
- Une variable doit recevoir une valeur à la déclaration (`variable x` seul est
  une `ErreurSyntaxe` ; écrire `variable x = nul` si besoin).
- Redéclarer un nom **dans la même portée** est une `ErreurNom`.

### 6.2 Déclaration de constante

```kplus
constante PI = 3.14159
```

- Une constante ne peut pas être réaffectée : `PI = 3` provoque une
  `ErreurConstante` au moment de l'exécution de cette ligne.
- Comme pour `variable`, une valeur initiale est obligatoire.
- Une constante protège le **nom**, pas le contenu : si la valeur est une
  liste, ses éléments restent modifiables.
- Convention recommandée (non obligatoire) : noms de constantes en MAJUSCULES.

### 6.3 Affectation

```kplus
x = 5
notes[0] = 18
grille[1][2] = "X"
```

La partie gauche doit être un nom de variable ou un accès par indice. Toute
autre forme (`3 = x`, `f() = 2`) est une `ErreurSyntaxe`.

### 6.4 Instruction-expression

Une ligne contenant seulement une expression n'est autorisée que si
l'expression est un **appel de fonction** (`afficher("ok")`). Une ligne comme
`x == 5` ou `a + b` seule est une `ErreurSyntaxe` (« cette expression n'a aucun
effet »). Cette règle repère une erreur fréquente de débutant : écrire `==` au
lieu de `=`.

*(Exception : dans le mode interactif, voir §10, toute expression est
autorisée et sa valeur est affichée.)*

### 6.5 Condition `si`

```kplus
si note >= 16 alors
    afficher("Très bien")
sinon si note >= 10 alors
    afficher("Admis")
sinon
    afficher("Ajourné")
fin
```

- `alors` est obligatoire et doit être suivi d'une fin de ligne.
- `sinon si` (deux mots, même ligne) enchaîne une nouvelle condition **sans**
  ajouter de `fin` supplémentaire.
- Un seul `fin` termine tout l'ensemble `si / sinon si / sinon`.
- La condition doit être un `booléen`, sinon `ErreurType`
  (`si 1 alors` est refusé).

### 6.6 Boucle `tant que`

```kplus
variable i = 1
tant que i <= 3 faire
    afficher(i)
    i = i + 1
fin
```

La condition est évaluée avant chaque tour ; elle doit être un `booléen`.

### 6.7 Boucle `pour` (compteur)

```kplus
pour i de 1 à 5 faire
    afficher(i)            # 1 2 3 4 5
fin

pour i de 0 à 10 pas 2 faire
    afficher(i)            # 0 2 4 6 8 10
fin

pour i de 3 à 1 pas -1 faire
    afficher(i)            # 3 2 1
fin
```

- Les **deux bornes sont incluses**.
- Les bornes et le `pas` doivent être des **entiers** (`ErreurType` sinon).
  Ils sont évalués **une seule fois**, avant le premier tour.
- `pas` vaut `1` par défaut. Avec un pas positif, la boucle tourne tant que
  `i <= fin` ; avec un pas négatif, tant que `i >= fin`.
  Ainsi `pour i de 5 à 1 faire` (pas implicite 1) ne fait **aucun** tour.
- `pas 0` est une `ErreurValeur`.
- `i` est une nouvelle variable propre au corps de la boucle, recréée à chaque
  tour. La modifier dans le corps n'influence pas le nombre de tours.
  Elle n'existe plus après `fin`.

### 6.8 Boucle `pour chaque`

```kplus
pour chaque fruit dans ["pomme", "kiwi"] faire
    afficher(fruit)
fin

pour chaque lettre dans "abc" faire
    afficher(lettre)
fin
```

- Parcourt une `liste` (élément par élément) ou un `texte` (caractère par
  caractère). Tout autre type : `ErreurType`.
- La boucle parcourt une **copie** de la liste prise au début : ajouter ou
  retirer des éléments pendant la boucle n'en change pas le nombre de tours.

### 6.9 `arreter` et `continuer`

- `arreter` (ou `arrêter`) quitte immédiatement la boucle la plus intérieure.
- `continuer` passe directement au tour suivant.
- Utilisés hors d'une boucle : `ErreurSyntaxe` (détectée avant l'exécution).
- Un corps de fonction définie dans une boucle ne « voit » pas cette boucle :
  `arreter` dans cette fonction (hors boucle propre) est une `ErreurSyntaxe`.

### 6.10 Fonctions

```kplus
fonction additionner(a, b)
    retourner a + b
fin

fonction saluer(nom)
    afficher("Bonjour " + nom)
fin                          # pas de retourner : renvoie nul
```

- Une fonction est déclarée par `fonction nom(paramètres) ... fin`.
  Les parenthèses sont obligatoires, même sans paramètre : `fonction f()`.
- Deux paramètres ne peuvent pas porter le même nom (`ErreurSyntaxe`).
- La déclaration est une instruction ordinaire : la fonction **existe à partir
  de la ligne où elle est déclarée**. L'appeler avant est une `ErreurNom`.
- `retourner expression` renvoie une valeur et termine la fonction.
  `retourner` seul renvoie `nul`. Une fonction qui atteint `fin` renvoie `nul`.
- `retourner` hors d'une fonction : `ErreurSyntaxe`.
- Le nombre d'arguments doit correspondre exactement au nombre de paramètres,
  sinon `ErreurType`.
- Appeler une valeur qui n'est pas une fonction (`5()`) : `ErreurType`.
- Les fonctions sont des valeurs : on peut les mettre dans une variable, les
  passer en argument, en définir à l'intérieur d'autres fonctions.
- Les fonctions **capturent** les variables de l'endroit où elles sont définies
  (fermetures) — voir §7.
- **Récursivité** autorisée, avec une profondeur maximale de **1000** appels
  imbriqués. Au-delà : `ErreurRecursion`.
- Les arguments sont évalués de gauche à droite, avant l'appel.

### 6.11 Gestion des erreurs dans le programme : `essayer`, `attraper`, `lever`

```kplus
essayer
    afficher(10 / 0)
attraper erreur
    afficher("Problème : " + erreur)
fin

lever "Le montant doit être positif"
```

- Si une erreur d'exécution survient dans le bloc `essayer`, l'exécution du
  bloc s'arrête et le bloc `attraper` s'exécute.
- `attraper nom` déclare une variable `nom`, locale au bloc `attraper`,
  contenant le **message** de l'erreur (un `texte`). Le nom est facultatif :
  `attraper` seul est permis.
- S'il n'y a pas d'erreur, le bloc `attraper` est ignoré.
- `lever expression` déclenche une `ErreurUtilisateur`. L'expression doit être
  un `texte` (sinon `ErreurType`) ; elle devient le message.
- Toutes les erreurs **d'exécution** sont attrapables, y compris
  `ErreurRecursion`. Les erreurs **lexicales et de syntaxe** ne le sont pas :
  elles empêchent le programme de démarrer.
- Une erreur levée dans un bloc `attraper` se propage normalement vers
  l'extérieur.
- `retourner`, `arreter` et `continuer` traversent un bloc `essayer` normalement
  (ce ne sont pas des erreurs).

---

## 7. Portée des noms

K+ utilise une **portée lexicale par blocs** :

- La **portée globale** contient les fonctions natives et les déclarations
  faites hors de tout bloc.
- **Chaque bloc** (corps de `si`, `sinon`, boucle, fonction, `essayer`,
  `attraper`) crée une nouvelle portée. Une variable déclarée dans un bloc
  n'existe plus après son `fin`.
- Un nom est recherché dans la portée courante, puis dans les portées
  englobantes, jusqu'à la portée globale.
- Une portée intérieure peut déclarer un nom qui existe déjà dans une portée
  extérieure (*masquage*) ; c'est une nouvelle variable distincte.
- Les paramètres d'une fonction sont des variables de la portée de la fonction.
- Une fonction se souvient des portées qui l'entouraient au moment de sa
  définition (fermeture) :

```kplus
fonction creer_compteur()
    variable n = 0
    fonction suivant()
        n = n + 1
        retourner n
    fin
    retourner suivant
fin

variable compteur = creer_compteur()
afficher(compteur())   # 1
afficher(compteur())   # 2
```

- Les **noms des fonctions natives** (`afficher`, `longueur`, …) sont protégés :
  les redéclarer ou les réaffecter, à n'importe quel niveau, provoque une
  `ErreurNom`.

---

## 8. Fonctions natives

| Fonction | Rôle | Erreurs possibles |
|---|---|---|
| `afficher(v1, v2, ...)` | Écrit les valeurs séparées par un espace, puis une fin de ligne. `afficher()` écrit une ligne vide. Renvoie `nul`. | — |
| `demander(invite)` | Affiche `invite` (un texte, sans fin de ligne), lit une ligne au clavier et la renvoie comme `texte` (sans la fin de ligne). Fin d'entrée : renvoie `nul`. | `ErreurType` si `invite` n'est pas un texte |
| `texte(v)` | Représentation textuelle de `v` (voir §4.2). | — |
| `entier(v)` | Décimal → entier tronqué vers zéro (`entier(-3.9)` = `-3`). Texte d'un entier (espaces autour tolérés, signe `-` ou `+` permis) → entier. Entier → lui-même. | `ErreurValeur` (texte invalide), `ErreurType` (autre type) |
| `decimal(v)` (alias `décimal`) | Entier ou texte d'un nombre (`"3.5"`, `"2"`, `"1e3"`) → décimal. | `ErreurValeur`, `ErreurType` |
| `type(v)` | Nom du type : `"entier"`, `"décimal"`, `"texte"`, `"booléen"`, `"nul"`, `"liste"`, `"fonction"`. | — |
| `longueur(v)` | Nombre de caractères d'un texte ou d'éléments d'une liste. | `ErreurType` |
| `ajouter(liste, v)` | Ajoute `v` à la fin de la liste (modifie la liste). Renvoie `nul`. | `ErreurType` |
| `absolu(x)` | Valeur absolue (garde le type). | `ErreurType` |
| `racine(x)` | Racine carrée, toujours `décimal`. | `ErreurType`, `ErreurValeur` si `x < 0` |
| `arrondir(x)` | Arrondi à l'entier le plus proche, renvoie un `entier`. Les demis s'arrondissent **en s'éloignant de zéro** (`2.5` → `3`, `-2.5` → `-3`). | `ErreurType` |
| `arrondir(x, n)` | Arrondi à `n` chiffres après la virgule (`n` entier ≥ 0), renvoie un `décimal`. | `ErreurType`, `ErreurValeur` |

| `quitter()` | Termine immédiatement le programme (ou le mode interactif) avec le code de sortie `0`. | — |

Les fonctions natives vérifient le nombre de leurs arguments comme les
fonctions utilisateur (`ErreurType` en cas d'écart).

---

## 9. Gestion des erreurs

### 9.1 Catégories

| Catégorie (nom technique) | Nom affiché | Moment | Exemple |
|---|---|---|---|
| `ErreurLexicale` | Erreur lexicale | avant exécution | caractère inconnu `@`, texte non fermé |
| `ErreurSyntaxe` | Erreur de syntaxe | avant exécution | `fin` manquant, `retourner` hors fonction |
| `ErreurNom` | Erreur de nom | exécution | variable non déclarée, redéclaration |
| `ErreurConstante` | Erreur de constante | exécution | réaffectation d'une constante |
| `ErreurType` | Erreur de type | exécution | `"a" + 1`, condition non booléenne |
| `ErreurValeur` | Erreur de valeur | exécution | `entier("abc")`, `pas 0` |
| `ErreurDivisionParZero` | Erreur de division par zéro | exécution | `1 / 0` |
| `ErreurIndex` | Erreur d'indice | exécution | `[1, 2][5]` |
| `ErreurRecursion` | Erreur de récursion | exécution | plus de 1000 appels imbriqués |
| `ErreurUtilisateur` | Erreur | exécution | `lever "..."` |

Une erreur non attrapée **arrête le programme**. Ce qui a déjà été affiché
reste affiché.

### 9.2 Format du message

Toutes les erreurs sont écrites sur la **sortie d'erreur** (*stderr*) au format :

```
Erreur de type (ligne 3, colonne 18) : impossible d'utiliser + entre un texte et un entier.
   3 | afficher("Âge : " + age)
     |                  ^
Conseil : convertissez le nombre avec texte(age).
```

- **Ligne et colonne** commencent à 1. La colonne compte les caractères
  Unicode (pas les octets) ; une tabulation compte pour 1.
- Si l'erreur survient dans une fonction, la pile d'appels est ajoutée :

```
Pile d'appels (du plus récent au plus ancien) :
  dans diviser, ligne 2
  appelée ligne 6
```

- Pour un bloc jamais fermé, l'erreur pointe la **ligne d'ouverture** du bloc :
  `Erreur de syntaxe (ligne 2, colonne 1) : le bloc « si » ouvert ici n'est jamais fermé par « fin ».`
- Pour `ErreurUtilisateur`, le message est celui donné à `lever`.

### 9.3 Message transmis à `attraper`

La variable de `attraper` reçoit uniquement le message principal, sans
catégorie ni numéro de ligne. Exemple : pour `10 / 0`, le texte
`"division par zéro"`.

---

## 10. Interface en ligne de commande

Commande prévue : `kplus` (installée en Phase 2 ; d'ici là, elle n'existe pas).

| Commande | Effet |
|---|---|
| `kplus programme.kplus` | Analyse puis exécute le fichier. |
| `kplus --verifier programme.kplus` | Analyse seulement (lexique + syntaxe) ; affiche `Aucune erreur détectée.` ou l'erreur. N'exécute rien. |
| `kplus` | Mode interactif : chaque ligne (ou bloc complet jusqu'à son `fin`) est exécutée immédiatement ; la valeur d'une expression seule est affichée. Les variables sont conservées entre les saisies. Une erreur affiche son message sans quitter. On quitte avec `quitter()` ou Ctrl+D (Linux/macOS) / Ctrl+Z puis Entrée (Windows). |
| `kplus --version` | Affiche `K+ 0.1.0`. |
| `kplus --aide` | Affiche l'aide. |

**Codes de sortie** (utiles pour l'automatisation) :

| Code | Signification |
|---|---|
| `0` | Succès |
| `1` | Erreur K+ (lexicale, syntaxe ou exécution non attrapée) |
| `2` | Mauvaise utilisation de la commande (fichier introuvable, option inconnue) |
| `130` | Interruption par l'utilisateur (Ctrl+C) |

Le fichier source peut avoir n'importe quelle extension, mais `.kplus` est
l'extension officielle. Un fichier qui n'est pas en UTF-8 valide provoque un
message clair et le code `2`.

---

## 11. Hors du périmètre de K+ 0.1

Ces éléments sont volontairement **reportés** (versions suivantes) :

- dictionnaires, ensembles, objets et classes ;
- modules et importation (`importer`) ;
- fichiers, réseau, date et heure ;
- textes multilignes et interpolation (`"Bonjour {nom}"`) ;
- indices négatifs, tranches (`liste[1:3]`) ;
- paramètres par défaut, nombre variable d'arguments ;
- objet d'erreur détaillé dans `attraper` (catégorie, ligne) ;
- annotations de type ;
- compilation native, K+ Studio, bibliothèques mathématiques/données/IA.

---

## 12. Cas de test

Les cas de test de conformité sont dans
[`tests/conformite/`](../../tests/conformite/). Chaque cas est un petit
programme `.kplus` accompagné de sa sortie attendue (`.sortie`) et, s'il doit
échouer, de l'erreur attendue (`.erreur`). Le format est décrit dans
[`tests/conformite/README.md`](../../tests/conformite/README.md).

Ils seront exécutés **automatiquement** en Phase 3 par un lanceur de tests ;
en Phase 1, ils ne servent que de référence : **aucun n'a encore été exécuté**,
puisque le moteur n'existe pas.

Couverture prévue par fonctionnalité du cahier des charges :

| # | Fonctionnalité | Cas |
|---|---|---|
| 1 | Affichage | 001, 002, 003, 004, 048 |
| 2 | Variables | 005, 008, 009, 043, 044 |
| 3 | Constantes | 006, 007 |
| 4 | Types de données | 010, 011, 012, 038, 039, 047 |
| 5 | Opérations mathématiques | 013, 014, 015, 016, 017, 041 |
| 6 | Conditions | 018, 019, 020, 021, 042 |
| 7 | Boucles | 022, 023, 024, 025, 045, 046 |
| 8 | Fonctions | 026, 027, 028, 029, 030, 031, 037 |
| 9 | Commentaires | 032 |
| 10 | Gestion des erreurs | 033, 034, 035, 036 (et tous les cas `.erreur`) |
| — | Programme complet du cahier des charges | 040 |

En plus de ces cas « boîte noire », la Phase 2 ajoutera des **tests unitaires**
pour chaque composant (lexer, parser, interpréteur).
