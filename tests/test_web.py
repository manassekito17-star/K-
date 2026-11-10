"""Tests de la bibliothèque web de K+ (« utiliser web »), sans navigateur :
on vérifie le modèle de la page, les commandes produites et les événements
simulés (spécification docs/specification/kplus-web-0.2.md)."""

import io
import json
import re
import sys
import unittest
from pathlib import Path

from tests.outils import RACINE, erreur_de, executer
import kplus
from kplus import web
from kplus.erreurs import ErreurNom, ErreurSyntaxe, ErreurType, ErreurValeur

sys.path.insert(0, str(Path(RACINE) / "studio"))
import pont  # noqa: E402

SPEC = (Path(RACINE) / "docs" / "specification" / "kplus-web-0.2.md").read_text(encoding="utf-8")
EXEMPLES = re.findall(r"```kplus\n(.*?)```", SPEC, re.S)


def lancer(source):
    sortie = io.StringIO()
    interp = kplus.Interpreteur(sortie, io.StringIO(""))
    interp.executer_programme(kplus.analyser(source))
    return interp, sortie


def elements(interp, genre):
    return [e for e in interp.page.elements.values() if e.genre == genre and not e.supprime]


class TestActivation(unittest.TestCase):
    def test_sans_utiliser_web_les_noms_restent_libres(self):
        source = "variable titre = 1\nvariable valeur = 2\nafficher(titre + valeur)"
        self.assertEqual(executer(source), "3\n")

    def test_utiliser_web_protege_les_noms(self):
        e = erreur_de("utiliser web\nvariable valeur = 2")
        self.assertIsInstance(e, ErreurNom)
        self.assertIn("fonction native", e.message)

    def test_nom_deja_utilise_avant(self):
        e = erreur_de("variable titre = 1\nutiliser web")
        self.assertIsInstance(e, ErreurNom)
        self.assertEqual(e.ligne, 2)
        self.assertIn("renommez « titre »", e.conseil)

    def test_bibliotheque_inconnue_et_position(self):
        self.assertIsInstance(erreur_de("utiliser maths"), ErreurNom)
        with self.assertRaises(ErreurSyntaxe):
            kplus.analyser("fonction f()\n    utiliser web\nfin")

    def test_utiliser_deux_fois(self):
        interp, _ = lancer("utiliser web\nutiliser web\ntitre(\"A\")")
        self.assertEqual(len(elements(interp, "titre")), 1)

    def test_type_et_affichage_d_un_element(self):
        self.assertEqual(executer('utiliser web\nvariable b = bouton("OK", afficher)\n'
                                  'afficher(type(b), b)\nafficher(b == b, b == bouton("OK", afficher))'),
                         "élément <élément bouton « OK »>\nvrai faux\n")


