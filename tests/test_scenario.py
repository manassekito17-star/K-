"""Scénarios de test des pages K+ Web (correction automatique des exercices web)."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.outils import RACINE
import kplus
from kplus.erreurs import ErreurNom
from kplus.pont import executer_test
from kplus.scenario import ErreurScenario, jouer

TACHES = (Path(RACINE) / "exemples" / "site_taches.kplus").read_text(encoding="utf-8")


class TestScenario(unittest.TestCase):
    def test_description_et_actions(self):
        texte = jouer(TACHES, 'saisir "Nouvelle tâche" "Lire"\ncliquer "Ajouter"\n'
                              'saisir "Nouvelle tâche" "Coder"\ncliquer "Ajouter"\ncliquer "Lire"')
        self.assertEqual(texte, 'titre: Mes tâches\nchamp: Nouvelle tâche = ""\nliste:\n'
                                '  ligne: Coder\nparagraphe: 1 tâche(s)\nbouton: Ajouter\n')

    def test_zones_images_liens_et_quand_change(self):
        source = ('utiliser web\nvariable z = zone()\nvariable c = champ("Nom")\nplacer(c, z)\n'
                  'variable p = paragraphe("")\nplacer(p, z)\nimage("photo.jpg", "Une photo")\n'
                  'lien("Accueil", "https://exemple.org")\n'
                  'fonction maj()\n    changer_texte(p, "Bonjour " + valeur(c))\nfin\nquand_change(c, maj)')
        self.assertEqual(jouer(source, 'saisir "Nom" "Awa"'),
                         'zone:\n  champ: Nom = "Awa"\n  paragraphe: Bonjour Awa\n'
                         'image: Une photo\nlien: Accueil -> https://exemple.org\n')

    def test_minuterie_et_erreur_dans_une_action(self):
        source = ('utiliser web\nvariable n = 0\nvariable p = paragraphe("0")\nfonction tic()\n'
                  '    n = n + 1\n    changer_texte(p, texte(n))\nfin\ntoutes_les(500, tic)\n'
                  'fonction panne()\n    lever "oups"\nfin\nbouton("Panne", panne)')
        self.assertEqual(jouer(source, "minuterie 3\ncliquer \"Panne\""),
                         "paragraphe: 3\nbouton: Panne\nerreur: Erreur (ligne 10, colonne 5) : oups\n")

    def test_actions_refusees(self):
        for scenario in ('cliquer "Inconnu"', 'saisir "Inconnu" "x"', "danser", 'cliquer "Ajouter'):
            with self.subTest(scenario=scenario):
                with self.assertRaises(ErreurScenario):
                    jouer(TACHES, scenario)
        with self.assertRaises(ErreurScenario):
            jouer('afficher("pas de page")', "")
        with self.assertRaises(ErreurNom):
            jouer("utiliser web\nafficher(x)", "")

    def test_executer_test_programme_ordinaire_ou_web(self):
        r = json.loads(executer_test('variable n = entier(demander())\nafficher(n * 2)', "21\n"))
        self.assertEqual((r["statut"], r["sortie"]), ("ok", "42\n"))
        r = json.loads(executer_test('afficher("avant")\nafficher(1 / 0)', ""))
        self.assertEqual((r["statut"], r["sortie"], r["erreur"]["ligne"]), ("erreur", "avant\n", 2))
        r = json.loads(executer_test(TACHES, 'saisir "Nouvelle tâche" "A"\ncliquer "Ajouter"'))
        self.assertIn("  ligne: A\n", r["sortie"])
        r = json.loads(executer_test(TACHES, "danser"))
        self.assertEqual(r["statut"], "scenario")
        r = json.loads(executer_test("si vrai alors", ""))
        self.assertEqual(r["erreur"]["categorie"], "ErreurSyntaxe")

    def test_commande(self):
        with tempfile.TemporaryDirectory() as d:
            visite = Path(d) / "visite.txt"
            visite.write_text('saisir "Nouvelle tâche" "Lire"\ncliquer "Ajouter"\n', encoding="utf-8")
            r = subprocess.run([sys.executable, "-m", "kplus", "--scenario", "exemples/site_taches.kplus",
                                str(visite)], cwd=RACINE, capture_output=True, text=True,
                               encoding="utf-8", env=dict(os.environ, PYTHONIOENCODING="utf-8"))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("  ligne: Lire\n", r.stdout)


if __name__ == "__main__":
    unittest.main()
