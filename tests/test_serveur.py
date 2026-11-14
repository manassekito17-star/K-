"""Tests de la bibliothèque serveur de K+ (« utiliser serveur ») :
docs/specification/kplus-serveur-0.3.md. Les requêtes passent par
Application.traiter (sans réseau), puis par un vrai serveur HTTP."""

import http.cookiejar
import io
import os
import re
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from tests.outils import RACINE, erreur_de
import kplus
from kplus import serveur
from kplus.erreurs import ErreurNom, ErreurSyntaxe, ErreurType, ErreurValeur

SPEC = (Path(RACINE) / "docs" / "specification" / "kplus-serveur-0.3.md").read_text(encoding="utf-8")
LIVRE = (Path(RACINE) / "exemples" / "serveur_livre_or.kplus").read_text(encoding="utf-8")
COMPTES = (Path(RACINE) / "exemples" / "serveur_comptes.kplus").read_text(encoding="utf-8")


def demarrer(source, fichier=":memory:", production=False):
    interp = kplus.Interpreteur(io.StringIO(), io.StringIO(""))
    interp.source = source
    interp.fichier_donnees = fichier
    interp.production = production
    interp.executer_programme(kplus.analyser(source))
    return interp.serveur


class Visiteur:
    """Navigateur simulé : garde le cookie de session et remplit les formulaires."""

    def __init__(self, app):
        self.app = app
        self.cookie = None
        self.page = ""

    def _entetes(self, extra=None):
        h = {"Host": "site.test"}
        if self.cookie:
            h["Cookie"] = self.cookie
        h.update(extra or {})
        return h

    def _garder_cookie(self, r):
        c = r.entete("Set-Cookie")
        if c:
            self.cookie = c.split(";")[0]

    def ouvrir(self, adresse):
        r = self.app.traiter("GET", adresse, self._entetes())
        self._garder_cookie(r)
        self.page = r.corps.decode("utf-8")
        return r

    def envoyer(self, adresse, champs, jeton=True, suivre=True, entetes=None):
        donnees = dict(champs)
        if jeton:
            donnees["_jeton"] = re.search(r'name="_jeton" value="([^"]+)"', self.page).group(1)
        r = self.app.traiter("POST", adresse, self._entetes({
            "Content-Type": "application/x-www-form-urlencoded", **(entetes or {})}),
            urllib.parse.urlencode(donnees).encode("utf-8"))
        self._garder_cookie(r)
        if suivre and r.statut == 303:
            return self.ouvrir(r.entete("Location"))
        self.page = r.corps.decode("utf-8")
        return r

    def textes(self, balise):
        return [re.sub(r"<[^>]+>", "", t) for t in re.findall(rf"<{balise}[^>]*>(.*?)</{balise}>", self.page, re.S)]


