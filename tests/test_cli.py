import os
import subprocess
import sys
import tempfile
import unittest

from tests.outils import RACINE


def kplus(*args, entree=""):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable, "-m", "kplus", *args], cwd=RACINE,
                          input=entree, capture_output=True, text=True,
                          encoding="utf-8", env=env, timeout=60)


class TestLigneDeCommande(unittest.TestCase):
    def setUp(self):
        self.dossier = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.dossier.cleanup()

    def fichier(self, contenu, nom="p.kplus", encodage="utf-8"):
        chemin = os.path.join(self.dossier.name, nom)
        with open(chemin, "w", encoding=encodage) as f:
            f.write(contenu)
        return chemin

    def test_version_et_aide(self):
        self.assertEqual(kplus("--version").stdout, "K+ 0.1.0\n")
        r = kplus("--aide")
        self.assertEqual(r.returncode, 0)
        self.assertIn("kplus --verifier", r.stdout)

    def test_execution(self):
        r = kplus(self.fichier('afficher("ok")'))
        self.assertEqual((r.returncode, r.stdout, r.stderr), (0, "ok\n", ""))

    def test_erreur_code_1(self):
        r = kplus(self.fichier('afficher("avant")\nafficher(1 / 0)'))
        self.assertEqual(r.returncode, 1)
        self.assertEqual(r.stdout, "avant\n")
        self.assertTrue(r.stderr.startswith("Erreur de division par zéro (ligne 2,"))

    def test_verifier_n_execute_rien(self):
        chemin = self.fichier('afficher("ne pas afficher")')
        r = kplus("--verifier", chemin)
        self.assertEqual((r.returncode, r.stdout), (0, "Aucune erreur détectée.\n"))
        r = kplus("--verifier", self.fichier("si vrai alors"))
        self.assertEqual(r.returncode, 1)

    def test_mauvaise_utilisation(self):
        self.assertEqual(kplus("absent.kplus").returncode, 2)
        self.assertEqual(kplus("--inconnue").returncode, 2)
        self.assertEqual(kplus("a.kplus", "b.kplus").returncode, 2)
        self.assertEqual(kplus("--verifier").returncode, 2)
        self.assertEqual(kplus(self.dossier.name).returncode, 2)

    def test_fichier_non_utf8(self):
        r = kplus(self.fichier('afficher("é")', encodage="latin-1"))
        self.assertEqual(r.returncode, 2)
        self.assertIn("UTF-8", r.stderr)

    def test_quitter(self):
        r = kplus(self.fichier('afficher(1)\nquitter()\nafficher(2)'))
        self.assertEqual((r.returncode, r.stdout), (0, "1\n"))

    def test_demander(self):
        r = kplus(self.fichier('afficher("Bonjour " + demander("Nom ? "))'),
                  entree="Awa\n")
        self.assertEqual(r.stdout, "Nom ? Bonjour Awa\n")

    def test_mode_interactif(self):
        entree = ("variable x = 2\nx * 21\nsi x > 1 alors\nafficher(\"grand\")\nfin\n"
                  "afficher(y)\n\"texte\"\nquitter()\nafficher(\"jamais\")\n")
        r = kplus(entree=entree)
        self.assertEqual(r.returncode, 0)
        self.assertIn("42\n", r.stdout)
        self.assertIn("grand\n", r.stdout)
        self.assertIn('"texte"\n', r.stdout)
        self.assertNotIn("jamais", r.stdout)
        self.assertIn("Erreur de nom", r.stderr)

    def test_mode_interactif_fin_d_entree(self):
        r = kplus(entree="afficher(1)\n")
        self.assertEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
