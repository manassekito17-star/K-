# Feuille de route de K+ — proposition

> **Statut : proposition, en attente de validation.** Seule la version 0.1
> existe et fonctionne. Tout ce qui suit est à faire.

**Objectif :** que K+ permette de faire ce que permettent PHP, Python,
JavaScript, HTML, CSS, C, C++, C# et Java. Il ne s'agit pas de copier leurs
syntaxes, mais de reprendre leurs **capacités**, écrites en français simple et
cohérent.

**Méthode, pour chaque version :** spécification validée → moteur → tests → K+
Studio, extension VS Code et UPL → formation. Une version n'est annoncée que
lorsqu'elle fonctionne et qu'elle est testée.

| Version | Capacité | Inspirée de | Exemple en K+ |
|---|---|---|---|
| **0.1** ✓ | Bases : variables, conditions, boucles, fonctions, listes, erreurs | Python, pseudocode | `si age >= 18 alors … fin` |
| **0.2** | **Sites dynamiques dans le navigateur** : pages, boutons, champs, événements, minuteries, export d'un site publiable | JavaScript, HTML, CSS | `bouton("Calculer", calculer)` |
| **0.3** | **Sites côté serveur** : pages générées par le serveur, formulaires, adresses (`/contact`), base de données, sessions, commande `kplus --serveur` | PHP, Python (Flask, Django) | `page "/bonjour" faire … fin` |
| **0.4** | **Données et organisation** : dictionnaires, textes avec `{variables}`, textes sur plusieurs lignes, modules (`utiliser`), mise en forme de la page façon CSS (`style`) | Python, JavaScript, PHP, CSS | `variable eleve = {"nom": "Awa", "note": 15}` |
| **0.5** | **Programmation objet** : classes, objets, méthodes, héritage | Java, C#, C++, Python | `classe Compte … fin` |
| **0.6** | **Types facultatifs** : `variable age : entier = 20`, erreurs détectées avant l'exécution | C#, Java, C, TypeScript | `fonction carre(x : entier) : entier` |
| **1.0** | **Vitesse** : compilation de K+ en programme natif, des dizaines de fois plus rapide | C, C++ | `kplus --compiler programme.kplus` |

## Ce que ces versions permettront de construire

- **0.2 :** calculatrices, jeux simples, quiz, listes de tâches, horloges,
  publiés comme de vrais sites.
- **0.3 :** sites avec formulaire de contact, livre d'or, petit blog, inscription
  avec mot de passe, données enregistrées sur le serveur. C'est ce que font
  PHP et Python.
- **0.4 et 0.5 :** applications plus grandes et mieux organisées (gestion
  d'école, de pharmacie, de boutique…).
- **0.6 et 1.0 :** programmes plus sûrs et plus rapides, utilisables en
  production.

## Limites honnêtes

- **Le calendrier est indicatif.** Chaque version demande plusieurs séances de
  travail, et des tests sur Windows, macOS, Linux et dans le navigateur.
- **Héberger un site côté serveur (0.3) a ses exigences.** Il faut un
  hébergeur qui exécute Python (Render, PythonAnywhere, un serveur
  personnel…) : GitHub Pages ne suffit pas, car il ne sert que des sites
  « navigateur » (0.2).
- **La compilation native (1.0) est le chantier le plus lourd.** Elle viendra
  en dernier, quand le langage sera stable.