class TestActivation(unittest.TestCase):
    def test_exemple_de_la_specification_est_l_exemple_livre(self):
        exemple = re.findall(r"```kplus\n(.*?)```", SPEC, re.S)[0]
        app = demarrer(exemple)
        self.assertEqual([r.adresse for r in app.pages], ["/"])
        self.assertEqual([r.adresse for r in app.formulaires], ["/ecrire"])

    def test_bibliotheque_inconnue(self):
        e = erreur_de("utiliser base")
        self.assertIsInstance(e, ErreurNom)
        self.assertIn("web, serveur", e.conseil)

    def test_web_et_serveur_incompatibles(self):
        e = erreur_de("utiliser web\nutiliser serveur")
        self.assertIsInstance(e, ErreurNom)
        self.assertIn("à la fois", e.message)

    def test_noms_proteges(self):
        e = erreur_de("variable page = 1\nutiliser serveur")
        self.assertIn("« page »", e.message)

    def test_utiliser_dans_un_bloc_refuse(self):
        e = erreur_de("si vrai alors\n    utiliser serveur\nfin")
        self.assertIsInstance(e, ErreurSyntaxe)

    def test_fonctions_de_page_hors_visite(self):
        e = erreur_de('utiliser serveur\ntitre("x")')
        self.assertIsInstance(e, ErreurValeur)
        self.assertIn("fonction de page", e.message)
        for appel in ('donnee("x")', 'session("x")', 'rediriger("/")', 'parametre("x")'):
            with self.subTest(appel=appel):
                self.assertIn("pendant une visite", erreur_de(f"utiliser serveur\n{appel}").message)

    def test_actions_du_navigateur_absentes(self):
        for nom in ("bouton", "champ", "quand_clic", "toutes_les"):
            with self.subTest(nom=nom):
                self.assertNotIn(nom, serveur.NOMS_SERVEUR)
                self.assertIsInstance(erreur_de(f'utiliser serveur\n{nom}("a", "b")'), ErreurNom)

    def test_adresses_invalides(self):
        base = "utiliser serveur\nfonction f()\nfin\n"
        for adresse in ("accueil", "//autre.site", "/a b", "/x/{1}", "/x/{a}/{a}", "/x/{a"):
            with self.subTest(adresse=adresse):
                self.assertIsInstance(erreur_de(base + f'page("{adresse}", f)'), ErreurValeur)
        self.assertIn("déjà déclarée", erreur_de(base + 'page("/", f)\npage("/", f)').message)
        e = erreur_de("utiliser serveur\nfonction f(x)\nfin\npage(\"/\", f)")
        self.assertIsInstance(e, ErreurType)


class TestPages(unittest.TestCase):
    def test_page_et_404(self):
        app = demarrer('utiliser serveur\nfonction a()\n    titre("Accueil")\nfin\npage("/", a)')
        v = Visiteur(app)
        r = v.ouvrir("/")
        self.assertEqual(r.statut, 200)
        self.assertEqual(v.textes("h1"), ["Accueil"])
        self.assertIn("text/html", r.entete("Content-Type"))
        self.assertEqual(v.ouvrir("/rien").statut, 404)
        self.assertIn("Page introuvable", v.page)

    def test_chaque_visite_construit_une_page_vierge(self):
        app = demarrer('utiliser serveur\nvariable n = 0\nfonction a()\n    n = n + 1\n'
                       '    paragraphe("visite " + texte(n))\nfin\npage("/", a)')
        v = Visiteur(app)
        v.ouvrir("/")
        v.ouvrir("/")
        self.assertEqual(v.textes("p"), ["visite 2"])

    def test_parametres(self):
        app = demarrer('utiliser serveur\nfonction article()\n'
                       '    titre("Article " + parametre("numero") + " de " + parametre("auteur"))\nfin\n'
                       'page("/article/{numero}/{auteur}", article)')
        v = Visiteur(app)
        v.ouvrir("/article/12/Gr%C3%A2ce")
        self.assertEqual(v.textes("h1"), ["Article 12 de Grâce"])
        self.assertEqual(v.ouvrir("/article/12").statut, 404)

    def test_parametre_absent(self):
        app = demarrer('utiliser serveur\nfonction a()\n    titre(parametre("id"))\nfin\npage("/", a)')
        r = Visiteur(app).ouvrir("/")
        self.assertEqual(r.statut, 500)
        self.assertIn("pas de paramètre « id »", r.corps.decode())

    def test_donnees_d_une_adresse_get(self):
        app = demarrer('utiliser serveur\nfonction a()\n    paragraphe("q=" + donnee("q") + ";x=" + donnee("x"))\n'
                       'fin\npage("/recherche", a)')
        v = Visiteur(app)
        v.ouvrir("/recherche?q=k%2B")
        self.assertEqual(v.textes("p"), ["q=k+;x="])

    def test_elements_web_et_mise_en_forme(self):
        app = demarrer('utiliser serveur\nfonction a()\n    titre_page("Mon site")\n'
                       '    variable z = zone()\n    variable p = paragraphe("rouge")\n    couleur(p, "rouge")\n'
                       '    placer(p, z)\n    cacher(sous_titre("caché"))\n'
                       '    lien("K+", "https://exemple.cd/k")\n    image("photo.jpg", "Une photo")\nfin\n'
                       'page("/", a)')
        v = Visiteur(app)
        v.ouvrir("/")
        self.assertIn("<title>Mon site</title>", v.page)
        self.assertIn('<div class="zone"><p style="color:#d62828">rouge</p></div>', v.page)
        self.assertIn("<h2 hidden>caché</h2>", v.page)
        self.assertIn('<a href="https://exemple.cd/k">K+</a>', v.page)
        self.assertIn('<img src="photo.jpg" alt="Une photo">', v.page)

    def test_textes_echappes(self):
        app = demarrer('utiliser serveur\nfonction a()\n    titre_page("</title><script>x</script>")\n'
                       '    paragraphe(donnee("t"))\n    lien("x", "/a\\"onclick=\\"x")\nfin\npage("/", a)')
        v = Visiteur(app)
        v.ouvrir("/?t=" + urllib.parse.quote("<img src=x onerror=alert(1)>"))
        self.assertNotIn("<script>", v.page)
        self.assertNotIn("<img src=x", v.page)
        self.assertIn("&lt;img src=x onerror=alert(1)&gt;", v.page)
        self.assertIn('href="/a&quot;onclick=&quot;x"', v.page)

    def test_entetes_de_securite(self):
        r = Visiteur(demarrer('utiliser serveur\nfonction a()\nfin\npage("/", a)')).ouvrir("/")
        self.assertIn("default-src 'none'", r.entete("Content-Security-Policy"))
        self.assertEqual(r.entete("X-Content-Type-Options"), "nosniff")
        cookie = r.entete("Set-Cookie")
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=Lax", cookie)
        self.assertNotIn("Secure", cookie)

    def test_head_et_methode_inconnue(self):
        app = demarrer('utiliser serveur\nfonction a()\n    titre("x")\nfin\npage("/", a)')
        r = app.traiter("HEAD", "/")
        self.assertEqual((r.statut, r.corps), (200, b""))
        self.assertEqual(app.traiter("DELETE", "/").statut, 405)


