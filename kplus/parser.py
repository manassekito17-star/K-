"""Analyse syntaxique : transforme la liste de jetons en arbre (AST).

Technique : « descente récursive ». Chaque règle de la grammaire
(docs/specification/grammaire.ebnf) correspond à une méthode de cette classe.
"""

from . import ast
from .erreurs import ErreurSyntaxe
from .jetons import (
    DECIMAL, ENTIER, FIN_FICHIER, IDENT, MOTCLE, NL, OPERATEURS_COMPARAISON,
    SYMBOLE, TEXTE, Jeton,
)


class Parser:
    def __init__(self, jetons: list[Jeton]):
        self.jetons = jetons
        self.i = 0

    # --- outils -------------------------------------------------------------

    @property
    def courant(self) -> Jeton:
        return self.jetons[self.i]

    def avancer(self) -> Jeton:
        jeton = self.jetons[self.i]
        if jeton.type != FIN_FICHIER:
            self.i += 1
        return jeton

    def est_motcle(self, *mots) -> bool:
        return self.courant.type == MOTCLE and self.courant.valeur in mots

    def est_symbole(self, *symboles) -> bool:
        return self.courant.type == SYMBOLE and self.courant.valeur in symboles

    def est_fin_ligne(self) -> bool:
        return self.courant.type in (NL, FIN_FICHIER)

    def erreur(self, message, jeton=None, conseil=None, incomplet=None):
        jeton = jeton or self.courant
        if incomplet is None:
            incomplet = jeton.type == FIN_FICHIER
        return ErreurSyntaxe(message, jeton.ligne, jeton.colonne, conseil,
                             incomplet)

    def sauter_fins_ligne(self):
        while self.courant.type == NL:
            self.avancer()

    def attendre_motcle(self, mot, message, conseil=None) -> Jeton:
        if not self.est_motcle(mot):
            if self.est_symbole("=") and mot in ("alors", "faire"):
                conseil = ("« = » sert à donner une valeur ; "
                           "pour comparer, écrivez ==")
            raise self.erreur(
                f"{message}, mais {self.courant.decrire()} a été trouvé",
                conseil=conseil)
        return self.avancer()

    def attendre_symbole(self, symbole, message, ouvrant=None) -> Jeton:
        if not self.est_symbole(symbole):
            if self.courant.type == FIN_FICHIER and ouvrant is not None:
                raise self.erreur(
                    f"« {ouvrant.valeur} » ouvert ici n'est jamais fermé par "
                    f"« {symbole} »", jeton=ouvrant, incomplet=True)
            raise self.erreur(
                f"{message}, mais {self.courant.decrire()} a été trouvé")
        return self.avancer()

    def attendre_fin_ligne_apres(self, mot):
        """Après « alors », « faire », etc., le bloc commence à la ligne suivante."""
        if self.courant.type == NL:
            self.avancer()
            return
        if self.courant.type == FIN_FICHIER:
            raise self.erreur(f"bloc attendu après « {mot} »", incomplet=True)
        raise self.erreur(
            f"fin de ligne attendue après « {mot} », mais "
            f"{self.courant.decrire()} a été trouvé",
            conseil="le contenu du bloc commence à la ligne suivante")

    def fin_instruction(self):
        if self.courant.type == NL:
            self.avancer()
        elif self.courant.type != FIN_FICHIER:
            raise self.erreur(
                f"fin de ligne attendue après l'instruction, mais "
                f"{self.courant.decrire()} a été trouvé",
                conseil="écrivez une seule instruction par ligne")

    def nom_declare(self, role) -> Jeton:
        jeton = self.courant
        if jeton.type == IDENT:
            return self.avancer()
        if jeton.type == MOTCLE:
            raise self.erreur(
                f"« {jeton.valeur} » est un mot réservé de K+ et ne peut pas "
                f"servir de {role}", conseil="choisissez un autre nom")
        raise self.erreur(f"{role} attendu, mais {jeton.decrire()} a été trouvé")

    # --- programme et blocs -----------------------------------------------------

    def programme(self) -> ast.Programme:
        instructions = []
        self.sauter_fins_ligne()
        while self.courant.type != FIN_FICHIER:
            instructions.append(self.instruction())
            self.fin_instruction()
            self.sauter_fins_ligne()
        return ast.Programme(1, 1, instructions)

    def bloc(self, fermants, ouvrant: Jeton, nom_bloc: str) -> list:
        """Lit des instructions jusqu'à l'un des mots-clés « fermants »."""
        instructions = []
        self.sauter_fins_ligne()
        while not self.est_motcle(*fermants):
            if self.courant.type == FIN_FICHIER:
                raise ErreurSyntaxe(
                    f"le bloc « {nom_bloc} » ouvert ici n'est jamais fermé "
                    f"par « fin »", ouvrant.ligne, ouvrant.colonne,
                    incomplet=True)
            instructions.append(self.instruction())
            self.fin_instruction()
            self.sauter_fins_ligne()
        return instructions

    # --- instructions -------------------------------------------------------------

    def instruction(self):
        jeton = self.courant
        if jeton.type == MOTCLE:
            mot = jeton.valeur
            if mot in ("variable", "constante"):
                return self.declaration()
            if mot == "si":
                return self.si()
            if mot == "tant":
                return self.tant_que()
            if mot == "pour":
                return self.pour()
            if mot == "fonction":
                return self.fonction()
            if mot == "essayer":
                return self.essayer()
            if mot == "retourner":
                self.avancer()
                valeur = None if self.est_fin_ligne() else self.expression()
                return ast.Retourner(jeton.ligne, jeton.colonne, valeur)
            if mot == "arreter":
                self.avancer()
                return ast.Arreter(jeton.ligne, jeton.colonne)
            if mot == "continuer":
                self.avancer()
                return ast.Continuer(jeton.ligne, jeton.colonne)
            if mot == "utiliser":
                self.avancer()
                nom = self.nom_declare("nom de bibliothèque")
                return ast.Utiliser(jeton.ligne, jeton.colonne, nom.valeur)
            if mot == "lever":
                self.avancer()
                return ast.Lever(jeton.ligne, jeton.colonne, self.expression())
            if mot == "fin":
                raise self.erreur("« fin » inattendu : aucun bloc n'est ouvert ici")
            if mot == "sinon":
                raise self.erreur(
                    "« sinon » inattendu : il doit suivre le bloc d'un « si »")
            if mot == "attraper":
                raise self.erreur(
                    "« attraper » inattendu : il doit suivre un bloc « essayer »")

        debut = self.courant
        expression = self.expression()
        if self.est_symbole("="):
            egal = self.avancer()
            if not self.est_cible(expression):
                raise self.erreur(
                    "on ne peut donner une valeur qu'à une variable ou à un "
                    "élément de liste", jeton=egal,
                    conseil="pour comparer deux valeurs, écrivez ==")
            valeur = self.expression()
            return ast.Affectation(debut.ligne, debut.colonne, expression,
                                   valeur)
        return ast.InstructionExpression(debut.ligne, debut.colonne, expression)

    def est_cible(self, noeud) -> bool:
        if isinstance(noeud, ast.Nom):
            return True
        if isinstance(noeud, ast.AccesIndice):
            return self.est_cible(noeud.objet)
        return False

    def declaration(self):
        mot = self.avancer()
        constante = mot.valeur == "constante"
        role = "nom de constante" if constante else "nom de variable"
        nom = self.nom_declare(role)
        if not self.est_symbole("="):
            raise self.erreur(
                f"« = » attendu après « {nom.valeur} » : une {mot.valeur} "
                f"doit recevoir une valeur",
                conseil=f"exemple : {mot.valeur} {nom.valeur} = nul")
        self.avancer()
        valeur = self.expression()
        return ast.Declaration(mot.ligne, mot.colonne, nom.valeur, valeur,
                               constante)

    def si(self):
        jeton_si = self.avancer()
        branches = []
        condition = self.expression()
        self.attendre_motcle("alors", "« alors » attendu après la condition")
        self.attendre_fin_ligne_apres("alors")
        corps = self.bloc(("fin", "sinon"), jeton_si, "si")
        branches.append((condition, corps))
        sinon = None
        while self.est_motcle("sinon"):
            jeton_sinon = self.avancer()
            if self.est_motcle("si"):
                self.avancer()
                condition = self.expression()
                self.attendre_motcle("alors", "« alors » attendu après la condition")
                self.attendre_fin_ligne_apres("alors")
                corps = self.bloc(("fin", "sinon"), jeton_si, "si")
                branches.append((condition, corps))
            else:
                self.attendre_fin_ligne_apres("sinon")
                sinon = self.bloc(("fin", "sinon"), jeton_si, "si")
                if self.est_motcle("sinon"):
                    raise self.erreur(
                        "un seul « sinon » est permis, et il doit être le dernier",
                        conseil="pour une autre condition, écrivez « sinon si ... alors » "
                                "avant le « sinon » final")
                break
        self.avancer()  # fin
        return ast.Si(jeton_si.ligne, jeton_si.colonne, branches, sinon)

    def tant_que(self):
        jeton = self.avancer()
        self.attendre_motcle("que", "« que » attendu après « tant »",
                             conseil="écrivez : tant que condition faire")
        condition = self.expression()
        self.attendre_motcle("faire", "« faire » attendu après la condition")
        self.attendre_fin_ligne_apres("faire")
        corps = self.bloc(("fin",), jeton, "tant que")
        self.avancer()
        return ast.TantQue(jeton.ligne, jeton.colonne, condition, corps)

    def pour(self):
        jeton = self.avancer()
        if self.est_motcle("chaque"):
            self.avancer()
            variable = self.nom_declare("nom de variable")
            self.attendre_motcle("dans", "« dans » attendu après le nom de la variable",
                                 conseil="écrivez : pour chaque x dans liste faire")
            iterable = self.expression()
            self.attendre_motcle("faire", "« faire » attendu")
            self.attendre_fin_ligne_apres("faire")
            corps = self.bloc(("fin",), jeton, "pour chaque")
            self.avancer()
            return ast.PourChaque(jeton.ligne, jeton.colonne, variable.valeur,
                                  iterable, corps)

        variable = self.nom_declare("nom de variable")
        self.attendre_motcle("de", "« de » attendu après le nom de la variable",
                             conseil="écrivez : pour i de 1 à 10 faire")
        debut = self.expression()
        conseil = None
        if self.courant.type == IDENT and self.courant.valeur in ("a", "A"):
            conseil = "écrivez « à » avec un accent : pour i de 1 à 10 faire"
        self.attendre_motcle("à", "« à » attendu après la valeur de départ",
                             conseil=conseil)
        fin = self.expression()
        pas = None
        if self.est_motcle("pas"):
            self.avancer()
            pas = self.expression()
        self.attendre_motcle("faire", "« faire » attendu")
        self.attendre_fin_ligne_apres("faire")
        corps = self.bloc(("fin",), jeton, "pour")
        self.avancer()
        return ast.Pour(jeton.ligne, jeton.colonne, variable.valeur, debut,
                        fin, pas, corps)

    def fonction(self):
        jeton = self.avancer()
        nom = self.nom_declare("nom de fonction")
        ouvrant = self.attendre_symbole(
            "(", f"« ( » attendu après le nom de la fonction « {nom.valeur} »")
        parametres = []
        if not self.est_symbole(")"):
            while True:
                parametre = self.nom_declare("nom de paramètre")
                if parametre.valeur in parametres:
                    raise self.erreur(
                        f"le paramètre « {parametre.valeur} » apparaît deux fois",
                        jeton=parametre)
                parametres.append(parametre.valeur)
                if not self.est_symbole(","):
                    break
                self.avancer()
        self.attendre_symbole(")", "« ) » ou « , » attendu dans la liste des "
                              "paramètres", ouvrant)
        self.attendre_fin_ligne_apres(")")
        corps = self.bloc(("fin",), jeton, "fonction")
        self.avancer()
        return ast.DefinitionFonction(jeton.ligne, jeton.colonne, nom.valeur,
                                      parametres, corps)

    def essayer(self):
        jeton = self.avancer()
        self.attendre_fin_ligne_apres("essayer")
        corps = self.bloc(("attraper", "fin"), jeton, "essayer")
        if self.est_motcle("fin"):
            raise self.erreur(
                "« attraper » attendu avant « fin » : un bloc « essayer » "
                "doit avoir une partie « attraper »")
        self.avancer()  # attraper
        nom_erreur = None
        if not self.est_fin_ligne():
            nom_erreur = self.nom_declare("nom de variable").valeur
        self.attendre_fin_ligne_apres("attraper")
        gestionnaire = self.bloc(("fin",), jeton, "essayer")
        self.avancer()
        return ast.Essayer(jeton.ligne, jeton.colonne, corps, nom_erreur,
                           gestionnaire)

    # --- expressions --------------------------------------------------------------

    def expression(self):
        return self.ou()

    def ou(self):
        gauche = self.et()
        while self.est_motcle("ou"):
            op = self.avancer()
            gauche = ast.OperationLogique(op.ligne, op.colonne, "ou", gauche,
                                          self.et())
        return gauche

    def et(self):
        gauche = self.non()
        while self.est_motcle("et"):
            op = self.avancer()
            gauche = ast.OperationLogique(op.ligne, op.colonne, "et", gauche,
                                          self.non())
        return gauche

    def non(self):
        if self.est_motcle("non"):
            op = self.avancer()
            return ast.OperationUnaire(op.ligne, op.colonne, "non", self.non())
        return self.comparaison()

    def comparaison(self):
        gauche = self.addition()
        if self.est_symbole(*OPERATEURS_COMPARAISON):
            op = self.avancer()
            gauche = ast.OperationBinaire(op.ligne, op.colonne, op.valeur,
                                          gauche, self.addition())
            if self.est_symbole(*OPERATEURS_COMPARAISON):
                raise self.erreur(
                    "les comparaisons ne peuvent pas s'enchaîner",
                    conseil="écrivez par exemple : a < b et b < c")
        return gauche

    def addition(self):
        gauche = self.multiplication()
        while self.est_symbole("+", "-"):
            op = self.avancer()
            gauche = ast.OperationBinaire(op.ligne, op.colonne, op.valeur,
                                          gauche, self.multiplication())
        return gauche

    def multiplication(self):
        gauche = self.unaire()
        while self.est_symbole("*", "/", "%"):
            op = self.avancer()
            gauche = ast.OperationBinaire(op.ligne, op.colonne, op.valeur,
                                          gauche, self.unaire())
        return gauche

    def unaire(self):
        if self.est_symbole("-", "+"):
            op = self.avancer()
            return ast.OperationUnaire(op.ligne, op.colonne, op.valeur,
                                       self.unaire())
        return self.puissance()

    def puissance(self):
        base = self.postfixe()
        if self.est_symbole("^"):
            op = self.avancer()
            # unaire() rappelle puissance() : associativité à droite.
            return ast.OperationBinaire(op.ligne, op.colonne, "^", base,
                                        self.unaire())
        return base

    def postfixe(self):
        expression = self.primaire()
        while True:
            if self.est_symbole("("):
                ouvrant = self.avancer()
                arguments = []
                if not self.est_symbole(")"):
                    arguments.append(self.expression())
                    while self.est_symbole(","):
                        self.avancer()
                        arguments.append(self.expression())
                self.attendre_symbole(
                    ")", "« ) » ou « , » attendu dans les arguments", ouvrant)
                expression = ast.Appel(expression.ligne, expression.colonne,
                                       expression, arguments)
            elif self.est_symbole("["):
                ouvrant = self.avancer()
                indice = self.expression()
                self.attendre_symbole("]", "« ] » attendu après l'indice", ouvrant)
                expression = ast.AccesIndice(ouvrant.ligne, ouvrant.colonne,
                                             expression, indice)
            else:
                return expression

    def primaire(self):
        jeton = self.courant
        if jeton.type in (ENTIER, DECIMAL, TEXTE):
            self.avancer()
            return ast.Litteral(jeton.ligne, jeton.colonne, jeton.valeur)
        if jeton.type == MOTCLE and jeton.valeur in ("vrai", "faux", "nul"):
            self.avancer()
            valeur = {"vrai": True, "faux": False, "nul": None}[jeton.valeur]
            return ast.Litteral(jeton.ligne, jeton.colonne, valeur)
        if jeton.type == IDENT:
            self.avancer()
            return ast.Nom(jeton.ligne, jeton.colonne, jeton.valeur)
        if self.est_symbole("("):
            ouvrant = self.avancer()
            expression = self.expression()
            self.attendre_symbole(")", "« ) » attendu", ouvrant)
            return expression
        if self.est_symbole("["):
            ouvrant = self.avancer()
            elements = []
            while not self.est_symbole("]"):
                elements.append(self.expression())
                if not self.est_symbole(","):
                    break
                self.avancer()
            self.attendre_symbole("]", "« ] » ou « , » attendu dans la liste",
                                  ouvrant)
            return ast.ListeLitterale(ouvrant.ligne, ouvrant.colonne, elements)

        conseil = None
        if jeton.type == MOTCLE:
            conseil = f"« {jeton.valeur} » est un mot réservé de K+"
        raise self.erreur(
            f"expression attendue, mais {jeton.decrire()} a été trouvé",
            conseil=conseil)


def analyser_syntaxe(jetons: list[Jeton]) -> ast.Programme:
    return Parser(jetons).programme()
