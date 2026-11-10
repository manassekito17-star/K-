# K+ Web — spécification (proposition pour K+ 0.2)

> **Statut : implémenté dans K+ 0.2** (spécification validée par le responsable
> du projet). Moteur : `kplus/web.py` ; affichage : `kplus/rendu_web.js` ;
> export : `kplus/site.py`. Tests : `tests/test_web.py`, `tests/test_site.py`,
> `studio/tests/e2e.mjs` (onglet Page) et `studio/tests/site_e2e.mjs` (site exporté).

## 1. Objectif

Permettre à un débutant de créer, en français, des **sites web dynamiques**,
c'est-à-dire des pages qui **réagissent** à l'utilisateur : boutons, champs de
saisie, listes qui se remplissent, textes qui changent, minuteries.

```kplus
utiliser web

titre_page("Calculatrice")
titre("Calculatrice du double")
variable saisie = champ("Votre nombre")
variable resultat = paragraphe("")

fonction calculer()
    essayer
        variable n = decimal(valeur(saisie))
        changer_texte(resultat, "Le double est " + texte(n * 2))
        couleur(resultat, "vert")
    attraper
        changer_texte(resultat, "Écrivez un nombre, par exemple 3.5")
        couleur(resultat, "rouge")
    fin
fin

bouton("Calculer", calculer)
```

Ce programme affiche un titre, un champ, un bouton et un paragraphe. Un clic sur
le bouton calcule et affiche le résultat, en vert, ou un message en rouge si la
saisie n'est pas un nombre.

### Ce que K+ Web 0.2 ne fera pas

- **Pas de serveur ni de base de données.** Le site tourne entièrement dans le
  navigateur du visiteur : il n'enregistre rien et ne partage rien entre
  visiteurs. Les sites côté serveur, à la manière de PHP et Python, sont prévus
  pour K+ 0.3 (voir [la feuille de route](../FEUILLE-DE-ROUTE.md)).
- **Pas d'écriture de HTML ni de CSS bruts.** On n'utilise que les fonctions
  ci-dessous. C'est plus simple, et cela empêche les failles de sécurité
  (injection de code).

## 2. Activer le web : `utiliser web`

- **Nouvelle instruction `utiliser web`**, placée au niveau principal du
  programme (pas dans un bloc). Elle rend disponibles les fonctions du web.
- **Les programmes K+ 0.1 ne changent pas.** Sans `utiliser web`, les noms
  `titre`, `valeur`, `liste`, `couleur`… restent libres pour des variables.
  Avec `utiliser web`, ils deviennent des fonctions protégées, comme `afficher`.
- **Nouveau mot-clé `utiliser`.** Il est réservé, et préparera de futures
  bibliothèques (`utiliser maths`, `utiliser fichiers`…).
- **Erreurs :** `utiliser inconnu` provoque une `ErreurNom` (« bibliothèque
  inconnue ») ; `utiliser web` dans un bloc provoque une `ErreurSyntaxe`.

## 3. Nouveau type : `élément`

- **Ce qu'il représente.** Chaque fonction de création renvoie un `élément` :
  un morceau de la page (titre, bouton, champ…).
- **`type(e)`** renvoie `"élément"`.
- **`texte(e)`** renvoie par exemple `<élément bouton « Calculer »>`.
- **Égalité.** Deux éléments ne sont égaux que s'il s'agit du même élément.

## 4. Fonctions

### 4.1 Créer des éléments

Chaque élément créé s'ajoute **à la fin de la page**, dans l'ordre d'exécution.

| Fonction | Crée | Renvoie |
|---|---|---|
| `titre(texte)` | un grand titre | élément |
| `sous_titre(texte)` | un titre de section | élément |
| `paragraphe(texte)` | un paragraphe | élément |
| `bouton(texte, action)` | un bouton ; `action` est une fonction appelée à chaque clic | élément |
| `champ(etiquette)` | une étiquette et une zone de saisie de texte | élément |
| `liste()` | une liste à puces vide | élément |
| `ajouter_ligne(liste, texte)` | une ligne à la fin de la liste | élément (la ligne) |
| `image(adresse, description)` | une image (adresse `https://…`) ; la description est lue aux personnes aveugles | élément |
| `lien(texte, adresse)` | un lien (adresse `https://…` ou `http://…`) | élément |
| `zone()` | un cadre vide pour regrouper des éléments | élément |
| `placer(element, zone)` | déplace un élément dans une zone | nul |

### 4.2 Lire et modifier