class TestFormulaires(unittest.TestCase):
    def test_livre_d_or(self):
        v = Visiteur(demarrer(LIVRE))
        v.ouvrir("/")
        self.assertEqual(v.textes("p"), ["0 message(s)"])
        self.assertIn('<input type="text" name="nom">', v.page)
        self.assertIn('<textarea name="message"></textarea>', v.page)
        v.envoyer("/ecrire", {"nom": "Awa", "message": "Bonjour"})
        v.envoyer("/ecrire", {"nom": "", "message": "ignoré"})
        v.envoyer("/ecrire", {"nom": "Koffi", "message": "Salut"})
        self.assertEqual(v.textes("li"), ["Awa : Bonjour", "Koffi : Salut"])
        self.assertEqual(v.textes("p"), ["2 message(s)"])

    def test_messages_partages_entre_visiteurs(self):
        app = demarrer(LIVRE)
        a, b = Visiteur(app), Visiteur(app)
        a.ouvrir("/")
        a.envoyer("/ecrire", {"nom": "Awa", "message": "Bonjour"})
        b.ouvrir("/")
        self.assertEqual(b.textes("li"), ["Awa : Bonjour"])
        self.assertNotEqual(a.cookie, b.cookie)

    def test_csrf_jeton_absent_faux_ou_d_un_autre_visiteur(self):
        app = demarrer(LIVRE)
        v = Visiteur(app)
        v.ouvrir("/")
        r = v.envoyer("/ecrire", {"nom": "X", "message": "Y", "_jeton": "faux"}, jeton=False)
        self.assertEqual(r.statut, 403)
        autre = Visiteur(app)
        autre.ouvrir("/")
        jeton = re.search(r'name="_jeton" value="([^"]+)"', autre.page).group(1)
        r = v.envoyer("/ecrire", {"nom": "X", "message": "Y", "_jeton": jeton}, jeton=False)
        self.assertEqual(r.statut, 403)
        self.assertIn("Formulaire refusé", r.corps.decode())
        self.assertEqual(app.donnees.compter("messages"), 0)

    def test_csrf_origine_d_un_autre_site(self):
        app = demarrer(LIVRE)
        v = Visiteur(app)
        v.ouvrir("/")
        r = v.envoyer("/ecrire", {"nom": "X", "message": "Y"}, entetes={"Origin": "https://pirate.test"})
        self.assertEqual(r.statut, 403)
        v.ouvrir("/")
        r = v.envoyer("/ecrire", {"nom": "X", "message": "Y"}, suivre=False,
                      entetes={"Origin": "http://site.test"})
        self.assertEqual(r.statut, 303)

    def test_cookie_falsifie_ignore(self):
        app = demarrer(LIVRE)
        v = Visiteur(app)
        v.ouvrir("/")
        ident = v.cookie.split("=")[1].split(".")[0]
        v.cookie = f"{serveur.NOM_COOKIE}={ident}.0000"
        r = v.ouvrir("/")
        self.assertIsNotNone(r.entete("Set-Cookie"))           # nouvelle session

    def test_types_de_contenu_et_taille(self):
        app = demarrer(LIVRE)
        v = Visiteur(app)
        v.ouvrir("/")
        r = app.traiter("POST", "/ecrire", {"Cookie": v.cookie, "Content-Type": "application/json"}, b"{}")
        self.assertEqual(r.statut, 415)
        r = app.traiter("POST", "/ecrire", {"Cookie": v.cookie,
                                            "Content-Type": "application/x-www-form-urlencoded"},
                        b"x" * (serveur.CORPS_MAX + 1))
        self.assertEqual(r.statut, 413)

    def test_adresses_et_methodes(self):
        app = demarrer(LIVRE)
        v = Visiteur(app)
        self.assertEqual(v.ouvrir("/ecrire").statut, 405)
        v.ouvrir("/")
        self.assertEqual(v.envoyer("/", {}, suivre=False).statut, 405)
        v.ouvrir("/")
        self.assertEqual(v.envoyer("/rien", {}, suivre=False).statut, 404)

    def test_formulaire_hors_page_et_mauvais_parent(self):
        e = erreur_de('utiliser serveur\nformulaire("/x")')
        self.assertIn("fonction de page", e.message)
        app = demarrer('utiliser serveur\nfonction a()\n    champ_texte(liste(), "n", "N")\nfin\npage("/", a)')
        r = Visiteur(app).ouvrir("/")
        self.assertEqual(r.statut, 500)
        self.assertIn("un formulaire créé par formulaire()", r.corps.decode())
        app = demarrer('utiliser serveur\nfonction a()\n    champ_texte(formulaire("/x"), "mon nom", "N")\n'
                       'fin\npage("/", a)')
        self.assertIn("nom du champ invalide", Visiteur(app).ouvrir("/").corps.decode())

    def test_rediriger_hors_du_site_refuse(self):
        app = demarrer('utiliser serveur\nfonction a()\n    rediriger("https://pirate.test")\nfin\npage("/", a)')
        r = Visiteur(app).ouvrir("/")
        self.assertEqual(r.statut, 500)
        self.assertIsNone(r.entete("Location"))


