"""Tests de K+ Studio côté Python : pont.py, construction du site,
cohérence de la coloration (coloration.js) avec le moteur."""

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

from tests.outils import RACINE
from kplus.jetons import ALIAS_MOTS_CLES, MOTS_CLES
from kplus.natives import NOMS_NATIFS

sys.path.insert(0, str(Path(RACINE) / "studio"))
import construire  # noqa: E402
import pont  # noqa: E402


def executer(source, entree=""):
    messages = []
    resultat = json.loads(pont.executer(source, entree, lambda g, t: messages.append((g, t))))
    return resultat, messages


def texte_affiche(messages):
    return "".join(t for _, t in messages)


class TestPont(unittest.TestCase):
    def test_execution(self):
        resultat, messages = executer('afficher("Bienvenue dans K+")\nafficher(1 + 2)')
        self.assertEqual(resultat["statut"], "ok")
        self.assertEqual(texte_affiche(messages), "Bienvenue dans K+\n3\n")
        self.assertIsInstance(resultat["duree_ms"], int)

    def test_erreur_execution(self):
        resultat, messages = executer('afficher("avant")\nafficher(10 / 0)')
        self.assertEqual(texte_affiche(messages), "avant\n")
        e = resultat["erreur"]
        self.assertEqual(resultat["statut"], "erreur")
        self.assertEqual((e["categorie"], e["ligne"], e["colonne"]),
                         ("ErreurDivisionParZero", 2, 13))
        self.assertTrue(e["texte"].startswith("Erreur de division par zéro (ligne 2"))

    def test_erreur_syntaxe_rien_execute(self):
        resultat, messages = executer('afficher("non")\nsi vrai alors')
        self.assertEqual(messages, [])
        self.assertEqual(resultat["erreur"]["categorie"], "ErreurSyntaxe")

    def test_pile_d_appels(self):
        resultat, _ = executer("fonction f()\nretourner 1 / 0\nfin\nf()")
        self.assertEqual(resultat["erreur"]["pile"], [{"fonction": "f", "ligne": 4}])

    def test_entrees_reaffichees(self):
        resultat, messages = executer(
            'afficher("Bonjour " + demander("Nom ? "))\nafficher(demander())', "Awa\n")
        self.assertEqual(resultat["statut"], "ok")
        self.assertEqual(messages, [("sortie", "Nom ? "), ("entree", "Awa\n"),
                                    ("sortie", "Bonjour Awa\nnul\n")])

    def test_quitter(self):
        resultat, messages = executer("afficher(1)\nquitter()\nafficher(2)")
        self.assertEqual((resultat["statut"], texte_affiche(messages)), ("ok", "1\n"))

    def test_envoi_par_paquets(self):
        _, messages = executer('pour i de 1 à 3000 faire\nafficher("ligne", i)\nfin')
        self.assertLess(len(messages), 100)        # pas un message par ligne
        self.assertTrue(texte_affiche(messages).endswith("ligne 3000\n"))

    def test_sortie_tronquee(self):
        _, messages = executer('pour i de 1 à 200000 faire\nafficher("0123456789")\nfin')
        self.assertLessEqual(sum(len(t) for g, t in messages if g == "sortie"), pont.SORTIE_MAX)
        self.assertIn("tronquée", messages[-1][1])

    def test_verifier(self):
        self.assertEqual(json.loads(pont.verifier("afficher(1)")), {"ok": True})
        resultat = json.loads(pont.verifier("x = = 2"))
        self.assertFalse(resultat["ok"])
        self.assertEqual(resultat["erreur"]["ligne"], 1)


class TestConstruction(unittest.TestCase):
    def test_site_complet(self):
        with tempfile.TemporaryDirectory() as dossier:
            dist = Path(dossier) / "dist"
            manifeste = construire.construire(dist)
            for nom in construire.FICHIERS_SITE + ["manifeste.json"]:
                self.assertTrue((dist / nom).is_file(), nom)
            moteur = sorted(p.name for p in (Path(RACINE) / "kplus").glob("*.py"))
            self.assertEqual(manifeste["moteur"], moteur)
            for nom in moteur:      # copie exacte du vrai moteur
                self.assertEqual((dist / "kplus" / nom).read_bytes(),
                                 (Path(RACINE) / "kplus" / nom).read_bytes())
            noms = [e["nom"] for e in manifeste["exemples"]]
            self.assertEqual(noms[0], "bonjour")
            self.assertEqual(sorted(noms),
                             sorted(p.stem for p in (Path(RACINE) / "exemples").glob("*.kplus")))
            devinette = next(e for e in manifeste["exemples"] if e["nom"] == "devinette")
            self.assertIn("entree", devinette)


class TestColoration(unittest.TestCase):
    """Les listes de coloration.js doivent rester identiques à celles du moteur."""

    @classmethod
    def setUpClass(cls):
        cls.source = (Path(RACINE) / "studio" / "coloration.js").read_text(encoding="utf-8")

    def liste_js(self, nom):
        bloc = re.search(rf"const {nom} = \[(.*?)\];", self.source, re.S).group(1)
        return set(re.findall(r'"([^"]+)"', bloc))

    def test_mots_cles(self):
        self.assertEqual(self.liste_js("MOTS_CLES"), set(MOTS_CLES) | set(ALIAS_MOTS_CLES))

    def test_natives(self):
        self.assertEqual(self.liste_js("NATIVES"), set(NOMS_NATIFS))


if __name__ == "__main__":
    unittest.main()
