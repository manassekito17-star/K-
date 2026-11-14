"""Bibliothèque serveur de K+ (« utiliser serveur »).

Spécification : docs/specification/kplus-serveur-0.3.md.

Le programme s'exécute une fois au démarrage : il déclare ses pages
(page, formulaire_recu). Ensuite, à chaque visite, le serveur appelle la
fonction de l'adresse demandée ; cette fonction construit une page vierge
avec les fonctions de K+ Web (titre, paragraphe, liste…), que le serveur
transforme en HTML.

Le cœur (Application.traiter) ne dépend pas du réseau : il reçoit une requête
(méthode, adresse, en-têtes, corps) et renvoie une réponse. Il est donc
testable sans serveur ; lancer() le branche sur un vrai serveur HTTP.

Sécurité : textes échappés, jeton anti-CSRF dans chaque formulaire, cookie de
session signé (HttpOnly, SameSite=Lax), mots de passe chiffrés avec scrypt,
données SQLite en requêtes préparées, durée de chaque visite limitée.
"""

import hashlib
import hmac
import html
import json
import re
import secrets
import sys
import threading
import time
import urllib.parse

from . import web
from .pile import DANS_NAVIGATEUR
from .erreurs import (
    ErreurExecution, ErreurType, ErreurValeur, Interruption, SignalQuitter,
    formater_erreur,
)
from .valeurs import FonctionNative, FonctionUtilisateur, decrire_type, est_fonction

DUREE_MAX = 10                    # secondes de calcul au plus par visite
CORPS_MAX = 1_000_000             # octets au plus par formulaire envoyé
SESSIONS_MAX = 10_000             # sessions gardées en mémoire
NOM_COOKIE = "kplus_session"
MOTIF_NOM = re.compile(r"[^\W\d]\w{0,63}")          # nom de table, de champ, de paramètre
MOTIF_ADRESSE = re.compile(r"/[^\s?#]*")

# Fonctions de K+ Web utilisables pour construire une page côté serveur.
# Les actions du navigateur (bouton, champ, quand_clic, toutes_les…) n'ont pas
# de sens ici : on utilise un formulaire à la place.
WEB_SERVEUR = (
    "titre", "sous_titre", "paragraphe", "liste", "ajouter_ligne", "image", "lien",
    "zone", "texte_de", "changer_texte", "vider", "supprimer", "cacher", "montrer",
    "couleur", "couleur_fond", "titre_page",
)
CHAMPS = ("champ_texte", "zone_texte", "mot_de_passe")
GENRES_FORMULAIRE = CHAMPS + ("bouton_envoyer",)

STYLE = """
body{font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;margin:0;background:#f7f7fb;color:#1f2330}
main{max-width:760px;margin:0 auto;padding:24px 16px 48px}
h1{font-size:1.9rem;margin:.3em 0 .5em}h2{font-size:1.35rem;margin:1.2em 0 .4em}
p{line-height:1.55}a{color:#1d4ed8}img{max-width:100%;height:auto}
.zone{border:1px solid #d9dbe5;border-radius:10px;padding:12px 16px;margin:12px 0;background:#fff}
form{display:grid;gap:12px;margin:16px 0;padding:16px;border:1px solid #d9dbe5;border-radius:10px;background:#fff}
label{display:grid;gap:4px;font-weight:600}
input,textarea{font:inherit;font-weight:400;padding:8px 10px;border:1px solid #b9bdcc;border-radius:8px}
textarea{min-height:6em}
button{font:inherit;justify-self:start;padding:8px 18px;border:0;border-radius:8px;background:#1d4ed8;color:#fff;cursor:pointer}
pre{white-space:pre-wrap;background:#fff3f3;border:1px solid #f1b5b5;border-radius:8px;padding:12px;overflow:auto}
"""

ENTETES_SECURITE = [
    ("Content-Security-Policy",
     "default-src 'none'; img-src 'self' https: data:; style-src 'unsafe-inline'; "
     "form-action 'self'; base-uri 'none'; frame-ancestors 'none'"),
    ("X-Content-Type-Options", "nosniff"),
    ("Referrer-Policy", "same-origin"),
    ("X-Frame-Options", "DENY"),
]


# --- Vérification des arguments ---------------------------------------------------

def _texte(fonction, v, position="le texte"):
    if type(v) is not str:
        raise ErreurType(f"{fonction}() attend un texte comme {position}, pas {decrire_type(v)}",
                         conseil="convertissez la valeur avec texte(...)")
    return v