class TestDonnees(unittest.TestCase):
    PROGRAMME = """utiliser serveur
variable a = enregistrer("notes", ["Awa", 15])
variable b = enregistrer("notes", ["Koffi", 12.5, vrai, nul])
afficher(a, b, compter("notes"), compter("vide"))
afficher(lire_tout("notes"))
modifier("notes", a, ["Awa", 17])
afficher(lire("notes", a), lire("notes", 99))
afficher(effacer("notes", b), effacer("notes", b))
variable c = enregistrer("notes", ["Moussa", 9])
afficher(c, lire_tout("notes"))
"""

    def test_ajout_lecture_modification_suppression(self):
        sortie = io.StringIO()
        kplus.executer(self.PROGRAMME, sortie=sortie)
        self.assertEqual(sortie.getvalue(),
                         '1 2 2 0\n[[1, "Awa", 15], [2, "Koffi", 12.5, vrai, nul]]\n'
                         '[1, "Awa", 17] nul\nvrai faux\n3 [[1, "Awa", 17], [3, "Moussa", 9]]\n')

    def test_persistance_apres_redemarrage(self):
        with tempfile.TemporaryDirectory() as d:
            fichier = str(Path(d) / "site.donnees")
            app = demarrer('utiliser serveur\nenregistrer("t", ["un"])', fichier)
            app.donnees.fermer()
            app = demarrer('utiliser serveur\nafficher(compter("t"))\nenregistrer("t", ["deux"])', fichier)
            self.assertEqual(app.donnees.lire_tout("t"), [[1, "un"], [2, "deux"]])
            app.donnees.fermer()

    def test_erreurs(self):
        cas = {
            'enregistrer("ma table", [1])': "nom de table invalide",
            'enregistrer("t", 1)': "liste de valeurs",
            'enregistrer("t", [[1]])': "chaque valeur de la ligne",
            'lire("t", "1")': "convertissez-le avec entier",
            'modifier("t", 5, [1])': "aucune ligne numéro 5",
        }
        for code, message in cas.items():
            with self.subTest(code=code):
                e = erreur_de("utiliser serveur\n" + code)
                self.assertIn(message, e.message + (e.conseil or ""))

    def test_tables_en_memoire_identiques_a_sqlite(self):
        for donnees in (serveur.Donnees(), serveur.DonneesMemoire()):
            with self.subTest(stockage=type(donnees).__name__):
                a = donnees.enregistrer("t", ["Awa", 15])
                b = donnees.enregistrer("t", ["Koffi", 12.5, True, None])
                self.assertEqual((a, b, donnees.compter("t"), donnees.compter("u")), (1, 2, 2, 0))
                self.assertTrue(donnees.modifier("t", a, ["Awa", 17]))
                self.assertFalse(donnees.modifier("t", 9, ["x"]))
                self.assertEqual((donnees.effacer("t", b), donnees.effacer("t", b)), (True, False))
                self.assertEqual(donnees.enregistrer("t", ["Moussa"]), 3)
                self.assertEqual(donnees.lire_tout("t"), [[1, "Awa", 17], [3, "Moussa"]])
                self.assertEqual((donnees.lire("t", 3), donnees.lire("t", 2)), ([3, "Moussa"], None))
                donnees.fermer()

    def test_injection_sql_impossible(self):
        app = demarrer("utiliser serveur\nenregistrer(\"t\", [\"x'); drop table kplus_lignes; --\"])")
        self.assertEqual(app.donnees.lire_tout("t"), [[1, "x'); drop table kplus_lignes; --"]])


