"""K+ : langage de programmation en français.

Utilisation depuis Python :

    import kplus
    kplus.executer('afficher("Bonjour")')
"""

from .ast import Programme
from .erreurs import ErreurKPlus, formater_erreur
from .interpreteur import Interpreteur
from .lexer import analyser_lexique
from .parser import analyser_syntaxe
from .pile import avec_grande_pile
from .verificateur import verifier

__version__ = "0.3.0"
VERSION_LANGAGE = "0.3"


def analyser(source: str, interactif: bool = False) -> Programme:
    """Analyse complète d'un programme (lexique, syntaxe, vérifications).
    Lève une ErreurLexicale ou une ErreurSyntaxe en cas de problème.
    Aucune instruction n'est exécutée."""
    def tout():
        programme = analyser_syntaxe(analyser_lexique(source))
        verifier(programme, interactif)
        return programme
    return avec_grande_pile(tout)


def executer(source: str, sortie=None, entree=None):
    """Analyse puis exécute un programme K+."""
    programme = analyser(source)
    return Interpreteur(sortie, entree).executer_programme(programme)


__all__ = [
    "analyser", "executer", "Interpreteur", "ErreurKPlus", "formater_erreur",
    "__version__",
]