def _nom(fonction, v, quoi="nom"):
    _texte(fonction, v, quoi)
    if not MOTIF_NOM.fullmatch(v):
        raise ErreurValeur(f"{fonction}() : {quoi} invalide : \"{v}\"",
                           conseil="utilisez des lettres, des chiffres et _, sans espace "
                                   "(par exemple \"messages\" ou \"nom_complet\")")
    return v


def _adresse_locale(fonction, v):
    _texte(fonction, v, "adresse")
    if not MOTIF_ADRESSE.fullmatch(v) or v.startswith("//"):
        raise ErreurValeur(f"{fonction}() : adresse invalide : \"{v}\"",
                           conseil="une adresse du site commence par / : \"/\", \"/contact\", "
                                   "\"/article/{numero}\"")
    return v


def _fonction_sans_parametre(fonction, v):
    if not est_fonction(v):
        raise ErreurType(f"{fonction}() attend une fonction, pas {decrire_type(v)}",
                         conseil="donnez le nom d'une fonction, sans parenthèses : "
                                 "page(\"/\", accueil)")
    if type(v) is FonctionUtilisateur and v.parametres:
        raise ErreurType(f"la fonction « {v.nom} » utilisée par {fonction}() ne doit pas avoir "
                         f"de paramètre", conseil="lisez les données avec donnee(…) ou parametre(…)")
    return v


def _valeur_simple(fonction, v, quoi="la valeur"):
    if v is None or type(v) in (str, int, float, bool):
        return v
    raise ErreurType(f"{fonction}() : {quoi} doit être un texte, un nombre, un booléen ou nul, "
                     f"pas {decrire_type(v)}")


def _ligne(fonction, v):
    if type(v) is not list:
        raise ErreurType(f"{fonction}() attend une liste de valeurs comme ligne, pas {decrire_type(v)}",
                         conseil="par exemple : [\"Awa\", \"Bonjour !\"]")
    if len(v) > 100:
        raise ErreurValeur(f"{fonction}() : une ligne contient au plus 100 valeurs")
    return [_valeur_simple(fonction, x, "chaque valeur de la ligne") for x in v]


def _numero(fonction, v):
    if type(v) is not int:
        raise ErreurType(f"{fonction}() attend un numéro de ligne entier, pas {decrire_type(v)}",
                         conseil="un numéro reçu dans une adresse est un texte : "
                                 "convertissez-le avec entier(...)")
    return v


# --- Données enregistrées (tables) ---------------------------------------------------

class DonneesMemoire:
    """Tables gardées en mémoire, sans SQLite : aperçu dans le navigateur
    (Pyodide n'inclut pas SQLite). Même comportement que Donnees."""

    def __init__(self):
        self.tables = {}
        self.compteurs = {}

    def enregistrer(self, table, ligne):
        numero = self.compteurs.get(table, 0) + 1
        self.compteurs[table] = numero
        self.tables.setdefault(table, {})[numero] = json.dumps(ligne, ensure_ascii=False)
        return numero

    def lire_tout(self, table):
        lignes = self.tables.get(table, {})
        return [[numero] + json.loads(lignes[numero]) for numero in sorted(lignes)]

    def lire(self, table, numero):
        v = self.tables.get(table, {}).get(numero)
        return None if v is None else [numero] + json.loads(v)

    def modifier(self, table, numero, ligne):
        lignes = self.tables.get(table, {})
        if numero not in lignes:
            return False
        lignes[numero] = json.dumps(ligne, ensure_ascii=False)
        return True

    def effacer(self, table, numero):
        return self.tables.get(table, {}).pop(numero, None) is not None

    def compter(self, table):
        return len(self.tables.get(table, {}))

    def fermer(self):
        pass


def ouvrir_donnees(fichier=":memory:"):
    """Tables SQLite ; en mémoire sans SQLite quand il est absent (navigateur)."""
    try:
        import sqlite3  # noqa: F401
    except ImportError:
        if fichier != ":memory:":
            raise
        return DonneesMemoire()
    return Donnees(fichier)