class TestSessionsEtComptes(unittest.TestCase):
    def test_mots_de_passe(self):
        e1 = serveur.chiffrer("secret123")
        e2 = serveur.chiffrer("secret123")
        self.assertNotEqual(e1, e2)                              # sel différent
        self.assertNotIn("secret123", e1)
        self.assertTrue(e1.startswith("scrypt$"))
        self.assertTrue(serveur.verifier("secret123", e1))
        self.assertFalse(serveur.verifier("secret124", e1))
        self.assertIsInstance(erreur_de('utiliser serveur\nverifier_mot_de_passe("a", "b")'), ErreurValeur)

    def test_repli_pbkdf2_sans_scrypt(self):
        import hashlib
        # Vecteur de référence : PBKDF2-HMAC-SHA256 de la bibliothèque standard.
        self.assertEqual(serveur._pbkdf2(b"motdepasse", b"sel", 1000),
                         hashlib.pbkdf2_hmac("sha256", b"motdepasse", b"sel", 1000))
        scrypt = hashlib.scrypt
        del hashlib.scrypt
        try:
            e = serveur.chiffrer("secret123")
            self.assertTrue(e.startswith("pbkdf2_sha256$20000$"))
            self.assertTrue(serveur.verifier("secret123", e))
            self.assertFalse(serveur.verifier("secret124", e))
        finally:
            hashlib.scrypt = scrypt
        self.assertTrue(serveur.verifier("secret123", e))            # vérifiable partout

    def test_inscription_connexion_deconnexion(self):
        app = demarrer(COMPTES)
        awa = Visiteur(app)
        awa.ouvrir("/")
        awa.envoyer("/inscription", {"nom": "Awa", "mdp": "court"})
        self.assertIn("8 caractères au moins", awa.page)
        awa.envoyer("/inscription", {"nom": "Awa", "mdp": "motdepasse1"})
        self.assertEqual(awa.textes("h1"), ["Bonjour Awa !"])
        self.assertNotIn("motdepasse1", str(app.donnees.lire_tout("comptes")))
        awa.envoyer("/deconnexion", {})
        self.assertEqual(awa.textes("h1"), ["Bienvenue"])
        awa.envoyer("/connexion", {"nom": "Awa", "mdp": "mauvais"})
        self.assertIn("Nom ou mot de passe incorrect.", awa.page)
        awa.envoyer("/connexion", {"nom": "Awa", "mdp": "motdepasse1"})
        self.assertEqual(awa.textes("h1"), ["Bonjour Awa !"])
        # Un autre visiteur n'est pas connecté, et ne peut pas reprendre le nom.
        koffi = Visiteur(app)
        koffi.ouvrir("/")
        self.assertEqual(koffi.textes("h1"), ["Bienvenue"])
        koffi.envoyer("/inscription", {"nom": "Awa", "mdp": "autremotdepasse"})
        self.assertIn("Ce nom est déjà pris.", koffi.page)

    def test_valeurs_de_session(self):
        app = demarrer('utiliser serveur\nfonction a()\n    retenir("l", [1, "a"])\n    variable l = session("l")\n'
                       '    ajouter(l, 2)\n    paragraphe(texte(session("l")) + texte(session("absent")))\nfin\n'
                       'fonction b()\n    retenir("x", liste())\nfin\npage("/", a)\npage("/b", b)')
        v = Visiteur(app)
        v.ouvrir("/")
        self.assertEqual(v.textes("p"), ['[1, &quot;a&quot;]nul'])
        self.assertEqual(v.ouvrir("/b").statut, 500)


