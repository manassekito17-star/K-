"""Création d'un site web à partir d'un programme K+ Web (« kplus --site »).

Le dossier produit est un vrai site statique, publiable chez n'importe quel
hébergeur (GitHub Pages, Netlify…). Le visiteur charge Python (Pyodide) et le
moteur K+ dans son navigateur ; le programme y tourne comme dans K+ Studio.
"""

import html
import json
from pathlib import Path

from . import __version__, analyser, ast

VERSION_PYODIDE = "0.27.7"
DOSSIER_MODELES = Path(__file__).resolve().parent / "site"
FICHIERS_PRODUITS = ("index.html", "site.js", "travailleur.js", "rendu_web.js", "moteur.json")


class ErreurSite(Exception):
    """Le site ne peut pas être créé (message destiné à l'utilisateur)."""


def utilise_le_web(programme: ast.Programme) -> bool:
    return any(isinstance(i, ast.Utiliser) and i.bibliotheque == "web"
               for i in programme.instructions)


def creer_site(source: str, dossier: Path, titre: str = "Site K+") -> list[Path]:
    """Écrit le site dans `dossier` et renvoie les fichiers créés.

    Lève ErreurKPlus si le programme contient une erreur de syntaxe, et
    ErreurSite s'il ne crée pas de page web ou si le dossier est occupé.
    """
    programme = analyser(source)                 # rien n'est écrit si le programme est faux
    if not utilise_le_web(programme):
        raise ErreurSite("ce programme ne crée pas de page web : ajoutez « utiliser web » "
                         "au début, puis des éléments (titre, bouton…)")
    dossier = Path(dossier)
    if dossier.exists():
        if not dossier.is_dir():
            raise ErreurSite(f"{dossier} existe déjà et n'est pas un dossier")
        etrangers = [p.name for p in dossier.iterdir() if p.name not in FICHIERS_PRODUITS]
        if etrangers:
            raise ErreurSite(f"le dossier {dossier} contient déjà d'autres fichiers "
                             f"({', '.join(sorted(etrangers)[:3])}…) : choisissez un dossier vide")
    dossier.mkdir(parents=True, exist_ok=True)

    racine_moteur = Path(__file__).resolve().parent
    fichiers = {f"kplus/{p.name}": p.read_text(encoding="utf-8")
                for p in sorted(racine_moteur.glob("*.py"))}
    paquet = {"version": __version__, "fichiers": fichiers, "programme": source}

    def modele(nom):
        return (DOSSIER_MODELES / nom).read_text(encoding="utf-8")

    contenus = {
        "index.html": modele("index.html").replace("__TITRE__", html.escape(titre))
                                         .replace("__VERSION__", __version__),
        "site.js": modele("site.js"),
        "travailleur.js": modele("travailleur.js").replace("__PYODIDE__", VERSION_PYODIDE),
        "rendu_web.js": (racine_moteur / "rendu_web.js").read_text(encoding="utf-8"),
        "moteur.json": json.dumps(paquet, ensure_ascii=False),
    }
    crees = []
    for nom, contenu in contenus.items():
        chemin = dossier / nom
        chemin.write_text(contenu, encoding="utf-8")
        crees.append(chemin)
    return crees