class Donnees:
    """Tables du programme, rangées dans un fichier SQLite (requêtes préparées)."""

    def __init__(self, fichier=":memory:"):
        import sqlite3
        self.verrou = threading.Lock()
        self.connexion = sqlite3.connect(fichier, check_same_thread=False)
        with self.connexion:
            self.connexion.execute(
                "create table if not exists kplus_lignes (tab text not null, numero integer not null, "
                "valeurs text not null, primary key (tab, numero))")
            self.connexion.execute(
                "create table if not exists kplus_compteurs (tab text primary key, dernier integer not null)")

    def enregistrer(self, table, ligne):
        with self.verrou, self.connexion:
            r = self.connexion.execute("select dernier from kplus_compteurs where tab = ?", (table,)).fetchone()
            numero = (r[0] if r else 0) + 1
            self.connexion.execute("insert or replace into kplus_compteurs (tab, dernier) values (?, ?)",
                                   (table, numero))
            self.connexion.execute("insert into kplus_lignes (tab, numero, valeurs) values (?, ?, ?)",
                                   (table, numero, json.dumps(ligne, ensure_ascii=False)))
        return numero

    def lire_tout(self, table):
        with self.verrou:
            lignes = self.connexion.execute(
                "select numero, valeurs from kplus_lignes where tab = ? order by numero", (table,)).fetchall()
        return [[numero] + json.loads(valeurs) for numero, valeurs in lignes]

    def lire(self, table, numero):
        with self.verrou:
            r = self.connexion.execute("select valeurs from kplus_lignes where tab = ? and numero = ?",
                                       (table, numero)).fetchone()
        return None if r is None else [numero] + json.loads(r[0])

    def modifier(self, table, numero, ligne):
        with self.verrou, self.connexion:
            n = self.connexion.execute("update kplus_lignes set valeurs = ? where tab = ? and numero = ?",
                                       (json.dumps(ligne, ensure_ascii=False), table, numero)).rowcount
        return n > 0

    def effacer(self, table, numero):
        with self.verrou, self.connexion:
            n = self.connexion.execute("delete from kplus_lignes where tab = ? and numero = ?",
                                       (table, numero)).rowcount
        return n > 0

    def compter(self, table):
        with self.verrou:
            return self.connexion.execute("select count(*) from kplus_lignes where tab = ?",
                                          (table,)).fetchone()[0]

    def fermer(self):
        self.connexion.close()

    def __del__(self):
        try:
            self.connexion.close()
        except Exception:
            pass


# --- Mots de passe -----------------------------------------------------------------

SCRYPT_N, SCRYPT_R, SCRYPT_P = 2 ** 14, 8, 1
PBKDF2_TOURS = 20_000      # repli sans scrypt (aperçu dans le navigateur)


def _pbkdf2(mot_de_passe: bytes, sel: bytes, tours: int) -> bytes:
    """PBKDF2-HMAC-SHA256 (RFC 8018), un bloc de 32 octets, en Python pur :
    Pyodide n'a ni scrypt ni pbkdf2_hmac (pas d'OpenSSL)."""
    base = hmac.new(mot_de_passe, digestmod=hashlib.sha256)

    def prf(donnees):
        h = base.copy()
        h.update(donnees)
        return h.digest()

    u = prf(sel + b"\x00\x00\x00\x01")
    resultat = int.from_bytes(u, "big")
    for _ in range(tours - 1):
        u = prf(u)
        resultat ^= int.from_bytes(u, "big")
    return resultat.to_bytes(32, "big")


def chiffrer(mot_de_passe: str) -> str:
    """Empreinte salée d'un mot de passe : scrypt, ou PBKDF2 là où scrypt manque."""
    sel = secrets.token_bytes(16)
    if hasattr(hashlib, "scrypt"):
        empreinte = hashlib.scrypt(mot_de_passe.encode("utf-8"), salt=sel,
                                   n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=32)
        return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${sel.hex()}${empreinte.hex()}"
    empreinte = _pbkdf2(mot_de_passe.encode("utf-8"), sel, PBKDF2_TOURS)
    return f"pbkdf2_sha256${PBKDF2_TOURS}${sel.hex()}${empreinte.hex()}"


def verifier(mot_de_passe: str, empreinte: str) -> bool:
    morceaux = empreinte.split("$")
    try:
        if morceaux[0] == "scrypt" and len(morceaux) == 6:
            n, r, p = (int(x) for x in morceaux[1:4])
            if not (2 <= n <= 2 ** 20 and 1 <= r <= 32 and 1 <= p <= 16):
                raise ValueError
            sel, attendu = bytes.fromhex(morceaux[4]), bytes.fromhex(morceaux[5])
            if not hasattr(hashlib, "scrypt"):
                raise ErreurValeur("cette empreinte (scrypt) ne peut pas être vérifiée ici",
                                   conseil="lancez le site avec « kplus --serveur » sur un ordinateur")
            calcule = hashlib.scrypt(mot_de_passe.encode("utf-8"), salt=sel, n=n, r=r, p=p,
                                     dklen=len(attendu), maxmem=2 ** 26)
        elif morceaux[0] == "pbkdf2_sha256" and len(morceaux) == 4:
            tours = int(morceaux[1])
            if not 1_000 <= tours <= 10_000_000:
                raise ValueError
            sel, attendu = bytes.fromhex(morceaux[2]), bytes.fromhex(morceaux[3])
            calcule = _pbkdf2(mot_de_passe.encode("utf-8"), sel, tours)
        else:
            raise ValueError
    except ValueError:
        raise ErreurValeur("verifier_mot_de_passe() : empreinte invalide",
                           conseil="donnez une empreinte créée par chiffrer_mot_de_passe(...)") from None
    return hmac.compare_digest(calcule, attendu)


