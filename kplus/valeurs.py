"""Valeurs de K+ et leur représentation.

Correspondance entre les types K+ et Python :
    entier   -> int        décimal  -> float     texte -> str
    booléen  -> bool       nul      -> None      liste -> list
    fonction -> FonctionUtilisateur ou FonctionNative

Attention : en Python, bool est un sous-type de int. On teste donc toujours
« type(v) is int » et jamais « isinstance(v, int) ».
"""


class FonctionUtilisateur:
    """Fonction écrite en K+ avec « fonction ... fin »."""

    __slots__ = ("nom", "parametres", "corps", "fermeture")

    def __init__(self, nom, parametres, corps, fermeture):
        self.nom = nom
        self.parametres = parametres
        self.corps = corps
        self.fermeture = fermeture      # environnement de définition


class FonctionNative:
    """Fonction fournie par K+ (afficher, longueur, ...)."""

    __slots__ = ("nom", "arite_min", "arite_max", "implementation")

    def __init__(self, nom, arite_min, arite_max, implementation):
        self.nom = nom
        self.arite_min = arite_min
        self.arite_max = arite_max      # None = pas de limite
        self.implementation = implementation


def est_nombre(v) -> bool:
    return type(v) is int or type(v) is float


def est_fonction(v) -> bool:
    return isinstance(v, (FonctionUtilisateur, FonctionNative))


def nom_type(v) -> str:
    t = type(v)
    if t is bool:
        return "booléen"
    if t is int:
        return "entier"
    if t is float:
        return "décimal"
    if t is str:
        return "texte"
    if v is None:
        return "nul"
    if t is list:
        return "liste"
    if est_fonction(v):
        return "fonction"
    raise TypeError(f"valeur Python inattendue : {v!r}")  # bogue interne


ARTICLES = {
    "booléen": "un booléen", "entier": "un entier", "décimal": "un décimal",
    "texte": "un texte", "nul": "nul", "liste": "une liste",
    "fonction": "une fonction",
}


def decrire_type(v) -> str:
    """« un entier », « une liste », ... pour les messages d'erreur."""
    return ARTICLES[nom_type(v)]


def _texte_entre_guillemets(t: str) -> str:
    t = (t.replace("\\", "\\\\").replace('"', '\\"')
         .replace("\n", "\\n").replace("\t", "\\t"))
    return f'"{t}"'


def representer(v, imbrique: bool = False, _en_cours=None) -> str:
    """Représentation textuelle d'une valeur (spécification §4.2).

    imbrique=True : la valeur est dans une liste, les textes sont alors
    affichés entre guillemets.
    """
    t = type(v)
    if t is bool:
        return "vrai" if v else "faux"
    if v is None:
        return "nul"
    if t is int:
        return str(v)
    if t is float:
        return repr(v)
    if t is str:
        return _texte_entre_guillemets(v) if imbrique else v
    if t is list:
        en_cours = _en_cours if _en_cours is not None else set()
        if id(v) in en_cours:
            return "[...]"                  # liste qui se contient elle-même
        en_cours.add(id(v))
        try:
            return "[" + ", ".join(
                representer(e, True, en_cours) for e in v) + "]"
        finally:
            en_cours.discard(id(v))
    if est_fonction(v):
        return f"<fonction {v.nom}>"
    raise TypeError(f"valeur Python inattendue : {v!r}")  # bogue interne


def egal(a, b) -> bool:
    """Égalité K+ (opérateur ==) : ne provoque jamais d'erreur."""
    if est_nombre(a) and est_nombre(b):
        return a == b
    if type(a) is not type(b):
        return False
    if type(a) is list:
        if a is b:
            return True
        return len(a) == len(b) and all(egal(x, y) for x, y in zip(a, b))
    if est_fonction(a):
        return a is b
    return a == b
