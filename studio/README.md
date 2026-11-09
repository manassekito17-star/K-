# K+ Studio

K+ Studio est l'éditeur officiel de K+. C'est une application web : il
s'ouvre dans un navigateur (Chrome, Edge, Firefox, Safari), sur ordinateur
comme sur téléphone.

Il exécute le **vrai moteur K+** (les mêmes fichiers `kplus/*.py` que la
commande `kplus`) grâce à [Pyodide](https://pyodide.org), une version de Python
qui fonctionne dans le navigateur.

## Lancer K+ Studio

Depuis la racine du projet :

```
python studio/construire.py --servir
```

Le navigateur s'ouvre sur `http://localhost:8000`. Laissez la fenêtre de
commande ouverte pendant l'utilisation (Ctrl+C pour arrêter).

Au premier lancement, le navigateur télécharge Python (environ 10 Mo depuis
cdn.jsdelivr.net) : une connexion Internet est nécessaire. Ensuite, le
navigateur garde ces fichiers en cache.

> Ouvrir directement `index.html` en double-cliquant ne fonctionne pas : les
> navigateurs interdisent alors le chargement du moteur. Il faut passer par
> `construire.py --servir` (ou tout autre serveur web).

## Fonctionnalités

| Fonction | Comment |
|---|---|
| Coloration du code | automatique (mots-clés, textes, nombres, commentaires...) |
| Exécuter | bouton **▶ Exécuter** ou **Ctrl+Entrée** |
| Arrêter un programme (boucle infinie...) | bouton **■ Arrêter** |
| Vérification pendant la saisie | en haut de l'éditeur ; cliquer sur l'erreur pour aller à la ligne |
| Erreurs | affichées dans la console, ligne surlignée en rouge, lien « Aller à la ligne » |
| Réponses pour `demander()` | panneau **Entrée clavier**, une réponse par ligne |
| Ouvrir / Enregistrer | fichiers `.kplus` de l'ordinateur (**Ctrl+S** pour enregistrer) |
| Exemples | menu **Exemples…** |
| Sauvegarde automatique | le programme en cours est conservé dans le navigateur |
| Indentation | **Tab** ajoute 4 espaces, **Maj+Tab** les retire ; retrait automatique après `alors`, `faire`... ; **Échap** puis **Tab** pour quitter l'éditeur au clavier |

## Limites de cette première version

- `demander()` lit les réponses préparées dans le panneau **Entrée clavier** :
  le programme ne s'interrompt pas pour poser la question. (Une vraie saisie
  interactive demande un hébergement spécial ; prévu plus tard.)
- **Arrêter** redémarre le moteur, ce qui prend une à deux secondes.
- La console affiche au plus 500 000 caractères par exécution.

## Organisation des fichiers

| Fichier | Rôle |
|---|---|
| `index.html`, `studio.css` | page et apparence (thèmes clair et sombre, mise en page mobile) |
| `studio.js` | éditeur, console, boutons |
| `coloration.js` | coloration syntaxique (mêmes règles que le lexer du moteur) |
| `travailleur.js` | fait tourner Pyodide et le moteur K+ en arrière-plan |
| `pont.py` | relie le moteur K+ à la page (sortie, entrées, erreurs) |
| `construire.py` | assemble le site dans `studio/dist/` et peut le servir |

## Tests

| Test | Commande |
|---|---|
| Pont, construction, cohérence de la coloration avec le moteur | `python -m unittest tests.test_studio` |
| Coloration | `node --test studio/tests/coloration.test.mjs` |
| De bout en bout dans Chromium (27 vérifications) | `node studio/tests/e2e.mjs` |

Le test de bout en bout ouvre K+ Studio dans un vrai navigateur et l'utilise
comme une personne : exécution de tous les exemples, erreurs, bouton
Arrêter sur une boucle infinie, récursion profonde, `demander()`, etc.
