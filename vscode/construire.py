"""Assemble l'extension K+ pour VS Code.

Utilisation (depuis la racine du projet) :
    python vscode/construire.py              prépare le dossier vscode/
    python vscode/construire.py --paquet     crée aussi vscode/dist/kplus-<version>.vsix
                                             (nécessite Node.js et Internet)

Le moteur K+ (kplus/*.py) est copié dans vscode/moteur/kplus : l'extension
signale exactement les mêmes erreurs que la commande « kplus ».
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
VSCODE = RACINE / "vscode"
VERSION_VSCE = "3.2.1"


def preparer():
    moteur = VSCODE / "moteur" / "kplus"
    if moteur.exists():
        shutil.rmtree(moteur)
    moteur.mkdir(parents=True)
    for fichier in sorted((RACINE / "kplus").glob("*.py")):
        shutil.copy2(fichier, moteur / fichier.name)

    icones = VSCODE / "icones"
    if icones.exists():
        shutil.rmtree(icones)
    icones.mkdir()
    for nom in ("icone.svg", "icone-512.png"):
        shutil.copy2(RACINE / "studio" / "icones" / nom, icones / nom)


def empaqueter() -> Path:
    version = json.loads((VSCODE / "package.json").read_text(encoding="utf-8"))["version"]
    dist = VSCODE / "dist"
    dist.mkdir(exist_ok=True)
    sortie = dist / f"kplus-{version}.vsix"
    npx = "npx.cmd" if sys.platform == "win32" else "npx"
    subprocess.run([npx, "--yes", f"@vscode/vsce@{VERSION_VSCE}", "package",
                    "--skip-license", "--allow-missing-repository", "--no-dependencies",
                    "--out", str(sortie)], cwd=VSCODE, check=True)
    return sortie


if __name__ == "__main__":
    preparer()
    print("Extension préparée dans", VSCODE)
    if "--paquet" in sys.argv:
        print("Paquet créé :", empaqueter())