# --- Application ---------------------------------------------------------------------

class Route:
    def __init__(self, adresse, fonction, ligne):
        self.adresse = adresse
        self.fonction = fonction
        self.ligne = ligne
        motif, noms = "", []
        for morceau in re.split(r"(\{[^{}]*\})", adresse):
            if morceau.startswith("{") and morceau.endswith("}"):
                nom = morceau[1:-1]
                if not MOTIF_NOM.fullmatch(nom) or nom in noms:
                    raise ErreurValeur(f"adresse invalide : \"{adresse}\" (paramètre « {nom} »)",
                                       conseil="un paramètre s'écrit entre accolades avec un nom "
                                               "simple : \"/article/{numero}\"")
                noms.append(nom)
                motif += f"(?P<{nom}>[^/]+)"
            elif "{" in morceau or "}" in morceau:
                raise ErreurValeur(f"adresse invalide : \"{adresse}\" (accolade mal fermée)")
            else:
                motif += re.escape(morceau)
        self.motif = re.compile(motif)
        self.noms = noms

    def correspond(self, chemin):
        m = self.motif.fullmatch(chemin)
        return None if m is None else m.groupdict()


class Requete:
    def __init__(self, methode, chemin, parametres, donnees, session):
        self.methode = methode
        self.chemin = chemin
        self.parametres = parametres
        self.donnees = donnees
        self.session = session
        self.redirection = None


class Reponse:
    def __init__(self, statut, corps=b"", entetes=None):
        self.statut = statut
        self.corps = corps
        self.entetes = list(entetes or [])

    def entete(self, nom):
        for cle, valeur in self.entetes:
            if cle.lower() == nom.lower():
                return valeur
        return None


