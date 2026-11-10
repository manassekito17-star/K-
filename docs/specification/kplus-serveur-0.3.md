# K+ Serveur — spécification (proposition pour K+ 0.3)

> **Statut : PROPOSITION, en attente de validation.** Rien de ce document n'est
> encore implémenté.

## 1. Objectif

Créer des **sites côté serveur**, comme avec PHP ou Python (Flask, Django) :

- des pages fabriquées par le serveur à chaque visite ;
- des formulaires dont les réponses sont reçues par le serveur ;
- des données enregistrées et partagées entre tous les visiteurs (livre d'or,
  blog, inscriptions…) ;
- des comptes avec mot de passe et une session qui retient l'utilisateur
  connecté.

K+ Web (0.2) fait réagir une page **dans le navigateur** ; K+ Serveur (0.3)
fait travailler **le serveur**. Les deux utilisent les mêmes éléments
(`titre`, `paragraphe`, `lien`, `liste`…).

## 2. Exemple complet : un livre d'or

```kplus
utiliser serveur

fonction accueil()
    titre_page("Livre d'or")
    titre("Livre d'or de la classe")
    variable messages = liste()
    pour chaque m dans lire_tout("messages") faire
        ajouter_ligne(messages, m[1] + " : " + m[2])
    fin
    variable f = formulaire("/ecrire")
    champ_texte(f, "nom", "Votre nom")
    zone_texte(f, "message", "Votre message")
    bouton_envoyer(f, "Publier")
fin

fonction ecrire()
    si donnee("nom") == "" ou donnee("message") == "" alors
        rediriger("/")
        retourner
    fin
    enregistrer("messages", [donnee("nom"), donnee("message")])
    rediriger("/")
fin

page("/", accueil)
formulaire_recu("/ecrire", ecrire)
```

On lance le serveur avec `kplus --serveur livre.kplus`, puis on ouvre
http://localhost:8000. Chaque visiteur voit les messages de tous les autres.

## 3. Activer : `utiliser serveur`

- **Où l'écrire.** Même règle que `utiliser web` : au niveau principal du
  programme.
- **Programme du serveur.** Il s'exécute **une fois au démarrage** pour
  déclarer les pages. Ensuite, le serveur appelle la fonction correspondant à
  chaque visite ou à chaque formulaire reçu.
- **Une page vierge à chaque visite.** À chaque visite, la fonction construit
  une **nouvelle page** avec les fonctions de K+ Web : `titre`, `paragraphe`,
  `lien`, `liste`, `image`, `zone`, `couleur`… Les actions qui s'exécutent dans
  le navigateur (`bouton(texte, action)`, `quand_clic`, `toutes_les`) ne sont
  pas disponibles côté serveur : on utilise un formulaire à la place.

## 4. Fonctions

### 4.1 Adresses

| Fonction | Rôle |
|---|---|
| `page(adresse, fonction)` | la fonction fabrique la page de cette adresse (ex. `"/"`, `"/contact"`) |
| `formulaire_recu(adresse, fonction)` | la fonction traite un formulaire envoyé à cette adresse |
| `parametre(nom)` | partie variable d'une adresse : `page("/article/{numero}", article)`, puis `parametre("numero")` |
| `rediriger(adresse)` | envoie le visiteur vers une autre adresse |

### 4.2 Formulaires

| Fonction | Rôle |
|---|---|
| `formulaire(adresse)` | crée un formulaire qui sera envoyé à cette adresse |
| `champ_texte(formulaire, nom, etiquette)` | zone de saisie d'une ligne |
| `zone_texte(formulaire, nom, etiquette)` | zone de saisie de plusieurs lignes |
| `mot_de_passe(formulaire, nom, etiquette)` | saisie masquée |
| `bouton_envoyer(formulaire, texte)` | bouton qui envoie le formulaire |
| `donnee(nom)` | texte reçu pour ce champ (vide s'il est absent) |

### 4.3 Données enregistrées

Les données sont rangées dans des **tables**. Chaque ligne est une liste de
textes ou de nombres. Le serveur les garde dans un fichier
(`programme.donnees`) : elles survivent à son redémarrage.

| Fonction | Rôle |
|---|---|
| `enregistrer(table, ligne)` | ajoute une ligne ; renvoie son numéro |
| `lire_tout(table)` | liste des lignes ; chaque ligne commence par son numéro : `[numero, valeur1, valeur2…]` |
| `lire(table, numero)` | une ligne, ou `nul` |
| `modifier(table, numero, ligne)` | remplace une ligne |
| `effacer(table, numero)` | supprime une ligne |
| `compter(table)` | nombre de lignes |

### 4.4 Sessions et comptes

| Fonction | Rôle |
|---|---|
| `session(nom)` | valeur retenue pour ce visiteur (ou `nul`) |
| `retenir(nom, valeur)` | retient une valeur pour ce visiteur (connexion…) |
| `oublier(nom)` | efface une valeur (déconnexion) |
| `chiffrer_mot_de_passe(mdp)` | empreinte sûre d'un mot de passe, à enregistrer à la place du mot de passe |
| `verifier_mot_de_passe(mdp, empreinte)` | `vrai` si le mot de passe correspond |

## 5. Sécurité (automatique)

- **Textes.** Tous les textes sont échappés : aucune injection de HTML ni de
  script.
- **Formulaires.** Chaque formulaire reçoit un jeton secret, et un formulaire
  venant d'un autre site est refusé (protection CSRF).
- **Session.** Le cookie de session est signé, inaccessible à JavaScript, et
  limité au site (`HttpOnly`, `SameSite=Lax`).
- **Mots de passe.** Ils ne sont jamais enregistrés en clair : l'empreinte est
  calculée avec `scrypt`, et un sel différent est utilisé pour chaque mot de
  passe.
- **Données.** Elles sont stockées avec SQLite, au moyen de requêtes
  préparées : aucune injection SQL n'est possible depuis K+.
- **Erreurs.** Une erreur dans une page produit une page « Erreur 500 ». Le
  détail est affiché seulement en mode développement ; il est masqué avec
  `--production`.

## 6. Commandes

| Commande | Rôle |
|---|---|
| `kplus --serveur programme.kplus` | lance le site sur http://localhost:8000 (`--port 5000` pour un autre port) |
| `kplus --serveur programme.kplus --production` | mode publication : détails des erreurs masqués |

**Héberger.** Il faut un hébergeur qui exécute Python (Render,
PythonAnywhere, un serveur personnel…). GitHub Pages ne convient pas : il ne
sert que des sites statiques.

## 7. Limites de 0.3

- **Pas d'envoi de fichiers ni d'e-mails.**
- **Une ligne de table est une liste.** Les données nommées
  (`{"nom": "Awa"}`) arriveront avec les dictionnaires, en K+ 0.4.
- **Le serveur intégré convient à l'apprentissage et aux petits sites.** Pour
  un site très fréquenté, un serveur plus robuste viendra plus tard.

## 8. Tests prévus

- **Python :** adresses, paramètres, formulaires, jetons CSRF refusés ou
  acceptés, données (ajout, lecture, modification, suppression, persistance
  après redémarrage), sessions, mots de passe, échappement, erreurs 404 et
  500, mode production.
- **Bout en bout :** livre d'or et inscription/connexion utilisés dans un vrai
  navigateur.
- **Non-régression :** K+ 0.1 et 0.2.
