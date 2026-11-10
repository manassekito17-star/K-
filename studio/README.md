# K+ Studio

K+ Studio est l'éditeur officiel de K+. C'est une application web : il
s'ouvre dans un navigateur (Chrome, Edge, Firefox, Safari), sur ordinateur
comme sur téléphone.

Il exécute le **vrai moteur K+** (les mêmes fichiers `kplus/*.py` que la
commande `kplus`) grâce à [Pyodide](https://pyodide.org), une version de Python
qui fonctionne dans le navigateur.

## Utiliser K+ Studio en ligne

**https://manassekito17-star.github.io/K-/** : rien à installer.

## Installer K+ Studio sur son appareil

K+ Studio est une application web installable : une fois installée, elle a
son icône sur l'écran d'accueil (téléphone) ou sur le bureau (ordinateur),
s'ouvre dans sa propre fenêtre et **fonctionne sans Internet**.

| Appareil | Comment installer |
|---|---|
| Ordinateur (Chrome, Edge) | bouton **⬇ Installer** dans K+ Studio, ou icône d'installation dans la barre d'adresse |
| Android (Chrome) | bouton **⬇ Installer**, ou menu ⋮ → « Installer l'application » |
| iPhone / iPad (Safari) | bouton **Partager** → « Sur l'écran d'accueil » → Ajouter |
| Mac (Safari) | menu Fichier → « Ajouter au Dock » |

Le bouton **⬇ Installer** de K+ Studio affiche les bonnes explications pour
chaque appareil. Firefox sur ordinateur ne sait pas installer les
applications web (Firefox sur Android, si).

**Hors ligne.** À la première visite, K+ Studio garde sur l'appareil tout ce
qu'il lui faut (environ 15 Mo, dont Python). La barre du bas affiche alors
« ✓ Disponible hors ligne ».

**Mises à jour.** Quand une nouvelle version est publiée, la barre du bas
propose « Nouvelle version disponible : recharger ». Le programme en cours
est conservé.

## Lancer K+ Studio sur son ordinateur (développement)

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
| Exemples | menu **Exemples…** (dont trois sites web : calculatrice, liste de tâches, chronomètre) |
| Sites web (K+ Web) | un programme qui commence par `utiliser web` s'affiche dans l'onglet **Page** ; clics, saisies et minuteries sont transmis au programme ; **Arrêter** fige la page |
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
| `manifest.webmanifest`, `icones/` | fiche de l'application installable et ses icônes |
| `service-worker.js` | fonctionnement hors ligne et mises à jour (liste des fichiers et version écrites par `construire.py`) |
| `outils/generer_icones.mjs` | régénère les icônes PNG à partir de `icones/icone.svg` |
| `construire.py` | assemble le site dans `studio/dist/` et peut le servir |

## Tests

| Test | Commande |
|---|---|
| Pont, construction, cohérence de la coloration avec le moteur | `python -m unittest tests.test_studio` |
| Coloration | `node --test studio/tests/coloration.test.mjs` |
| De bout en bout dans Chromium (45 vérifications, dont installation, hors ligne et onglet Page) | `node studio/tests/e2e.mjs` |
| Sites créés par `kplus --site`, dans Chromium | `node studio/tests/site_e2e.mjs` |
| Même test sur le site en ligne | `node studio/tests/e2e.mjs --url https://manassekito17-star.github.io/K-/` |

Le test de bout en bout ouvre K+ Studio dans un vrai navigateur et l'utilise
comme une personne : exécution de tous les exemples, erreurs, bouton
Arrêter sur une boucle infinie, récursion profonde, `demander()`,
installabilité, et redémarrage complet avec le réseau coupé.