class Application:
    """Site K+ : routes déclarées au démarrage, traitement de chaque requête."""

    def __init__(self, interp, fichier_donnees=":memory:", production=False):
        self.interp = interp
        self.pages = []
        self.formulaires = []
        self.donnees = ouvrir_donnees(fichier_donnees)
        self.production = production
        self.secret = secrets.token_bytes(32)
        self.sessions = {}
        self.requete = None
        self.source = None

    # --- déclarations -------------------------------------------------------------

    def declarer(self, liste, quoi, adresse, fonction):
        if self.requete is not None:
            raise ErreurValeur(f"{quoi}() se déclare au démarrage du programme, pas pendant une visite",
                               conseil=f"écrivez {quoi}(...) au niveau principal du programme")
        for route in liste:
            if route.adresse == adresse:
                raise ErreurValeur(f"{quoi}() : l'adresse \"{adresse}\" est déjà déclarée")
        ligne = getattr(getattr(self.interp, "noeud_appel", None), "ligne", None)
        liste.append(Route(adresse, fonction, ligne))

    def demander_visite(self, fonction):
        if self.requete is None:
            raise ErreurValeur(f"{fonction}() n'est disponible que pendant une visite",
                               conseil=f"appelez {fonction}(...) dans une fonction de page "
                                       f"ou de formulaire")
        return self.requete

    # --- sessions et jetons ------------------------------------------------------------

    def _signer(self, texte):
        return hmac.new(self.secret, texte.encode(), hashlib.sha256).hexdigest()

    def jeton(self, ident):
        return self._signer("formulaire:" + ident)

    def _session(self, en_tetes):
        """Renvoie (identifiant, données, nouvelle ?)."""
        cookie = en_tetes.get("cookie", "")
        for morceau in cookie.split(";"):
            cle, _, valeur = morceau.strip().partition("=")
            if cle == NOM_COOKIE and "." in valeur:
                ident, _, signature = valeur.partition(".")
                if hmac.compare_digest(signature, self._signer("session:" + ident)) \
                        and ident in self.sessions:
                    return ident, self.sessions[ident], False
        while len(self.sessions) >= SESSIONS_MAX:
            del self.sessions[next(iter(self.sessions))]       # la plus ancienne
        ident = secrets.token_urlsafe(24)
        self.sessions[ident] = {}
        return ident, self.sessions[ident], True

    def _cookie(self, ident):
        valeur = f"{NOM_COOKIE}={ident}.{self._signer('session:' + ident)}; Path=/; HttpOnly; SameSite=Lax"
        return valeur + ("; Secure" if self.production else "")

    # --- traitement d'une requête ----------------------------------------------------

    def traiter(self, methode, cible, en_tetes=None, corps=b"") -> Reponse:
        en_tetes = {k.lower(): v for k, v in (en_tetes or {}).items()}
        methode = methode.upper()
        morceaux = urllib.parse.urlsplit(cible)
        chemin = urllib.parse.unquote(morceaux.path) or "/"
        ident, session, nouvelle = self._session(en_tetes)
        reponse = self._traiter(methode, chemin, morceaux.query, en_tetes, corps, ident, session)
        if nouvelle:
            reponse.entetes.append(("Set-Cookie", self._cookie(ident)))
        reponse.entetes.extend(ENTETES_SECURITE)
        reponse.entetes.append(("Cache-Control", "no-store"))
        if methode == "HEAD":
            reponse.corps = b""
        return reponse

    def _traiter(self, methode, chemin, requete_texte, en_tetes, corps, ident, session):
        if methode in ("GET", "HEAD"):
            routes, autres = self.pages, self.formulaires
            donnees = dict(urllib.parse.parse_qsl(requete_texte, keep_blank_values=True))
        elif methode == "POST":
            routes, autres = self.formulaires, self.pages
            if len(corps) > CORPS_MAX:
                return self._page_message(413, "Formulaire trop volumineux",
                                          "Les données envoyées dépassent la taille autorisée.")
            type_contenu = en_tetes.get("content-type", "").split(";")[0].strip().lower()
            if type_contenu != "application/x-www-form-urlencoded":
                return self._page_message(415, "Formulaire non reconnu",
                                          "Ce site n'accepte que les formulaires ordinaires.")
            try:
                donnees = dict(urllib.parse.parse_qsl(corps.decode("utf-8"), keep_blank_values=True))
            except UnicodeDecodeError:
                return self._page_message(400, "Formulaire illisible", "Les données reçues sont illisibles.")
            if not self._origine_acceptee(en_tetes) or not hmac.compare_digest(
                    donnees.pop("_jeton", ""), self.jeton(ident)):
                return self._page_message(
                    403, "Formulaire refusé",
                    "Ce formulaire a expiré ou vient d'un autre site. Rechargez la page et réessayez.")
        else:
            return self._page_message(405, "Méthode non autorisée", "Cette méthode n'est pas acceptée.",
                                      [("Allow", "GET, HEAD, POST")])
        for route in routes:
            parametres = route.correspond(chemin)
            if parametres is not None:
                return self._executer(route, Requete(methode, chemin, parametres, donnees, session), ident)
        if any(route.correspond(chemin) is not None for route in autres):
            return self._page_message(405, "Méthode non autorisée",
                                      "Cette adresse reçoit un formulaire : elle ne s'ouvre pas directement."
                                      if methode != "POST" else "Cette adresse n'accepte pas de formulaire.")
        return self._page_message(404, "Page introuvable",
                                  "L'adresse demandée n'existe pas sur ce site.")

    @staticmethod
    def _origine_acceptee(en_tetes):
        origine = en_tetes.get("origin")
        if origine is None or origine == "null":
            return origine is None
        hote = en_tetes.get("host", "")
        return urllib.parse.urlsplit(origine).netloc == hote

    def _executer(self, route, requete, ident):
        interp = self.interp
        interp.page = web.Page()
        self.requete = requete
        requete.ident = ident
        # Dans le navigateur (Pyodide), pas de fil : le Web Worker a sa propre limite de durée.
        minuteur = None
        if not DANS_NAVIGATEUR:
            minuteur = threading.Timer(DUREE_MAX, lambda: setattr(interp, "interrompu", True))
            minuteur.daemon = True
            minuteur.start()
        try:
            interp.appeler_action(route.fonction, [], web._NoeudAction(route.ligne))
        except SignalQuitter:
            pass
        except Interruption:
            return self._page_erreur(
                f"La page a mis plus de {DUREE_MAX} secondes à se construire : elle a été arrêtée. "
                f"Vérifiez qu'il n'y a pas de boucle infinie.")
        except ErreurExecution as erreur:
            return self._page_erreur(formater_erreur(erreur, self.source))
        finally:
            if minuteur is not None:
                minuteur.cancel()
            interp.interrompu = False
            self.requete = None
            page, interp.page = interp.page, None
        if requete.redirection is not None:
            return Reponse(303, b"", [("Location", requete.redirection)])
        return Reponse(200, rendre(page, self.jeton(ident)).encode("utf-8"),
                       [("Content-Type", "text/html; charset=utf-8")])

    def _page_erreur(self, detail):
        if self.production:
            return self._page_message(500, "Erreur du site",
                                      "Une erreur est survenue. Réessayez plus tard.")
        print(detail, file=sys.stderr)
        return self._page_message(500, "Erreur dans le programme K+",
                                  "Cette page n'a pas pu être construite :", detail=detail)

    @staticmethod
    def _page_message(statut, titre, texte, entetes=(), detail=None):
        corps = f"<h1>{html.escape(titre)}</h1><p>{html.escape(texte)}</p>"
        if detail:
            corps += f"<pre>{html.escape(detail)}</pre>"
        corps += '<p><a href="/">Retour à l\'accueil</a></p>'
        return Reponse(statut, _document(f"{statut} — {titre}", corps).encode("utf-8"),
                       [("Content-Type", "text/html; charset=utf-8"), *entetes])


