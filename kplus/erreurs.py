"""Erreurs de K+ et mise en forme des messages.

Chaque erreur connaît sa catégorie, sa position (ligne, colonne), un message
et éventuellement un conseil. Les erreurs d'analyse (lexicales, de syntaxe)
surviennent avant l'exécution ; les autres pendant l'exécution et peuvent être
attrapées avec « essayer ... attraper ».
"""

from .jetons import preparer_source


class ErreurKPlus(Exception):
    categorie = "ErreurKPlus"
    nom_affiche = "Erreur"

    def __init__(self, message, ligne=None, colonne=None, conseil=None):
        super().__init__(message)
        self.message = message
        self.ligne = ligne
        self.colonne = colonne
        self.conseil = conseil
        # Pile d'appels : liste de (nom de fonction, ligne de l'appel),
        # de l'appel le plus récent au plus ancien.
        self.pile = []

    def placer(self, ligne, colonne):
        """Fixe la position si elle n'est pas encore connue."""
        if self.ligne is None:
            self.ligne = ligne
            self.colonne = colonne


# --- Erreurs détectées avant l'exécution -----------------------------------

class ErreurAnalyse(ErreurKPlus):
    def __init__(self, message, ligne=None, colonne=None, conseil=None,
                 incomplet=False):
        super().__init__(message, ligne, colonne, conseil)
        # Vrai si le programme est simplement inachevé (bloc ou parenthèse
        # pas encore fermé) : le mode interactif attend alors la suite.
        self.incomplet = incomplet


class ErreurLexicale(ErreurAnalyse):
    categorie = "ErreurLexicale"
    nom_affiche = "Erreur lexicale"


class ErreurSyntaxe(ErreurAnalyse):
    categorie = "ErreurSyntaxe"
    nom_affiche = "Erreur de syntaxe"


# --- Erreurs d'exécution (attrapables) -------------------------------------

class ErreurExecution(ErreurKPlus):
    pass


class ErreurNom(ErreurExecution):
    categorie = "ErreurNom"
    nom_affiche = "Erreur de nom"


class ErreurConstante(ErreurExecution):
    categorie = "ErreurConstante"
    nom_affiche = "Erreur de constante"


class ErreurType(ErreurExecution):
    categorie = "ErreurType"
    nom_affiche = "Erreur de type"


class ErreurValeur(ErreurExecution):
    categorie = "ErreurValeur"
    nom_affiche = "Erreur de valeur"


class ErreurDivisionParZero(ErreurExecution):
    categorie = "ErreurDivisionParZero"
    nom_affiche = "Erreur de division par zéro"


class ErreurIndex(ErreurExecution):
    categorie = "ErreurIndex"
    nom_affiche = "Erreur d'indice"


class ErreurRecursion(ErreurExecution):
    categorie = "ErreurRecursion"
    nom_affiche = "Erreur de récursion"


class ErreurUtilisateur(ErreurExecution):
    categorie = "ErreurUtilisateur"
    nom_affiche = "Erreur"


CATEGORIES = {
    classe.categorie: classe
    for classe in (
        ErreurLexicale, ErreurSyntaxe, ErreurNom, ErreurConstante, ErreurType,
        ErreurValeur, ErreurDivisionParZero, ErreurIndex, ErreurRecursion,
        ErreurUtilisateur,
    )
}


# --- Signaux de contrôle (ce ne sont PAS des erreurs) ----------------------
# Ils servent à interrompre le cours normal de l'exécution
# (retourner, arreter, continuer, quitter, Ctrl+C).

class SignalControle(Exception):
    pass


class SignalRetour(SignalControle):
    def __init__(self, valeur):
        super().__init__()
        self.valeur = valeur


class SignalArret(SignalControle):
    pass


class SignalContinuer(SignalControle):
    pass


class SignalQuitter(Exception):
    def __init__(self, code=0):
        super().__init__(code)
        self.code = code


class Interruption(Exception):
    """Programme interrompu par l'utilisateur (Ctrl+C). Non attrapable."""


# --- Mise en forme ----------------------------------------------------------

PILE_MAX_AFFICHEE = 10


def formater_erreur(erreur: ErreurKPlus, source: str | None = None) -> str:
    """Construit le message d'erreur complet affiché à l'utilisateur."""
    entete = erreur.nom_affiche
    if erreur.ligne is not None:
        entete += f" (ligne {erreur.ligne}, colonne {erreur.colonne})"
    lignes = [f"{entete} : {erreur.message}"]

    if source is not None and erreur.ligne is not None:
        lignes_source = preparer_source(source).split("\n")
        if 1 <= erreur.ligne <= len(lignes_source):
            code = lignes_source[erreur.ligne - 1]
            numero = f"{erreur.ligne:>4}"
            lignes.append(f"{numero} | {code}")
            avant = code[: max(erreur.colonne - 1, 0)]
            # On garde les tabulations pour que le ^ tombe au bon endroit.
            decalage = "".join("\t" if c == "\t" else " " for c in avant)
            lignes.append(f"{' ' * len(numero)} | {decalage}^")

    if erreur.conseil:
        lignes.append(f"Conseil : {erreur.conseil}")

    if erreur.pile:
        lignes.append("Pile d'appels (du plus récent au plus ancien) :")
        # Les appels identiques consécutifs (récursion) sont regroupés.
        groupes = []
        for appel in erreur.pile:
            if groupes and groupes[-1][0] == appel:
                groupes[-1][1] += 1
            else:
                groupes.append([appel, 1])
        omis = 0
        if len(groupes) > PILE_MAX_AFFICHEE:
            omis = len(groupes) - PILE_MAX_AFFICHEE
            groupes = groupes[: PILE_MAX_AFFICHEE - 2] + [None] + groupes[-2:]
        for groupe in groupes:
            if groupe is None:
                lignes.append(f"  ... ({omis} autres appels) ...")
                continue
            (nom, ligne), fois = groupe
            repetition = f" (× {fois})" if fois > 1 else ""
            lignes.append(f"  dans « {nom} », appelée ligne {ligne}{repetition}")

    return "\n".join(lignes)