| Fonction | Rôle |
|---|---|
| `valeur(champ)` | texte tapé dans le champ (toujours un `texte`) |
| `changer_valeur(champ, texte)` | remplace le texte du champ |
| `texte_de(element)` | texte affiché par l'élément |
| `changer_texte(element, texte)` | remplace le texte affiché |
| `vider(element)` | enlève le contenu d'une liste ou d'une zone, ou le texte d'un champ |
| `supprimer(element)` | retire l'élément de la page |
| `cacher(element)` / `montrer(element)` | masque ou réaffiche l'élément |
| `couleur(element, couleur)` | couleur du texte |
| `couleur_fond(element, couleur)` | couleur du fond |
| `titre_page(texte)` | titre de l'onglet du navigateur |

**Couleurs** : `rouge`, `vert`, `bleu`, `jaune`, `orange`, `violet`, `rose`,
`noir`, `blanc`, `gris`, ou un code `#rrggbb`. Toute autre valeur provoque une
`ErreurValeur`.

### 4.3 Réagir

| Fonction | Rôle |
|---|---|
| `quand_clic(element, action)` | appelle `action` à chaque clic sur l'élément |
| `quand_change(champ, action)` | appelle `action` à chaque modification du champ (à chaque touche) |
| `toutes_les(millisecondes, action)` | appelle `action` régulièrement (au moins 100 ms) ; renvoie un élément « minuterie » |
| `arreter_minuterie(minuterie)` | arrête la minuterie |

- **Forme de l'action.** C'est une fonction sans paramètre, ou avec un
  paramètre qui reçoit l'élément concerné.
- **Erreur dans une action.** Elle est affichée (dans un bandeau en haut de la
  page et dans la console), et la page continue de fonctionner. Une minuterie
  dont l'action provoque une erreur est arrêtée.

### 4.4 Exemple de site dynamique : liste de tâches

```kplus
utiliser web

titre("Mes tâches")
variable nouvelle = champ("Nouvelle tâche")
variable taches = liste()
variable compteur = paragraphe("0 tâche")
variable nombre = 0

fonction ajouter_tache()
    si valeur(nouvelle) == "" alors
        retourner
    fin
    variable ligne = ajouter_ligne(taches, valeur(nouvelle))
    quand_clic(ligne, terminer)
    changer_valeur(nouvelle, "")
    nombre = nombre + 1
    changer_texte(compteur, texte(nombre) + " tâche(s)")
fin

fonction terminer(ligne)
    supprimer(ligne)
    nombre = nombre - 1
    changer_texte(compteur, texte(nombre) + " tâche(s)")
fin

bouton("Ajouter", ajouter_tache)
```

## 5. Fonctionnement

1. **Démarrage.** Le programme s'exécute une fois, du début à la fin : il
   construit la page et déclare les actions.
2. **Ensuite, il reste vivant.** Chaque clic, saisie ou minuterie appelle la
   fonction K+ correspondante, avec les variables du programme telles qu'elles
   sont à ce moment-là, comme `nombre` dans l'exemple.
3. **Le moteur ne touche pas directement la page.** Il tient un **modèle de la
   page** et envoie des **commandes** au navigateur (créer, changer le texte,
   supprimer…). Le navigateur renvoie les événements, avec le contenu des
   champs.
4. **Bénéfice.** Ce découpage rend le moteur **testable sans navigateur** et
   **sûr** : les textes sont toujours insérés comme du texte, jamais comme du
   HTML.

## 6. Où l'utiliser

| Outil | Ce qui change |
|---|---|
| **K+ Studio** | nouvel onglet **Page** à côté de la console, qui montre le site en direct |
| **Commande `kplus`** | `kplus --site programme.kplus` crée un dossier contenant un vrai site (`index.html` autonome), publiable sur n'importe quel hébergeur gratuit (GitHub Pages…) ; `kplus programme.kplus` sur un programme web explique qu'il faut `--site` ou K+ Studio |
| **UPL Code Académie** | aperçu de la page dans UPL IDE, et formation « Sites web dynamiques avec K+ » (étape suivante) |

## 7. Tests prévus

- Tests du modèle de page en Python : création, modification, événements
  simulés, erreurs dans les actions, minuteries, couleurs refusées, adresses
  refusées (`javascript:`…), textes contenant `<script>` affichés tels quels.
- Nouveaux cas de conformité (programmes web avec clics simulés).
- Test de bout en bout dans un vrai navigateur : K+ Studio (onglet Page,
  clics, saisie, minuterie) et site exporté par `kplus --site`.
- Non-régression : tous les tests de K+ 0.1 doivent continuer de passer.