class TestErreurs(unittest.TestCase):
    SOURCE = 'utiliser serveur\nfonction a()\n    titre("x")\n    afficher(1 / 0)\nfin\npage("/", a)'

    def test_erreur_500_detaillee_en_developpement(self):
        r = Visiteur(demarrer(self.SOURCE)).ouvrir("/")
        self.assertEqual(r.statut, 500)
        self.assertIn("ligne 4", r.corps.decode())
        self.assertIn("division par zéro", r.corps.decode())

    def test_erreur_500_masquee_en_production(self):
        app = demarrer(self.SOURCE, production=True)
        r = Visiteur(app).ouvrir("/")
        self.assertEqual(r.statut, 500)
        self.assertNotIn("ligne 4", r.corps.decode())
        self.assertIn("Secure", r.entete("Set-Cookie"))

    def test_boucle_infinie_arretee(self):
        ancien = serveur.DUREE_MAX
        serveur.DUREE_MAX = 0.5
        try:
            app = demarrer('utiliser serveur\nfonction a()\n    tant que vrai faire\n    fin\nfin\n'
                           'fonction b()\n    titre("ok")\nfin\npage("/", a)\npage("/b", b)')
            r = Visiteur(app).ouvrir("/")
            self.assertEqual(r.statut, 500)
            self.assertIn("boucle infinie", r.corps.decode())
            self.assertEqual(Visiteur(app).ouvrir("/b").statut, 200)     # le serveur continue
        finally:
            serveur.DUREE_MAX = ancien

    def test_quitter_termine_la_visite(self):
        app = demarrer('utiliser serveur\nfonction a()\n    titre("x")\n    quitter()\n    titre("y")\nfin\n'
                       'page("/", a)')
        v = Visiteur(app)
        v.ouvrir("/")
        self.assertEqual(v.textes("h1"), ["x"])