class TestCreationEtModification(unittest.TestCase):
    def test_commandes_de_creation(self):
        interp, _ = lancer('utiliser web\ntitre_page("Site")\ntitre("Bonjour")\nsous_titre("Partie")\n'
                           'paragraphe("Texte")\nvariable c = champ("Nom")\nvariable l = liste()\n'
                           'ajouter_ligne(l, "un")\nimage("https://exemple.org/a.png", "Logo")\n'
                           'lien("Site", "https://exemple.org")\nvariable z = zone()\nplacer(c, z)')
        ops = [(c["op"], c.get("genre")) for c in interp.page.prendre_commandes()]
        self.assertEqual(ops, [("titre_page", None), ("creer", "titre"), ("creer", "sous_titre"),
                               ("creer", "paragraphe"), ("creer", "champ"), ("creer", "liste"),
                               ("creer", "ligne"), ("creer", "image"), ("creer", "lien"),
                               ("creer", "zone"), ("deplacer", None)])

    def test_lire_et_modifier(self):
        source = ('utiliser web\nvariable p = paragraphe("a")\nchanger_texte(p, "b")\n'
                  'variable c = champ("Nom")\nchanger_valeur(c, "Awa")\n'
                  'afficher(texte_de(p), valeur(c), texte_de(c))\nvider(c)\nafficher(valeur(c) == "")')
        self.assertEqual(executer(source), "b Awa Awa\nvrai\n")

    def test_vider_et_supprimer(self):
        interp, _ = lancer('utiliser web\nvariable l = liste()\nvariable a = ajouter_ligne(l, "a")\n'
                           'ajouter_ligne(l, "b")\nvider(l)\nvariable p = paragraphe("x")\nsupprimer(p)')
        self.assertEqual(elements(interp, "ligne"), [])
        self.assertEqual(elements(interp, "paragraphe"), [])
        e = erreur_de('utiliser web\nvariable p = paragraphe("x")\nsupprimer(p)\nchanger_texte(p, "y")')
        self.assertIsInstance(e, ErreurValeur)
        self.assertIn("supprimé", e.message)

    def test_couleurs(self):
        interp, _ = lancer('utiliser web\nvariable p = paragraphe("x")\ncouleur(p, "Rouge")\n'
                           'couleur_fond(p, "#00ff00")')
        styles = [c for c in interp.page.prendre_commandes() if c["op"] == "style"]
        self.assertEqual([(c["propriete"], c["valeur"]) for c in styles],
                         [("color", "#d62828"), ("background-color", "#00ff00")])
        self.assertIsInstance(erreur_de('utiliser web\ncouleur(paragraphe("x"), "url(x)")'), ErreurValeur)

    def test_erreurs_de_type(self):
        cas = {
            'utiliser web\ntitre(42)': ErreurType,
            'utiliser web\nvaleur(paragraphe("x"))': ErreurType,
            'utiliser web\nchanger_texte(champ("x"), "y")': ErreurType,
            'utiliser web\nbouton("OK", 3)': ErreurType,
            'utiliser web\nfonction f(a, b)\nfin\nbouton("OK", f)': ErreurType,
            'utiliser web\najouter_ligne(zone(), "x")': ErreurType,
            'utiliser web\nvariable z = zone()\nplacer(z, z)': ErreurValeur,
            'utiliser web\ntoutes_les(50, afficher)': ErreurValeur,
            'utiliser web\ntoutes_les(1.5, afficher)': ErreurType,
        }
        for source, classe in cas.items():
            with self.subTest(source=source):
                self.assertIsInstance(erreur_de(source), classe)


class TestSecurite(unittest.TestCase):
    def test_adresses_dangereuses_refusees(self):
        for adresse in ("javascript:alert(1)", "JaVaScRiPt:alert(1)", "data:text/html,<b>",
                        "vbscript:x", "//autre-site.org/x", "file:///etc/passwd", ""):
            with self.subTest(adresse=adresse):
                e = erreur_de(f'utiliser web\nlien("x", "{adresse}")')
                self.assertIsInstance(e, ErreurValeur)
        lancer('utiliser web\nlien("a", "https://exemple.org")\nlien("b", "page2.html")\n'
               'image("data:image/png;base64,AAAA", "point")\nimage("photo.jpg", "photo")')

    def test_textes_jamais_interpretes(self):
        interp, _ = lancer('utiliser web\nparagraphe("<script>alert(1)</script>")')
        creation = interp.page.prendre_commandes()[0]
        # Le texte est transmis tel quel ; le navigateur l'affiche avec textContent.
        self.assertEqual(creation["texte"], "<script>alert(1)</script>")
        self.assertNotIn("html", json.dumps(creation).lower())

    def test_nombre_d_elements_limite(self):
        e = erreur_de('utiliser web\npour i de 1 à 20000 faire\n    paragraphe("x")\nfin')
        self.assertIsInstance(e, ErreurValeur)
        self.assertIn("trop d'éléments", e.message)