# --- Page HTML ----------------------------------------------------------------------

def _document(titre, corps):
    return ('<!doctype html>\n<html lang="fr"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            f"<title>{html.escape(titre)}</title><style>{STYLE}</style></head>"
            f"<body><main>{corps}</main></body></html>\n")


def rendre(page, jeton) -> str:
    """Transforme le modèle de la page (K+ Web) en HTML, textes échappés."""
    styles, caches, titre = {}, set(), "Site K+"
    for c in page.prendre_commandes():
        if c["op"] == "style":
            styles.setdefault(c["id"], {})[c["propriete"]] = c["valeur"]
        elif c["op"] == "visible":
            (caches.discard if c["visible"] else caches.add)(c["id"])
        elif c["op"] == "titre_page":
            titre = c["texte"]
    e_ = html.escape

    def attributs(e):
        texte = ""
        if e.id in styles:
            # Couleurs déjà vérifiées par K+ Web (#rrggbb).
            texte += ' style="' + ";".join(f"{p}:{v}" for p, v in styles[e.id].items()) + '"'
        if e.id in caches:
            texte += " hidden"
        return texte

    def enfants(e):
        return "".join(element(x) for x in e.enfants if not x.supprime)

    def element(e):
        a, g = attributs(e), e.genre
        if g == "titre":
            return f"<h1{a}>{e_(e.texte)}</h1>"
        if g == "sous_titre":
            return f"<h2{a}>{e_(e.texte)}</h2>"
        if g == "paragraphe":
            return f"<p{a}>{e_(e.texte)}</p>"
        if g == "liste":
            return f"<ul{a}>{enfants(e)}</ul>"
        if g == "ligne":
            return f"<li{a}>{e_(e.texte)}</li>"
        if g == "lien":
            return f'<a href="{e_(e.adresse)}"{a}>{e_(e.texte)}</a>'
        if g == "image":
            return f'<img src="{e_(e.adresse)}" alt="{e_(e.description)}"{a}>'
        if g == "zone":
            return f'<div class="zone"{a}>{enfants(e)}</div>'
        if g == "formulaire":
            return (f'<form method="post" action="{e_(e.adresse)}"{a}>'
                    f'<input type="hidden" name="_jeton" value="{e_(jeton)}">{enfants(e)}</form>')
        if g in ("champ_texte", "mot_de_passe"):
            genre = "password" if g == "mot_de_passe" else "text"
            complement = ' autocomplete="current-password"' if g == "mot_de_passe" else ""
            return (f'<label{a}><span>{e_(e.etiquette)}</span>'
                    f'<input type="{genre}" name="{e_(e.nom)}"{complement}></label>')
        if g == "zone_texte":
            return (f'<label{a}><span>{e_(e.etiquette)}</span>'
                    f'<textarea name="{e_(e.nom)}"></textarea></label>')
        if g == "bouton_envoyer":
            return f'<button type="submit"{a}>{e_(e.texte)}</button>'
        return ""

    corps = "".join(element(e) for e in page.elements.values()
                    if e.parent is None and not e.supprime and e.genre != "minuterie")
    return _document(titre, corps)


