"""Bibliothèque web de K+ (« utiliser web »).

Spécification : docs/specification/kplus-web-0.2.md.

Le moteur ne touche jamais directement la page du navigateur. Il tient un
MODÈLE de la page (des objets Element) et produit des COMMANDES : créer un
élément, changer un texte, supprimer… Le navigateur (K+ Studio, site exporté)
applique ces commandes et renvoie les événements (clics, saisies, minuteries).

Ce découpage rend la bibliothèque testable sans navigateur, et sûre : les
textes sont toujours affichés comme du texte, jamais interprétés comme du HTML.
"""

import re

from .erreurs import (
    ErreurExecution, ErreurType, ErreurValeur, SignalQuitter, formater_erreur,
)
from .valeurs import (
    Element, FonctionNative, FonctionUtilisateur, decrire_type, est_fonction,
)

COULEURS = {
    "rouge": "#d62828", "vert": "#2a9d4b", "bleu": "#1d4ed8",
    "jaune": "#f4c20d", "orange": "#f77f00", "violet": "#7b2cbf",
    "rose": "#e5579b", "noir": "#111111", "blanc": "#ffffff", "gris": "#6b7280",
}
MOTIF_COULEUR = re.compile(r"#[0-9a-fA-F]{6}")
INTERVALLE_MIN = 100          # millisecondes, pour toutes_les()
ELEMENTS_MAX = 10_000         # protection contre une boucle qui crée sans fin

GENRES_TEXTE = ("titre", "sous_titre", "paragraphe", "bouton", "ligne", "lien")


class Page:
    """Modèle de la page et file des commandes à envoyer au navigateur."""

    def __init__(self):
        self.elements = {}
        self.compteur = 0
        self.commandes = []

    def emettre(self, **commande):
        self.commandes.append(commande)

    def prendre_commandes(self):
        commandes, self.commandes = self.commandes, []
        return commandes

    def nouveau(self, interp, genre, texte="", parent=None, visible=True, **attributs):
        if len(self.elements) >= ELEMENTS_MAX:
            raise ErreurValeur(f"trop d'éléments dans la page (plus de {ELEMENTS_MAX})",
                               conseil="vérifiez qu'une boucle ne crée pas des éléments sans fin")
        self.compteur += 1
        ligne = getattr(getattr(interp, "noeud_appel", None), "ligne", None)
        e = Element(f"e{self.compteur}", genre, texte, ligne)
        for cle, valeur in attributs.items():
            setattr(e, cle, valeur)
        self.elements[e.id] = e
        if parent is not None:
            e.parent = parent
            parent.enfants.append(e)
        if visible:
            self.emettre(op="creer", id=e.id, genre=genre, texte=texte,
                         parent=parent.id if parent else None, **attributs)
        return e

    def retirer(self, e):
        """Marque un élément et ses descendants comme supprimés."""
        e.supprime = True
        for enfant in e.enfants:
            self.retirer(enfant)
        e.enfants = []


# --- Vérification des arguments ---------------------------------------------

def _texte(fonction, v, position="le texte"):
    if type(v) is not str:
        raise ErreurType(f"{fonction}() attend un texte comme {position}, pas {decrire_type(v)}",
                         conseil="convertissez la valeur avec texte(...)")
    return v


def _element(fonction, v, genres=None, quoi="un élément"):
    if type(v) is not Element:
        raise ErreurType(f"{fonction}() attend {quoi}, pas {decrire_type(v)}")
    if v.supprime:
        raise ErreurValeur(f"{fonction}() : cet élément a été supprimé de la page")
    if genres is not None and v.genre not in genres:
        raise ErreurType(f"{fonction}() attend {quoi}, pas un élément {v.genre}")
    return v


def _action(fonction, v):
    if not est_fonction(v):
        raise ErreurType(f"{fonction}() attend une fonction comme action, pas {decrire_type(v)}",
                         conseil="donnez le nom d'une fonction, sans parenthèses : "
                                 "bouton(\"OK\", ma_fonction)")
    if type(v) is FonctionUtilisateur and len(v.parametres) > 1:
        raise ErreurType(f"la fonction « {v.nom} » utilisée comme action doit avoir "
                         f"0 ou 1 paramètre, pas {len(v.parametres)}")
    return v


def _couleur(fonction, v):
    _texte(fonction, v, "couleur")
    nom = v.strip().lower()
    if nom in COULEURS:
        return COULEURS[nom]
    if MOTIF_COULEUR.fullmatch(nom):
        return nom
    raise ErreurValeur(f"couleur inconnue : \"{v}\"",
                       conseil="couleurs possibles : " + ", ".join(COULEURS) + ", ou un code #rrggbb")


def _adresse(fonction, v, images=False):
    _texte(fonction, v, "adresse")
    adresse = v.strip()
    schema = re.match(r"([a-zA-Z][a-zA-Z0-9+.-]*):", adresse)
    if schema is None:
        if adresse and not adresse.startswith("//"):
            return adresse                       # adresse relative : photo.jpg
    elif schema.group(1).lower() in ("http", "https"):
        return adresse
    elif images and adresse.lower().startswith("data:image/"):
        return adresse
    raise ErreurValeur(f"adresse refusée : \"{v}\"",
                       conseil="utilisez une adresse qui commence par https:// "
                               "(ou un nom de fichier, comme photo.jpg)")