class TestEvenements(unittest.TestCase):
    def test_exemple_calculatrice_de_la_specification(self):
        interp, _ = lancer(EXEMPLES[0])
        interp.page.prendre_commandes()
        champ = elements(interp, "champ")[0].id
        bouton = elements(interp, "bouton")[0].id
        self.assertIsNone(web.declencher(interp, bouton, "clic", {champ: "21"}))
        self.assertEqual(interp.page.prendre_commandes(), [
            {"op": "texte", "id": "e3", "texte": "Le double est 42.0"},
            {"op": "style", "id": "e3", "propriete": "color", "valeur": "#2a9d4b"}])
        web.declencher(interp, bouton, "clic", {champ: "abc"})
        self.assertEqual(elements(interp, "paragraphe")[0].texte, "Écrivez un nombre, par exemple 3.5")

    def test_exemple_liste_de_taches_de_la_specification(self):
        interp, _ = lancer(EXEMPLES[1])
        champ = elements(interp, "champ")[0].id
        bouton = elements(interp, "bouton")[0].id
        for tache in ("Réviser", "", "Sport"):
            web.declencher(interp, bouton, "clic", {champ: tache})
        lignes = elements(interp, "ligne")
        self.assertEqual([e.texte for e in lignes], ["Réviser", "Sport"])
        self.assertEqual(elements(interp, "paragraphe")[0].texte, "2 tâche(s)")
        self.assertEqual(elements(interp, "champ")[0].valeur, "")
        web.declencher(interp, lignes[0].id, "clic", {})       # action avec paramètre
        self.assertEqual([e.texte for e in elements(interp, "ligne")], ["Sport"])
        self.assertEqual(elements(interp, "paragraphe")[0].texte, "1 tâche(s)")

    def test_quand_change_et_variables_conservees(self):
        interp, sortie = lancer('utiliser web\nvariable c = champ("Nom")\nvariable n = 0\n'
                                'fonction maj()\n    n = n + 1\n    afficher(n, valeur(c))\nfin\n'
                                'quand_change(c, maj)')
        c = elements(interp, "champ")[0].id
        web.declencher(interp, c, "change", {c: "A"})
        web.declencher(interp, c, "change", {c: "Aw"})
        self.assertEqual(sortie.getvalue(), "1 A\n2 Aw\n")

    def test_erreur_dans_une_action(self):
        source = 'utiliser web\nfonction f()\n    afficher(1 / 0)\nfin\nvariable b = bouton("OK", f)'
        interp, _ = lancer(source)
        interp.page.prendre_commandes()
        b = elements(interp, "bouton")[0].id
        texte = web.declencher(interp, b, "clic", {}, source)
        self.assertTrue(texte.startswith("Erreur de division par zéro (ligne 3"))
        self.assertEqual(interp.page.prendre_commandes(), [{"op": "erreur", "texte": texte}])
        # La page continue de fonctionner : un second clic redonne la même erreur.
        self.assertIsNotNone(web.declencher(interp, b, "clic", {}, source))

    def test_minuterie(self):
        interp, sortie = lancer('utiliser web\nvariable n = 0\nvariable m = nul\nfonction tic()\n'
                                '    n = n + 1\n    afficher(n)\n    si n == 3 alors\n'
                                '        arreter_minuterie(m)\n    fin\nfin\nm = toutes_les(100, tic)')
        commandes = interp.page.prendre_commandes()
        m = elements(interp, "minuterie")[0].id
        self.assertEqual(commandes, [{"op": "minuterie", "id": m, "intervalle": 100}])
        for _ in range(5):
            web.declencher(interp, m, "minuterie", {})
        self.assertEqual(sortie.getvalue(), "1\n2\n3\n")       # arrêtée au 3e tour
        self.assertIn({"op": "arreter_minuterie", "id": m}, interp.page.prendre_commandes())

    def test_minuterie_arretee_par_une_erreur(self):
        interp, _ = lancer('utiliser web\nfonction tic()\n    lever "panne"\nfin\ntoutes_les(200, tic)')
        interp.page.prendre_commandes()
        m = elements(interp, "minuterie")[0].id
        self.assertIsNotNone(web.declencher(interp, m, "minuterie", {}))
        self.assertIn({"op": "arreter_minuterie", "id": m}, interp.page.prendre_commandes())
        self.assertEqual(elements(interp, "minuterie"), [])

    def test_evenement_inconnu_ou_element_supprime(self):
        interp, _ = lancer('utiliser web\nvariable p = paragraphe("x")')
        self.assertIsNone(web.declencher(interp, "e999", "clic", {}))
        self.assertIsNone(web.declencher(interp, "e1", "clic", {}))


