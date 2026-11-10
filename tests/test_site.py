"""Tests de « kplus --site » (création d'un site à partir d'un programme K+ Web)."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.outils import RACINE
import kplus
from kplus.erreurs import ErreurSyntaxe
from kplus.site import FICHIERS_PRODUITS, ErreurSite, creer_site

SITE = 'utiliser web\ntitre("Bonjour")\n'


class TestCreationDeSite(unittest.TestCase):
    def setUp(self):
        self.temporaire = tempfile.TemporaryDirectory()
        self.dossier = Path(self.temporaire.name) / "site"

    def tearDown(self):
        self.temporaire.cleanup()

    def test_fichiers_produits(self):
        crees = creer_site(SITE, self.dossier, titre="Mon site")
        self.assertEqual(sorted(p.name for p in crees), sorted(FICHIERS_PRODUITS))
        paquet = json.loads((self.dossier / "moteur.json").read_text(encoding="utf-8"))
        self.assertEqual(paquet["programme"], SITE)
        self.assertEqual(paquet["version"], kplus.__version__)
        moteur = sorted(p.name for p in (Path(RACINE) / "kplus").glob("*.py"))
        self.assertEqual(sorted(n.split("/")[1] for n in paquet["fichiers"]), moteur)
        page = (self.dossier / "index.html").read_text(encoding="utf-8")
        self.assertIn("<title>Mon site</title>", page)
        self.assertNotIn("__", page.replace("__init__", ""))
        self.assertIn("pyodide@", (self.dossier / "travailleur.js").read_text(encoding="utf-8"))

    def test_titre_echappe(self):
        creer_site(SITE, self.dossier, titre='<script>alert(1)</script>')
        page = (self.dossier / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("<script>alert", page)
        self.assertIn("&lt;script&gt;", page)

    def test_refus(self):
        with self.assertRaises(ErreurSyntaxe):
            creer_site("utiliser web\nsi vrai alors\n", self.dossier)
        self.assertFalse(self.dossier.exists())             # rien d'écrit
        with self.assertRaises(ErreurSite):
            creer_site('afficher("pas de page")', self.dossier)
        self.dossier.mkdir()
        (self.dossier / "important.txt").write_text("à garder")
        with self.assertRaises(ErreurSite):
            creer_site(SITE, self.dossier)
        self.assertEqual((self.dossier / "important.txt").read_text(), "à garder")

    def test_recreer_dans_le_meme_dossier(self):
        creer_site(SITE, self.dossier)
        creer_site('utiliser web\ntitre("Nouveau")\n', self.dossier)
        paquet = json.loads((self.dossier / "moteur.json").read_text(encoding="utf-8"))
        self.assertIn("Nouveau", paquet["programme"])


class TestCommande(unittest.TestCase):
    def test_kplus_site(self):
        with tempfile.TemporaryDirectory() as d:
            cible = Path(d) / "calc"
            r = subprocess.run([sys.executable, "-m", "kplus", "--site",
                                "exemples/site_calculatrice.kplus", str(cible)],
                               cwd=RACINE, capture_output=True, text=True, encoding="utf-8",
                               env=dict(os.environ, PYTHONIOENCODING="utf-8"))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("Site créé", r.stdout)
            self.assertTrue((cible / "index.html").is_file())
            r = subprocess.run([sys.executable, "-m", "kplus", "--site"], cwd=RACINE,
                               capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(r.returncode, 2)


if __name__ == "__main__":
    unittest.main()
