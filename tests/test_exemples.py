"""Exécute les programmes de exemples/ et compare leur sortie à tests/exemples/.

Les résultats attendus ont été vérifiés indépendamment (calculs refaits en
Python) avant d'être enregistrés.
"""

import os
import subprocess
import sys
import unittest
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
ATTENDUS = RACINE / "tests" / "exemples"

# Cas : (programme, fichier d'entrée clavier ou None, fichier de sortie attendue)
CAS = [(p.stem, None, p.stem) for p in sorted((RACINE / "exemples").glob("*.kplus"))
       if p.stem != "devinette"]
CAS += [("devinette", "devinette", "devinette"),
        ("devinette", "devinette_perdu", "devinette_perdu")]


class TestExemples(unittest.TestCase):
    def test_exemples(self):
        self.assertGreaterEqual(len(CAS), 9)
        for programme, entree, sortie in CAS:
            with self.subTest(programme=programme, entree=entree):
                texte_entree = ""
                if entree:
                    texte_entree = (ATTENDUS / f"{entree}.entree").read_text(encoding="utf-8")
                r = subprocess.run(
                    [sys.executable, "-m", "kplus", f"exemples/{programme}.kplus"],
                    cwd=RACINE, input=texte_entree, capture_output=True, text=True,
                    encoding="utf-8", timeout=60,
                    env=dict(os.environ, PYTHONIOENCODING="utf-8"))
                attendu = (ATTENDUS / f"{sortie}.sortie").read_text(encoding="utf-8")
                self.assertEqual(r.stderr, "")
                self.assertEqual(r.returncode, 0)
                self.assertEqual(r.stdout, attendu)


if __name__ == "__main__":
    unittest.main()
