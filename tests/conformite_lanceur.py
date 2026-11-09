"""Lanceur des tests de conformité (tests/conformite/).

Utilisation : python tests/conformite_lanceur.py
Format des cas : voir tests/conformite/README.md.
"""

import os
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
DOSSIER = RACINE / "tests" / "conformite"

sys.path.insert(0, str(RACINE))
from kplus.erreurs import CATEGORIES  # noqa: E402


def lister_cas():
    return sorted(p.stem for p in DOSSIER.glob("*.kplus"))


def executer_cas(nom):
    """Renvoie la liste des problèmes (vide si le cas réussit)."""
    programme = DOSSIER / f"{nom}.kplus"
    sortie_attendue = (DOSSIER / f"{nom}.sortie").read_text(encoding="utf-8")
    fichier_erreur = DOSSIER / f"{nom}.erreur"
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    r = subprocess.run(
        [sys.executable, "-m", "kplus", str(programme)],
        cwd=RACINE, capture_output=True, text=True, encoding="utf-8",
        stdin=subprocess.DEVNULL, timeout=60, env=env)

    problemes = []
    if r.stdout != sortie_attendue:
        problemes.append(f"sortie différente\n  attendu : {sortie_attendue!r}\n"
                         f"  obtenu  : {r.stdout!r}")
    if fichier_erreur.exists():
        categorie, _, ligne = fichier_erreur.read_text(encoding="utf-8").split()
        nom_affiche = CATEGORIES[categorie].nom_affiche
        if r.returncode != 1:
            problemes.append(f"code de sortie {r.returncode}, attendu 1")
        attendu = f"{nom_affiche} (ligne {ligne},"
        if not r.stderr.startswith(attendu):
            problemes.append(f"erreur attendue « {attendu} »\n  obtenu : {r.stderr!r}")
    else:
        if r.returncode != 0:
            problemes.append(f"code de sortie {r.returncode}, attendu 0")
        if r.stderr:
            problemes.append(f"sortie d'erreur non vide : {r.stderr!r}")
    return problemes


def principal():
    cas = lister_cas()
    echecs = 0
    for nom in cas:
        problemes = executer_cas(nom)
        if problemes:
            echecs += 1
            print(f"ÉCHEC  {nom}")
            for p in problemes:
                print("   ", p)
        else:
            print(f"ok     {nom}")
    print(f"\n{len(cas) - echecs}/{len(cas)} cas réussis.")
    return 1 if echecs else 0


if __name__ == "__main__":
    raise SystemExit(principal())