def _page(interp):
    return interp.page


# --- Fonctions : créer --------------------------------------------------------

def titre(interp, args):
    return _page(interp).nouveau(interp, "titre", _texte("titre", args[0]))


def sous_titre(interp, args):
    return _page(interp).nouveau(interp, "sous_titre", _texte("sous_titre", args[0]))


def paragraphe(interp, args):
    return _page(interp).nouveau(interp, "paragraphe", _texte("paragraphe", args[0]))


def bouton(interp, args):
    action = _action("bouton", args[1])
    e = _page(interp).nouveau(interp, "bouton", _texte("bouton", args[0]))
    e.actions["clic"] = action
    _page(interp).emettre(op="ecouter", id=e.id, evenement="clic")
    return e


def champ(interp, args):
    return _page(interp).nouveau(interp, "champ", etiquette=_texte("champ", args[0], "étiquette"))


def liste(interp, args):
    return _page(interp).nouveau(interp, "liste")


def ajouter_ligne(interp, args):
    parent = _element("ajouter_ligne", args[0], ("liste",), "une liste créée par liste()")
    return _page(interp).nouveau(interp, "ligne", _texte("ajouter_ligne", args[1]), parent=parent)


def image(interp, args):
    adresse = _adresse("image", args[0], images=True)
    description = _texte("image", args[1], "description")
    return _page(interp).nouveau(interp, "image", adresse=adresse, description=description)


def lien(interp, args):
    texte_lien = _texte("lien", args[0])
    return _page(interp).nouveau(interp, "lien", texte_lien, adresse=_adresse("lien", args[1]))


def zone(interp, args):
    return _page(interp).nouveau(interp, "zone")


def placer(interp, args):
    e = _element("placer", args[0], quoi="un élément")
    z = _element("placer", args[1], ("zone",), "une zone créée par zone()")
    if e.genre in ("ligne", "minuterie"):
        raise ErreurType(f"placer() ne peut pas déplacer un élément {e.genre}")
    parent = z
    while parent is not None:
        if parent is e:
            raise ErreurValeur("placer() : on ne peut pas placer une zone dans elle-même")
        parent = parent.parent
    if e.parent is not None:
        e.parent.enfants.remove(e)
    e.parent = z
    z.enfants.append(e)
    _page(interp).emettre(op="deplacer", id=e.id, parent=z.id)
    return None


# --- Fonctions : lire et modifier ---------------------------------------------

def valeur(interp, args):
    return _element("valeur", args[0], ("champ",), "un champ créé par champ()").valeur


def changer_valeur(interp, args):
    e = _element("changer_valeur", args[0], ("champ",), "un champ créé par champ()")
    e.valeur = _texte("changer_valeur", args[1])
    _page(interp).emettre(op="valeur", id=e.id, valeur=e.valeur)
    return None


def texte_de(interp, args):
    e = _element("texte_de", args[0])
    if e.genre == "champ":
        return e.valeur
    if e.genre == "image":
        return e.description
    return e.texte


def changer_texte(interp, args):
    e = _element("changer_texte", args[0], GENRES_TEXTE,
                 "un élément qui affiche un texte (titre, paragraphe, bouton, ligne, lien)")
    e.texte = _texte("changer_texte", args[1])
    _page(interp).emettre(op="texte", id=e.id, texte=e.texte)
    return None


def vider(interp, args):
    e = _element("vider", args[0])
    page = _page(interp)
    if e.genre in ("liste", "zone"):
        for enfant in list(e.enfants):
            page.retirer(enfant)
        e.enfants = []
        page.emettre(op="vider", id=e.id)
    elif e.genre == "champ":
        e.valeur = ""
        page.emettre(op="valeur", id=e.id, valeur="")
    elif e.genre in GENRES_TEXTE:
        e.texte = ""
        page.emettre(op="texte", id=e.id, texte="")
    else:
        raise ErreurType(f"vider() ne s'applique pas à un élément {e.genre}")
    return None


def supprimer(interp, args):
    e = _element("supprimer", args[0])
    page = _page(interp)
    if e.parent is not None:
        e.parent.enfants.remove(e)
    page.retirer(e)
    if e.genre == "minuterie":
        page.emettre(op="arreter_minuterie", id=e.id)
    else:
        page.emettre(op="supprimer", id=e.id)
    return None


def _visibilite(nom, visible):
    def fonction(interp, args):
        e = _element(nom, args[0])
        _page(interp).emettre(op="visible", id=e.id, visible=visible)
        return None
    return fonction


def _style(nom, propriete):
    def fonction(interp, args):
        e = _element(nom, args[0])
        _page(interp).emettre(op="style", id=e.id, propriete=propriete,
                              valeur=_couleur(nom, args[1]))
        return None
    return fonction


