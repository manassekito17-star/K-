"""Vérifications statiques, faites sur l'AST avant l'exécution.

Elles détectent les erreurs de structure qui ne dépendent pas des valeurs :
- « retourner » hors d'une fonction ;
- « arreter » / « continuer » hors d'une boucle ;
- une ligne contenant une expression sans effet (par exemple « x == 5 »).
"""

from . import ast
from .erreurs import ErreurSyntaxe


class Verificateur:
    def __init__(self, interactif: bool = False):
        self.interactif = interactif

    def verifier(self, programme: ast.Programme):
        self.bloc(programme.instructions, dans_fonction=False,
                  dans_boucle=False, global_=True)

    def bloc(self, instructions, dans_fonction, dans_boucle, global_=False):
        for instruction in instructions:
            self.instruction(instruction, dans_fonction, dans_boucle, global_)

    def instruction(self, n, dans_fonction, dans_boucle, global_):
        if isinstance(n, ast.InstructionExpression):
            if not isinstance(n.expression, ast.Appel) and not (
                    self.interactif and global_):
                conseil = "utilisez cette valeur, par exemple : afficher(...)"
                e = n.expression
                if isinstance(e, ast.OperationBinaire) and e.operateur == "==":
                    conseil = "pour donner une valeur, écrivez = (un seul signe égal)"
                raise ErreurSyntaxe("cette expression n'a aucun effet",
                                    n.ligne, n.colonne, conseil)
        elif isinstance(n, ast.Retourner):
            if not dans_fonction:
                raise ErreurSyntaxe(
                    "« retourner » ne peut être utilisé que dans une fonction",
                    n.ligne, n.colonne)
        elif isinstance(n, (ast.Arreter, ast.Continuer)):
            if not dans_boucle:
                mot = "arreter" if isinstance(n, ast.Arreter) else "continuer"
                raise ErreurSyntaxe(
                    f"« {mot} » ne peut être utilisé que dans une boucle",
                    n.ligne, n.colonne)
        elif isinstance(n, ast.Si):
            for _, corps in n.branches:
                self.bloc(corps, dans_fonction, dans_boucle)
            if n.sinon is not None:
                self.bloc(n.sinon, dans_fonction, dans_boucle)
        elif isinstance(n, (ast.TantQue, ast.Pour, ast.PourChaque)):
            self.bloc(n.corps, dans_fonction, True)
        elif isinstance(n, ast.DefinitionFonction):
            # Une fonction ne « voit » pas la boucle qui l'entoure.
            self.bloc(n.corps, True, False)
        elif isinstance(n, ast.Essayer):
            self.bloc(n.corps, dans_fonction, dans_boucle)
            self.bloc(n.gestionnaire, dans_fonction, dans_boucle)


def verifier(programme: ast.Programme, interactif: bool = False):
    Verificateur(interactif).verifier(programme)
