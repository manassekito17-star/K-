"""Gestionnaire des variables : portées (environnements) imbriquées.

Chaque bloc crée un environnement dont le « parent » est l'environnement
englobant. Pour trouver un nom, on cherche dans l'environnement courant,
puis dans son parent, etc., jusqu'à l'environnement global.
"""

import difflib

from .erreurs import ErreurConstante, ErreurNom


class Environnement:
    __slots__ = ("valeurs", "constantes", "parent", "natives")

    def __init__(self, parent=None, natives=None):
        self.valeurs = {}
        self.constantes = set()
        self.parent = parent
        if natives is not None:
            self.natives = natives
        else:
            self.natives = parent.natives if parent is not None else frozenset()

    def declarer(self, nom, valeur, constante=False):
        if nom in self.natives:
            raise ErreurNom(
                f"« {nom} » est une fonction native de K+ et ne peut pas être "
                f"redéfini", conseil="choisissez un autre nom")
        if nom in self.valeurs:
            raise ErreurNom(
                f"« {nom} » est déjà déclaré dans ce bloc",
                conseil=f"pour changer sa valeur, écrivez simplement : {nom} = ...")
        self.valeurs[nom] = valeur
        if constante:
            self.constantes.add(nom)

    def definir_native(self, nom, valeur):
        self.valeurs[nom] = valeur

    def lire(self, nom):
        env = self
        while env is not None:
            valeurs = env.valeurs
            if nom in valeurs:
                return valeurs[nom]
            env = env.parent
        raise ErreurNom(f"le nom « {nom} » n'est pas défini",
                        conseil=self._conseil_nom_inconnu(nom))

    def affecter(self, nom, valeur):
        env = self
        while env is not None:
            if nom in env.valeurs:
                if env.parent is None and nom in self.natives:
                    raise ErreurNom(
                        f"« {nom} » est une fonction native de K+ et ne peut "
                        f"pas être modifié")
                if nom in env.constantes:
                    raise ErreurConstante(
                        f"« {nom} » est une constante : sa valeur ne peut pas "
                        f"être modifiée",
                        conseil="si la valeur doit changer, déclarez-la avec "
                                "« variable » au lieu de « constante »")
                env.valeurs[nom] = valeur
                return
            env = env.parent
        raise ErreurNom(
            f"« {nom} » n'est pas déclaré",
            conseil=f"déclarez-le d'abord : variable {nom} = ...")

    def noms_visibles(self):
        noms = set()
        env = self
        while env is not None:
            noms.update(env.valeurs)
            env = env.parent
        return noms

    def _conseil_nom_inconnu(self, nom):
        proches = difflib.get_close_matches(nom, self.noms_visibles(), n=1,
                                            cutoff=0.75)
        if proches:
            return f"vouliez-vous dire « {proches[0]} » ?"
        return (f"déclarez-le avant de l'utiliser : variable {nom} = ... "
                f"(une fonction doit être déclarée avant d'être appelée)")