# --- Fonctions natives --------------------------------------------------------------

def _app(interp):
    return interp.serveur


def _page_web(nom, fonction):
    """Fonction de K+ Web, utilisable seulement pendant une visite."""
    def enveloppe(interp, args):
        if _app(interp).requete is None:
            raise ErreurValeur(f"{nom}() construit une page : appelez-le dans une fonction de page",
                               conseil="par exemple : fonction accueil() … titre(\"Bienvenue\") … fin, "
                                       "puis page(\"/\", accueil)")
        return fonction(interp, args)
    return enveloppe


def page(interp, args):
    _app(interp).declarer(_app(interp).pages, "page", _adresse_locale("page", args[0]),
                          _fonction_sans_parametre("page", args[1]))
    return None


def formulaire_recu(interp, args):
    _app(interp).declarer(_app(interp).formulaires, "formulaire_recu",
                          _adresse_locale("formulaire_recu", args[0]),
                          _fonction_sans_parametre("formulaire_recu", args[1]))
    return None


def parametre(interp, args):
    requete = _app(interp).demander_visite("parametre")
    nom = _texte("parametre", args[0], "nom")
    if nom not in requete.parametres:
        disponibles = ", ".join(requete.parametres) or "aucun"
        raise ErreurValeur(f"parametre() : l'adresse n'a pas de paramètre « {nom} »",
                           conseil=f"paramètres de cette adresse : {disponibles}")
    return requete.parametres[nom]


def rediriger(interp, args):
    requete = _app(interp).demander_visite("rediriger")
    requete.redirection = _adresse_locale("rediriger", args[0])
    return None


def donnee(interp, args):
    requete = _app(interp).demander_visite("donnee")
    return requete.donnees.get(_texte("donnee", args[0], "nom"), "")


def _nouveau(interp, genre, parent=None, **attributs):
    return interp.page.nouveau(interp, genre, parent=parent, **attributs)


def formulaire(interp, args):
    return _nouveau(interp, "formulaire", adresse=_adresse_locale("formulaire", args[0]))


def _formulaire_parent(fonction, v):
    return web._element(fonction, v, ("formulaire",), "un formulaire créé par formulaire()")


def _champ(genre):
    def fonction(interp, args):
        parent = _formulaire_parent(genre, args[0])
        return _nouveau(interp, genre, parent, nom=_nom(genre, args[1], "nom du champ"),
                        etiquette=_texte(genre, args[2], "étiquette"))
    return fonction


def bouton_envoyer(interp, args):
    parent = _formulaire_parent("bouton_envoyer", args[0])
    e = _nouveau(interp, "bouton_envoyer", parent)
    e.texte = _texte("bouton_envoyer", args[1])
    return e


def placer(interp, args):
    e = web._element("placer", args[0])
    if e.genre in GENRES_FORMULAIRE:
        raise ErreurType(f"placer() ne peut pas sortir un élément {e.genre} de son formulaire",
                         conseil="placez le formulaire entier dans la zone")
    return web.placer(interp, args)


def _table(fonction, v):
    return _nom(fonction, v, "nom de table")


def enregistrer(interp, args):
    return _app(interp).donnees.enregistrer(_table("enregistrer", args[0]), _ligne("enregistrer", args[1]))


def lire_tout(interp, args):
    return _app(interp).donnees.lire_tout(_table("lire_tout", args[0]))


def lire(interp, args):
    return _app(interp).donnees.lire(_table("lire", args[0]), _numero("lire", args[1]))


def modifier(interp, args):
    table, numero = _table("modifier", args[0]), _numero("modifier", args[1])
    if not _app(interp).donnees.modifier(table, numero, _ligne("modifier", args[2])):
        raise ErreurValeur(f"modifier() : aucune ligne numéro {numero} dans la table « {table} »",
                           conseil="vérifiez le numéro avec lire(table, numero) avant de modifier")
    return None


def effacer(interp, args):
    return _app(interp).donnees.effacer(_table("effacer", args[0]), _numero("effacer", args[1]))


def compter(interp, args):
    return _app(interp).donnees.compter(_table("compter", args[0]))


def _valeur_session(fonction, v):
    if type(v) is list:
        return [_valeur_simple(fonction, x, "chaque valeur de la liste") for x in v]
    return _valeur_simple(fonction, v)


def session(interp, args):
    requete = _app(interp).demander_visite("session")
    v = requete.session.get(_texte("session", args[0], "nom"))
    return list(v) if type(v) is list else v