class TestExemplesDeSites(unittest.TestCase):
    def test_chronometre(self):
        source = (Path(RACINE) / "exemples" / "site_chronometre.kplus").read_text(encoding="utf-8")
        interp, _ = lancer(source)
        interp.page.prendre_commandes()
        boutons = {e.texte: e.id for e in elements(interp, "bouton")}
        affichage = elements(interp, "paragraphe")[0]
        web.declencher(interp, boutons["Démarrer"], "clic", {})
        web.declencher(interp, boutons["Démarrer"], "clic", {})        # pas de 2e minuterie
        self.assertEqual(len(elements(interp, "minuterie")), 1)
        m = elements(interp, "minuterie")[0].id
        for _ in range(15):
            web.declencher(interp, m, "minuterie", {})
        self.assertEqual(affichage.texte, "1.5 s")
        web.declencher(interp, boutons["Pause"], "clic", {})
        self.assertEqual(elements(interp, "minuterie"), [])
        web.declencher(interp, m, "minuterie", {})                     # arrêtée : sans effet
        self.assertEqual(affichage.texte, "1.5 s")
        web.declencher(interp, boutons["Remettre à zéro"], "clic", {})
        self.assertEqual(affichage.texte, "0.0 s")


class TestPont(unittest.TestCase):
    """Session web de K+ Studio : démarrage puis événements."""

    def test_demarrage_puis_clic(self):
        sorties = []
        envoyer = lambda genre, texte: sorties.append(texte)   # noqa: E731
        r = json.loads(pont.executer(EXEMPLES[1], "", envoyer))
        self.assertTrue(r["web"])
        creations = [c for c in r["commandes"] if c["op"] == "creer"]
        champ = next(c["id"] for c in creations if c["genre"] == "champ")
        bouton = next(c["id"] for c in creations if c["genre"] == "bouton")
        la_liste = next(c["id"] for c in creations if c["genre"] == "liste")
        r = json.loads(pont.evenement(bouton, "clic", json.dumps({champ: "Lire"}), envoyer))
        self.assertEqual(r["statut"], "ok")
        ligne = r["commandes"][0]
        self.assertEqual((ligne["op"], ligne["genre"], ligne["texte"], ligne["parent"]),
                         ("creer", "ligne", "Lire", la_liste))
        self.assertIn({"op": "valeur", "id": champ, "valeur": ""}, r["commandes"])

    def test_programme_ordinaire_sans_page(self):
        r = json.loads(pont.executer('afficher("ok")', "", lambda g, t: None))
        self.assertNotIn("web", r)
        self.assertEqual(json.loads(pont.evenement("e1", "clic", "{}", lambda g, t: None))["commandes"], [])

    def test_erreur_dans_une_action_via_le_pont(self):
        source = 'utiliser web\nbouton("OK", quitter)\nfonction f()\n    lever "oups"\nfin\nbouton("KO", f)'
        r = json.loads(pont.executer(source, "", lambda g, t: None))
        ko = [c["id"] for c in r["commandes"] if c.get("texte") == "KO"][0]
        r = json.loads(pont.evenement(ko, "clic", "{}", lambda g, t: None))
        self.assertEqual(r["statut"], "erreur")
        self.assertIn("oups", r["texte_erreur"])


if __name__ == "__main__":
    unittest.main()
