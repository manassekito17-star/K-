# Mettre K+ Studio en ligne (GitHub Pages)

K+ Studio peut être utilisé par n'importe qui, sans rien installer, à
l'adresse :

**https://manassekito17-star.github.io/K-/**

**État : activé et en ligne** (vérifié par le test de bout en bout lancé sur
l'adresse publique). Les étapes ci-dessous ne servent que pour un autre dépôt.

## Activation (une seule fois)

1. Ouvrir le dépôt sur GitHub : https://github.com/manassekito17-star/K-
2. Cliquer sur **Settings** (Paramètres), en haut à droite du dépôt.
3. Dans le menu de gauche, cliquer sur **Pages**.
4. Sous **Build and deployment**, dans **Source**, choisir **GitHub Actions**.
5. Aller dans l'onglet **Actions**, choisir **Publication de K+ Studio** dans
   la liste de gauche, puis **Run workflow** → **Run workflow**.

Après une à deux minutes, K+ Studio est en ligne à l'adresse ci-dessus.

> Le dépôt doit être **public** pour utiliser GitHub Pages avec un compte
> gratuit.

## Fonctionnement

Le fichier `.github/workflows/studio-pages.yml` s'exécute à chaque envoi de
code sur la branche principale :

1. il lance **tous les tests** : si un seul échoue, rien n'est publié ;
2. il construit K+ Studio (`python studio/construire.py`) ;
3. il met le site en ligne.

Tant que Pages n'est pas activé, le travail réussit sans rien publier et
affiche le message « K+ Studio non publié » avec la marche à suivre.

## Avant d'annoncer K+ publiquement

- **Choisir une licence** (MIT, Apache 2.0, GPL…) : sans licence, personne
  n'a légalement le droit de réutiliser le code, même s'il est visible.
- Le site charge Python depuis cdn.jsdelivr.net (service public et
  gratuit) : les visiteurs ont besoin d'Internet au premier lancement.
