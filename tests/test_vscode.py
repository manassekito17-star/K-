"""Tests de l'extension VS Code côté Python : serveur de vérification,
cohérence de la grammaire et de la fiche de l'extension avec le moteur."""

import json
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

from tests.outils import RACINE
from kplus import __version__
from kplus.jetons import ALIAS_MOTS_CLES, MOTS_CLES
from kplus.natives import NOMS_NATIFS

VSCODE = Path(RACINE) / "vscode"


class TestServeurVerification(unittest.TestCase):
    """Dialogue réel avec moteur/serveur_verification.py (un processus Python)."""

    @classmethod
    def setUpClass(cls):
        env = dict(os.environ, PYTHONPATH=str(RACINE), PYTHONIOENCODING="utf-8")
        cls.processus = subprocess.Popen(
            [sys.executable, str(VSCODE / "moteur" / "serveur_verification.py")],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, env=env,
            text=True, encoding="utf-8")
        cls.accueil = json.loads(cls.processus.stdout.readline())

    @classmethod
    def tearDownClass(cls):
        cls.processus.stdin.close()
        cls.processus.wait(timeout=10)

    def demander(self, identifiant, source):
        self.processus.stdin.write(json.dumps({"id": identifiant, "source": source}) + "\n")
        self.processus.stdin.flush()
        return json.loads(self.processus.stdout.readline())

    def test_accueil(self):
        self.assertEqual(self.accueil, {"pret": True, "version": __version__})

    def test_programme_correct(self):
        self.assertEqual(self.demander(1, 'afficher("ok")\n'), {"ok": True, "id": 1})

    def test_erreur_de_syntaxe(self):
        r = self.demander(2, 'afficher("ok")\nsi vrai alors\n')
        self.assertFalse(r["ok"])
        self.assertEqual(r["id"], 2)
        e = r["erreur"]
        self.assertEqual((e["categorie"], e["ligne"], e["colonne"]), ("ErreurSyntaxe", 2, 1))
        self.assertIn("jamais fermé", e["message"])

    def test_accents_et_conseil(self):
        e = self.demander(3, "variable été = “à”\nafficher(été) ; x")["erreur"]
        self.assertEqual((e["categorie"], e["ligne"], e["colonne"]), ("ErreurLexicale", 2, 15))
        self.assertIn("point-virgule", e["conseil"])

    def test_erreur_d_execution_non_signalee(self):
        # La vérification n'exécute rien : 1 / 0 n'est pas une erreur de syntaxe.
        self.assertTrue(self.demander(4, "afficher(1 / 0)\n")["ok"])

    def test_message_mal_forme(self):
        self.processus.stdin.write("ceci n'est pas du JSON\n")
        self.processus.stdin.flush()
        r = json.loads(self.processus.stdout.readline())
        self.assertIn("interne", r)
        self.assertTrue(self.demander(5, "afficher(1)")["ok"])   # toujours vivant


class TestCoherence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.grammaire = (VSCODE / "syntaxes" / "kplus.tmLanguage.json").read_text(encoding="utf-8")
        cls.paquet = json.loads((VSCODE / "package.json").read_text(encoding="utf-8"))

    def mots(self, cle):
        bloc = json.loads(self.grammaire)["repository"][cle]
        motifs = [p["match"] for p in bloc.get("patterns", [bloc])]
        mots = set()
        for motif in motifs:
            groupe = re.search(r"\]\)\((.*?)\)\(\?!", motif).group(1)
            mots.update(groupe.split("|"))
        return mots

    def test_mots_cles_identiques_au_moteur(self):
        self.assertEqual(self.mots("mots-cles"), set(MOTS_CLES) | set(ALIAS_MOTS_CLES))

    def test_natives_identiques_au_moteur(self):
        self.assertEqual(self.mots("natives"), set(NOMS_NATIFS))

    def test_natives_web_identiques_au_moteur(self):
        from kplus.web import NOMS_WEB
        self.assertEqual(self.mots("natives-web"), set(NOMS_WEB))

    def test_fiche_de_l_extension(self):
        p = self.paquet
        self.assertEqual(p["version"], __version__)
        langage = p["contributes"]["languages"][0]
        self.assertEqual((langage["id"], langage["extensions"]), ("kplus", [".kplus"]))
        for chemin in (p["main"], langage["configuration"],
                       p["contributes"]["grammars"][0]["path"],
                       p["contributes"]["snippets"][0]["path"]):
            self.assertTrue((VSCODE / chemin).is_file(), chemin)
        commandes = {c["command"] for c in p["contributes"]["commands"]}
        self.assertEqual(commandes, {"kplus.executer", "kplus.verifier"})

    def test_snippets_produisent_du_k_plus_valide(self):
        import kplus
        extraits = json.loads((VSCODE / "snippets" / "kplus.json").read_text(encoding="utf-8"))
        for nom, extrait in extraits.items():
            corps = "\n".join(extrait["body"]).replace("\t", "    ")
            # Remplace ${1:texte} par texte, et $0 / $1 par une valeur simple.
            corps = re.sub(r"\$\{\d+:([^}]*)\}", r"\1", corps)
            corps = re.sub(r"\$\d+", "", corps)
            corps = corps.replace("condition", "vrai").replace("parametres", "p")
            source = "variable liste = [1]\nvariable valeur = 1\n" + corps
            with self.subTest(extrait=nom):
                if corps.startswith("afficher"):
                    kplus.analyser(source)
                else:
                    kplus.analyser(source, interactif=True)


if __name__ == "__main__":
    unittest.main()