def retenir(interp, args):
    requete = _app(interp).demander_visite("retenir")
    requete.session[_texte("retenir", args[0], "nom")] = _valeur_session("retenir", args[1])
    return None


def oublier(interp, args):
    requete = _app(interp).demander_visite("oublier")
    requete.session.pop(_texte("oublier", args[0], "nom"), None)
    return None


def chiffrer_mot_de_passe(interp, args):
    return chiffrer(_texte("chiffrer_mot_de_passe", args[0], "mot de passe"))


def verifier_mot_de_passe(interp, args):
    return verifier(_texte("verifier_mot_de_passe", args[0], "mot de passe"),
                    _texte("verifier_mot_de_passe", args[1], "empreinte"))


NATIVES = {
    "page": (2, 2, page),
    "formulaire_recu": (2, 2, formulaire_recu),
    "parametre": (1, 1, parametre),
    "rediriger": (1, 1, rediriger),
    "donnee": (1, 1, donnee),
    "formulaire": (1, 1, _page_web("formulaire", formulaire)),
    "champ_texte": (3, 3, _page_web("champ_texte", _champ("champ_texte"))),
    "zone_texte": (3, 3, _page_web("zone_texte", _champ("zone_texte"))),
    "mot_de_passe": (3, 3, _page_web("mot_de_passe", _champ("mot_de_passe"))),
    "bouton_envoyer": (2, 2, _page_web("bouton_envoyer", bouton_envoyer)),
    "placer": (2, 2, _page_web("placer", placer)),
    "enregistrer": (2, 2, enregistrer),
    "lire_tout": (1, 1, lire_tout),
    "lire": (2, 2, lire),
    "modifier": (3, 3, modifier),
    "effacer": (2, 2, effacer),
    "compter": (1, 1, compter),
    "session": (1, 1, session),
    "retenir": (2, 2, retenir),
    "oublier": (1, 1, oublier),
    "chiffrer_mot_de_passe": (1, 1, chiffrer_mot_de_passe),
    "verifier_mot_de_passe": (2, 2, verifier_mot_de_passe),
}
for _nom_web in WEB_SERVEUR:
    _mini, _maxi, _f = web.NATIVES[_nom_web]
    NATIVES[_nom_web] = (_mini, _maxi, _page_web(_nom_web, _f))

NOMS_SERVEUR = frozenset(NATIVES)


def fonctions_natives():
    return {nom: FonctionNative(nom, mini, maxi, f) for nom, (mini, maxi, f) in NATIVES.items()}


# --- Serveur HTTP ---------------------------------------------------------------------

def lancer(app, hote="127.0.0.1", port=8000, journal=sys.stderr, pret=None):
    """Sert le site jusqu'à Ctrl+C. Un seul visiteur est traité à la fois
    (l'interpréteur n'est pas partagé entre plusieurs fils)."""
    from http.server import BaseHTTPRequestHandler, HTTPServer

    class Gestionnaire(BaseHTTPRequestHandler):
        server_version = "KPlus"
        sys_version = ""
        protocol_version = "HTTP/1.0"

        def _repondre(self, methode):
            debut = time.monotonic()
            try:
                longueur = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                longueur = -1
            if longueur < 0 or longueur > CORPS_MAX:
                reponse = app._page_message(413, "Formulaire trop volumineux",
                                            "Les données envoyées dépassent la taille autorisée.")
                reponse.entetes.extend(ENTETES_SECURITE)
            else:
                corps = self.rfile.read(longueur) if longueur else b""
                reponse = app.traiter(methode, self.path, dict(self.headers.items()), corps)
            self.send_response(reponse.statut)
            for cle, valeur in reponse.entetes:
                self.send_header(cle, valeur)
            self.send_header("Content-Length", str(len(reponse.corps)))
            self.end_headers()
            if methode != "HEAD":
                self.wfile.write(reponse.corps)
            duree = (time.monotonic() - debut) * 1000
            print(f"{methode} {self.path} → {reponse.statut} ({duree:.0f} ms)", file=journal, flush=True)

        def do_GET(self):
            self._repondre("GET")

        def do_HEAD(self):
            self._repondre("HEAD")

        def do_POST(self):
            self._repondre("POST")

        def log_message(self, format, *args):     # journal déjà écrit par _repondre
            pass

    serveur = HTTPServer((hote, port), Gestionnaire)
    if pret is not None:
        pret(serveur)
    try:
        serveur.serve_forever(poll_interval=0.2)
    finally:
        serveur.server_close()
