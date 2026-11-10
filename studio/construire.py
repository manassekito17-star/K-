"""Construit K+ Studio dans studio/dist et, si demandé, l'ouvre dans le navigateur.

Utilisation (depuis la racine du projet) :
    python studio/construire.py            construit le site dans studio/dist
    python studio/construire.py --servir   construit, puis ouvre K+ Studio
                                           sur http://localhost:8000

Le site contient une copie du vrai moteur (kplus/*.py) : K+ Studio exécute
exactement le même code que la commande « kplus ».
"""

import functools
import hashlib
import http.server
import json
import shutil
import socketserver
import sys
import webbrowser
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
STUDIO = RACINE / "studio"
DIST = STUDIO / "dist"
FICHIERS_SITE = ["index.html", "studio.css", "studio.js", "coloration.js",
                 "travailleur.js", "pont.py", "manifest.webmanifest"]

TITRES_EXEMPLES = {
    "bonjour": "Bonjour (exemple du cahier des charges)",
    "calculatrice": "Calculatrice",
    "devinette": "Jeu de devinette",
    "statistiques": "Statistiques sur des notes",
    "nombres_premiers": "Nombres premiers",
    "textes": "Manipulation de textes",
    "banque": "Compte bancaire",
    "grands_nombres": "Grands nombres",
    "site_calculatrice": "Site web : calculatrice",
    "site_taches": "Site web : liste de tâches",
    "site_chronometre": "Site web : chronomètre",
}


def construire(dist: Path = DIST) -> dict:
    if dist.exists():
        shutil.rmtree(dist)
    (dist / "kplus").mkdir(parents=True)
    (dist / "exemples").mkdir()

    for nom in FICHIERS_SITE:
        shutil.copy2(STUDIO / nom, dist / nom)

    moteur = sorted(p.name for p in (RACINE / "kplus").glob("*.py"))
    for nom in moteur:
        shutil.copy2(RACINE / "kplus" / nom, dist / "kplus" / nom)

    exemples = []
    ordre = list(TITRES_EXEMPLES)
    for chemin in sorted((RACINE / "exemples").glob("*.kplus"),
                         key=lambda p: (ordre.index(p.stem) if p.stem in ordre
                                        else len(ordre), p.stem)):
        shutil.copy2(chemin, dist / "exemples" / chemin.name)
        exemple = {"nom": chemin.stem,
                   "titre": TITRES_EXEMPLES.get(chemin.stem, chemin.stem)}
        entree = RACINE / "tests" / "exemples" / f"{chemin.stem}.entree"
        if entree.exists():
            exemple["entree"] = entree.read_text(encoding="utf-8")
        exemples.append(exemple)

    sys.path.insert(0, str(RACINE))
    import kplus
    manifeste = {"version": kplus.__version__, "moteur": moteur, "exemples": exemples}
    (dist / "manifeste.json").write_text(
        json.dumps(manifeste, ensure_ascii=False, indent=2), encoding="utf-8")

    # Affichage des pages K+ Web : le même fichier que pour « kplus --site ».
    shutil.copy2(RACINE / "kplus" / "rendu_web.js", dist / "rendu_web.js")
    shutil.copytree(STUDIO / "icones", dist / "icones")
    ecrire_service_worker(dist)
    return manifeste


def ecrire_service_worker(dist: Path):
    """Écrit service-worker.js avec la liste des fichiers à garder hors ligne
    et un numéro de version calculé d'après leur contenu : toute modification
    du site produit une nouvelle version, que les navigateurs récupèrent."""
    fichiers = sorted(p.relative_to(dist).as_posix()
                      for p in dist.rglob("*")
                      if p.is_file() and p.relative_to(dist).as_posix() != "service-worker.js")
    empreinte = hashlib.sha256()
    for nom in fichiers:
        empreinte.update(nom.encode("utf-8"))
        empreinte.update((dist / nom).read_bytes())
    version = empreinte.hexdigest()[:12]
    source = (STUDIO / "service-worker.js").read_text(encoding="utf-8")
    source = source.replace('"__VERSION__"', json.dumps(version))
    source = source.replace("__FICHIERS__", json.dumps(["./"] + fichiers))
    (dist / "service-worker.js").write_text(source, encoding="utf-8")
    return version


def servir(dist: Path = DIST, port: int = 8000):
    gestionnaire = functools.partial(http.server.SimpleHTTPRequestHandler,
                                     directory=str(dist))
    gestionnaire.extensions_map = {**gestionnaire.extensions_map,
                                   ".js": "text/javascript", ".py": "text/plain",
                                   ".webmanifest": "application/manifest+json",
                                   ".kplus": "text/plain"}
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", port), gestionnaire) as serveur:
        adresse = f"http://localhost:{port}/"
        print(f"K+ Studio est ouvert sur {adresse}")
        print("Laissez cette fenêtre ouverte. Ctrl+C pour arrêter.")
        webbrowser.open(adresse)
        try:
            serveur.serve_forever()
        except KeyboardInterrupt:
            print("\nK+ Studio arrêté.")


if __name__ == "__main__":
    infos = construire()
    print(f"K+ Studio construit dans {DIST} "
          f"({len(infos['moteur'])} fichiers du moteur, {len(infos['exemples'])} exemples).")
    if "--servir" in sys.argv:
        port = 8000
        if "--port" in sys.argv:
            port = int(sys.argv[sys.argv.index("--port") + 1])
        servir(port=port)