class TestApercuNavigateur(unittest.TestCase):
    """kplus/pont.py : le site tourne en mémoire (K+ Studio, UPL), sans réseau."""

    def test_executer_puis_visiter(self):
        import json
        from kplus import pont
        sortie = []
        r = json.loads(pont.executer(LIVRE, "", lambda g, t: sortie.append(t)))
        self.assertTrue(r["serveur"])
        self.assertEqual(r["pages"], ["/"])
        self.assertEqual(r["visite"]["statut"], 200)
        jeton = re.search(r'name="_jeton" value="([^"]+)"', r["visite"]["html"]).group(1)
        v = json.loads(pont.serveur_requete(
            "POST", "/ecrire", json.dumps([["_jeton", jeton], ["nom", "Awa"], ["message", "Salut"]]),
            lambda g, t: sortie.append(t)))
        self.assertEqual((v["statut"], v["adresse"]), (200, "/"))
        self.assertIn("<li>Awa : Salut</li>", v["html"])
        v = json.loads(pont.serveur_requete("POST", "/ecrire", "[]", lambda g, t: None))
        self.assertEqual(v["statut"], 403)                       # sans jeton
        self.assertEqual(json.loads(pont.serveur_requete("GET", "/rien", "", lambda g, t: None))["statut"], 404)
        pont.executer('afficher("autre")', "", lambda g, t: None)
        self.assertEqual(json.loads(pont.serveur_requete("GET", "/", "", lambda g, t: None))["statut"], 410)


def port_libre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestServeurHTTP(unittest.TestCase):
    """La commande kplus --serveur, avec de vraies requêtes HTTP."""

    def test_commande_kplus_serveur(self):
        with tempfile.TemporaryDirectory() as d:
            programme = Path(d) / "livre.kplus"
            programme.write_text(LIVRE, encoding="utf-8")
            port = port_libre()
            processus = subprocess.Popen(
                [sys.executable, "-m", "kplus", "--serveur", str(programme), "--port", str(port)],
                cwd=RACINE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8",
                env=dict(os.environ, PYTHONIOENCODING="utf-8"))
            try:
                premiere = processus.stdout.readline()
                self.assertIn(f"http://localhost:{port}", premiere)
                ouvreur = urllib.request.build_opener(
                    urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
                base = f"http://127.0.0.1:{port}"
                page = ouvreur.open(base + "/", timeout=10).read().decode()
                jeton = re.search(r'name="_jeton" value="([^"]+)"', page).group(1)
                donnees = urllib.parse.urlencode({"_jeton": jeton, "nom": "Awa", "message": "Bonjour"})
                page = ouvreur.open(base + "/ecrire", data=donnees.encode(), timeout=10).read().decode()
                self.assertIn("<li>Awa : Bonjour</li>", page)       # redirection suivie
                with self.assertRaises(urllib.error.HTTPError) as e:
                    urllib.request.urlopen(base + "/rien", timeout=10)
                self.assertEqual(e.exception.code, 404)
            finally:
                processus.terminate()
                processus.communicate(timeout=10)
            self.assertTrue((Path(d) / "livre.donnees").exists())

    def test_erreurs_de_la_commande(self):
        def kplus_(*args):
            return subprocess.run([sys.executable, "-m", "kplus", *args], cwd=RACINE, capture_output=True,
                                  text=True, encoding="utf-8", timeout=60,
                                  env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        r = kplus_("--serveur")
        self.assertEqual(r.returncode, 2)
        r = kplus_("--serveur", "exemples/bonjour.kplus", "--port", "abc")
        self.assertEqual(r.returncode, 2)
        r = kplus_("--serveur", "exemples/bonjour.kplus")
        self.assertEqual(r.returncode, 1)
        self.assertIn("utiliser serveur", r.stderr)
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "vide.kplus"
            p.write_text("utiliser serveur\n", encoding="utf-8")
            r = kplus_("--serveur", str(p))
            self.assertEqual(r.returncode, 1)
            self.assertIn("aucune page", r.stderr)


if __name__ == "__main__":
    unittest.main()