def titre_page(interp, args):
    _page(interp).emettre(op="titre_page", texte=_texte("titre_page", args[0]))
    return None


# --- Fonctions : réagir --------------------------------------------------------

def quand_clic(interp, args):
    e = _element("quand_clic", args[0])
    if e.genre == "minuterie":
        raise ErreurType("quand_clic() ne s'applique pas à une minuterie")
    e.actions["clic"] = _action("quand_clic", args[1])
    _page(interp).emettre(op="ecouter", id=e.id, evenement="clic")
    return None


def quand_change(interp, args):
    e = _element("quand_change", args[0], ("champ",), "un champ créé par champ()")
    e.actions["change"] = _action("quand_change", args[1])
    _page(interp).emettre(op="ecouter", id=e.id, evenement="change")
    return None


def toutes_les(interp, args):
    intervalle = args[0]
    if type(intervalle) is not int:
        raise ErreurType(f"toutes_les() attend un nombre entier de millisecondes, "
                         f"pas {decrire_type(intervalle)}")
    if intervalle < INTERVALLE_MIN:
        raise ErreurValeur(f"toutes_les() : l'intervalle doit être d'au moins "
                           f"{INTERVALLE_MIN} millisecondes")
    action = _action("toutes_les", args[1])
    page = _page(interp)
    e = page.nouveau(interp, "minuterie", visible=False)
    e.actions["minuterie"] = action
    page.emettre(op="minuterie", id=e.id, intervalle=intervalle)
    return e


def arreter_minuterie(interp, args):
    e = _element("arreter_minuterie", args[0], ("minuterie",), "une minuterie créée par toutes_les()")
    e.supprime = True
    _page(interp).emettre(op="arreter_minuterie", id=e.id)
    return None


# nom -> (nombre minimal d'arguments, nombre maximal, fonction)
NATIVES = {
    "titre": (1, 1, titre),
    "sous_titre": (1, 1, sous_titre),
    "paragraphe": (1, 1, paragraphe),
    "bouton": (2, 2, bouton),
    "champ": (1, 1, champ),
    "liste": (0, 0, liste),
    "ajouter_ligne": (2, 2, ajouter_ligne),
    "image": (2, 2, image),
    "lien": (2, 2, lien),
    "zone": (0, 0, zone),
    "placer": (2, 2, placer),
    "valeur": (1, 1, valeur),
    "changer_valeur": (2, 2, changer_valeur),
    "texte_de": (1, 1, texte_de),
    "changer_texte": (2, 2, changer_texte),
    "vider": (1, 1, vider),
    "supprimer": (1, 1, supprimer),
    "cacher": (1, 1, _visibilite("cacher", False)),
    "montrer": (1, 1, _visibilite("montrer", True)),
    "couleur": (2, 2, _style("couleur", "color")),
    "couleur_fond": (2, 2, _style("couleur_fond", "background-color")),
    "titre_page": (1, 1, titre_page),
    "quand_clic": (2, 2, quand_clic),
    "quand_change": (2, 2, quand_change),
    "toutes_les": (2, 2, toutes_les),
    "arreter_minuterie": (1, 1, arreter_minuterie),
}

NOMS_WEB = frozenset(NATIVES)


def fonctions_natives():
    return {nom: FonctionNative(nom, mini, maxi, f) for nom, (mini, maxi, f) in NATIVES.items()}


# --- Événements ------------------------------------------------------------------

class _NoeudAction:
    """Position utilisée dans la pile d'appels quand une action est déclenchée."""

    def __init__(self, ligne):
        self.ligne = ligne
        self.colonne = 1


def declencher(interp, ident, evenement, valeurs=None, source=None):
    """Exécute l'action liée à un événement du navigateur.

    `valeurs` : contenu actuel des champs ({identifiant: texte}), lu par le
    navigateur au moment de l'événement. Renvoie None, ou le message de
    l'erreur K+ survenue dans l'action (affiché aussi dans la page).
    """
    page = interp.page
    for cle, contenu in (valeurs or {}).items():
        e = page.elements.get(cle)
        if e is not None and e.genre == "champ" and not e.supprime and type(contenu) is str:
            e.valeur = contenu
    e = page.elements.get(ident)
    if e is None or e.supprime:
        return None
    action = e.actions.get(evenement)
    if action is None:
        return None
    if type(action) is FonctionUtilisateur:
        arguments = [e] if len(action.parametres) == 1 else []
    else:
        arguments = [] if action.arite_min == 0 else [e]
    try:
        interp.appeler_action(action, arguments, _NoeudAction(e.ligne))
    except SignalQuitter:
        for autre in page.elements.values():
            if autre.genre == "minuterie" and not autre.supprime:
                autre.supprime = True
                page.emettre(op="arreter_minuterie", id=autre.id)
    except ErreurExecution as erreur:
        if evenement == "minuterie":
            e.supprime = True
            page.emettre(op="arreter_minuterie", id=e.id)
        texte = formater_erreur(erreur, source)
        page.emettre(op="erreur", texte=texte)
        return texte
    return None
