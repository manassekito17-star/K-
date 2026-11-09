"""Interpréteur : exécute l'arbre syntaxique (AST) instruction par instruction."""

import sys

from . import ast, natives, operations
from .environnement import Environnement
from .pile import avec_grande_pile
from .erreurs import (
    ErreurExecution, ErreurNom, ErreurRecursion, ErreurType, ErreurUtilisateur,
    ErreurValeur, Interruption, SignalArret, SignalContinuer, SignalRetour,
)
from .valeurs import (
    FonctionNative, FonctionUtilisateur, decrire_type, representer,
)

PROFONDEUR_MAX = 1000          # appels de fonctions imbriqués (spécification §6.10)


def _pluriel(n, mot):
    return f"{n} {mot}{'s' if n > 1 else ''}"


class Interpreteur:
    def __init__(self, sortie=None, entree=None):
        self.sortie = sortie if sortie is not None else sys.stdout
        self._entree = entree if entree is not None else sys.stdin
        # Noms protégés : fonctions natives, plus celles des bibliothèques
        # activées par « utiliser » (ensemble partagé par tous les environnements).
        self.noms_natifs = set(natives.NOMS_NATIFS)
        self.globales = Environnement(natives=self.noms_natifs)
        natives.installer(self.globales)
        self.page = None             # modèle de la page web (« utiliser web »)
        self.noeud_appel = None      # appel de fonction native en cours
        self.profondeur = 0
        self.interrompu = False      # mis à vrai par Ctrl+C
        # Les entiers K+ sont de précision illimitée : on lève la limite
        # d'affichage des grands entiers ajoutée dans Python 3.11.
        if hasattr(sys, "set_int_max_str_digits"):
            sys.set_int_max_str_digits(0)

    # --- entrée -------------------------------------------------------------

    def lire_ligne(self, invite: str) -> str:
        self.sortie.write(invite)
        self.sortie.flush()
        ligne = self._entree.readline()
        if ligne == "":
            raise EOFError
        if ligne.endswith("\n"):
            ligne = ligne[:-1]
        if ligne.endswith("\r"):
            ligne = ligne[:-1]
        return ligne

    # --- points d'entrée ------------------------------------------------------

    def executer_programme(self, programme: ast.Programme):
        """Exécute un programme dans l'environnement global.
        Renvoie la valeur de la dernière instruction-expression (mode interactif)."""
        def tout():
            resultat = None
            for instruction in programme.instructions:
                resultat = self.executer(instruction, self.globales)
            return resultat
        return avec_grande_pile(tout, self)

    def executer(self, noeud, env):
        if self.interrompu:
            raise Interruption()
        try:
            return INSTRUCTIONS[type(noeud)](self, noeud, env)
        except ErreurExecution as e:
            e.placer(noeud.ligne, noeud.colonne)
            raise

    def evaluer(self, noeud, env):
        try:
            return EXPRESSIONS[type(noeud)](self, noeud, env)
        except ErreurExecution as e:
            e.placer(noeud.ligne, noeud.colonne)
            raise

    def executer_bloc(self, instructions, env):
        nouvel = Environnement(env)
        for instruction in instructions:
            self.executer(instruction, nouvel)

    def exiger_booleen(self, noeud, env, contexte):
        valeur = self.evaluer(noeud, env)
        if type(valeur) is not bool:
            raise ErreurType(
                f"{contexte} doit valoir vrai ou faux, mais c'est "
                f"{decrire_type(valeur)} ({representer(valeur, True)})",
                noeud.ligne, noeud.colonne,
                "écrivez une comparaison, par exemple : x > 0")
        return valeur

    def exiger_entier(self, noeud, env, contexte):
        valeur = self.evaluer(noeud, env)
        if type(valeur) is not int:
            raise ErreurType(
                f"{contexte} doit être un entier, pas {decrire_type(valeur)}",
                noeud.ligne, noeud.colonne)
        return valeur

    # --- instructions -----------------------------------------------------------

    def _declaration(self, n: ast.Declaration, env):
        env.declarer(n.nom, self.evaluer(n.valeur, env), n.constante)

    def _affectation(self, n: ast.Affectation, env):
        cible = n.cible
        if isinstance(cible, ast.Nom):
            env.affecter(cible.nom, self.evaluer(n.valeur, env))
            return
        objet = self.evaluer(cible.objet, env)
        indice = self.evaluer(cible.indice, env)
        valeur = self.evaluer(n.valeur, env)
        try:
            operations.ecrire_indice(objet, indice, valeur)
        except ErreurExecution as e:
            e.placer(cible.ligne, cible.colonne)
            raise

    def _instruction_expression(self, n: ast.InstructionExpression, env):
        return self.evaluer(n.expression, env)

    def _si(self, n: ast.Si, env):
        for condition, corps in n.branches:
            if self.exiger_booleen(condition, env, "la condition du « si »"):
                self.executer_bloc(corps, env)
                return
        if n.sinon is not None:
            self.executer_bloc(n.sinon, env)

    def _tant_que(self, n: ast.TantQue, env):
        while self.exiger_booleen(n.condition, env, "la condition du « tant que »"):
            if self.interrompu:
                raise Interruption()
            try:
                self.executer_bloc(n.corps, env)
            except SignalArret:
                break
            except SignalContinuer:
                continue

    def _pour(self, n: ast.Pour, env):
        debut = self.exiger_entier(n.debut, env, "la valeur de départ du « pour »")
        fin = self.exiger_entier(n.fin, env, "la valeur de fin du « pour »")
        pas = 1
        if n.pas is not None:
            pas = self.exiger_entier(n.pas, env, "le pas du « pour »")
            if pas == 0:
                raise ErreurValeur("le pas d'une boucle « pour » ne peut pas être 0",
                                   n.pas.ligne, n.pas.colonne)
        i = debut
        while (i <= fin) if pas > 0 else (i >= fin):
            if self.interrompu:
                raise Interruption()
            tour = Environnement(env)
            tour.declarer(n.variable, i)
            try:
                for instruction in n.corps:
                    self.executer(instruction, tour)
            except SignalArret:
                break
            except SignalContinuer:
                pass
            i += pas

    def _pour_chaque(self, n: ast.PourChaque, env):
        collection = self.evaluer(n.iterable, env)
        if type(collection) not in (list, str):
            raise ErreurType(
                f"« pour chaque » parcourt une liste ou un texte, pas "
                f"{decrire_type(collection)}", n.iterable.ligne, n.iterable.colonne)
        for element in list(collection):      # copie : voir spécification §6.8
            if self.interrompu:
                raise Interruption()
            tour = Environnement(env)
            tour.declarer(n.variable, element)
            try:
                for instruction in n.corps:
                    self.executer(instruction, tour)
            except SignalArret:
                break
            except SignalContinuer:
                pass

    def _definition_fonction(self, n: ast.DefinitionFonction, env):
        for parametre in n.parametres:
            if parametre in env.natives:
                raise ErreurNom(
                    f"le paramètre « {parametre} » porte le nom d'une fonction "
                    f"native de K+", conseil="choisissez un autre nom")
        env.declarer(n.nom, FonctionUtilisateur(n.nom, n.parametres, n.corps, env))

    def _retourner(self, n: ast.Retourner, env):
        valeur = None if n.valeur is None else self.evaluer(n.valeur, env)
        raise SignalRetour(valeur)

    def _arreter(self, n, env):
        raise SignalArret()

    def _continuer(self, n, env):
        raise SignalContinuer()

    def _essayer(self, n: ast.Essayer, env):
        try:
            self.executer_bloc(n.corps, env)
        except ErreurExecution as erreur:
            gestion = Environnement(env)
            if n.nom_erreur is not None:
                gestion.declarer(n.nom_erreur, erreur.message)
            for instruction in n.gestionnaire:
                self.executer(instruction, gestion)

    def _utiliser(self, n: ast.Utiliser, env):
        if n.bibliotheque != "web":
            raise ErreurNom(f"bibliothèque « {n.bibliotheque} » inconnue",
                            n.ligne, n.colonne, "bibliothèque disponible : web")
        if self.page is not None:
            return                                   # déjà activée
        from . import web
        for nom in web.NOMS_WEB:
            if nom in self.globales.valeurs:
                raise ErreurNom(
                    f"« {nom} » est déjà utilisé dans ce programme, mais c'est aussi "
                    f"une fonction de la bibliothèque web", n.ligne, n.colonne,
                    f"renommez « {nom} », ou placez « utiliser web » au tout début du programme")
        self.page = web.Page()
        for nom, fonction in web.fonctions_natives().items():
            self.globales.definir_native(nom, fonction)
            self.noms_natifs.add(nom)

    def appeler_action(self, fonction, arguments, noeud):
        """Appelle une action web (clic, saisie, minuterie) avec une grande pile."""
        return avec_grande_pile(lambda: self.appeler(fonction, arguments, noeud), self)

    def _lever(self, n: ast.Lever, env):
        message = self.evaluer(n.valeur, env)
        if type(message) is not str:
            raise ErreurType(f"« lever » attend un texte, pas {decrire_type(message)}",
                             n.valeur.ligne, n.valeur.colonne,
                             'exemple : lever "message d\'erreur"')
        raise ErreurUtilisateur(message, n.ligne, n.colonne)

    # --- expressions --------------------------------------------------------------

    def _litteral(self, n: ast.Litteral, env):
        return n.valeur

    def _nom(self, n: ast.Nom, env):
        return env.lire(n.nom)

    def _liste(self, n: ast.ListeLitterale, env):
        return [self.evaluer(e, env) for e in n.elements]

    def _unaire(self, n: ast.OperationUnaire, env):
        if n.operateur == "non":
            return not self.exiger_booleen(n.operande, env, "la valeur après « non »")
        return operations.unaire(n.operateur, self.evaluer(n.operande, env))

    def _binaire(self, n: ast.OperationBinaire, env):
        gauche = self.evaluer(n.gauche, env)
        droite = self.evaluer(n.droite, env)
        return operations.binaire(n.operateur, gauche, droite)

    def _logique(self, n: ast.OperationLogique, env):
        contexte = f"chaque côté de « {n.operateur} »"
        gauche = self.exiger_booleen(n.gauche, env, contexte)
        if n.operateur == "et" and not gauche:
            return False
        if n.operateur == "ou" and gauche:
            return True
        return self.exiger_booleen(n.droite, env, contexte)

    def _acces_indice(self, n: ast.AccesIndice, env):
        objet = self.evaluer(n.objet, env)
        indice = self.evaluer(n.indice, env)
        return operations.lire_indice(objet, indice)

    def _appel(self, n: ast.Appel, env):
        fonction = self.evaluer(n.fonction, env)
        arguments = [self.evaluer(a, env) for a in n.arguments]
        return self.appeler(fonction, arguments, n)

    def appeler(self, fonction, arguments, noeud):
        nombre = len(arguments)
        if type(fonction) is FonctionNative:
            mini, maxi = fonction.arite_min, fonction.arite_max
            if nombre < mini or (maxi is not None and nombre > maxi):
                if maxi is None:
                    attendu = f"au moins {_pluriel(mini, 'argument')}"
                elif mini == maxi:
                    attendu = _pluriel(mini, "argument")
                else:
                    attendu = f"entre {mini} et {maxi} arguments"
                raise ErreurType(
                    f"la fonction « {fonction.nom} » attend {attendu}, "
                    f"mais en a reçu {nombre}")
            self.noeud_appel = noeud
            return fonction.implementation(self, arguments)

        if type(fonction) is not FonctionUtilisateur:
            raise ErreurType(
                f"impossible d'appeler {decrire_type(fonction)} : ce n'est pas "
                f"une fonction")

        attendus = len(fonction.parametres)
        if nombre != attendus:
            raise ErreurType(
                f"la fonction « {fonction.nom} » attend "
                f"{_pluriel(attendus, 'argument')}, mais en a reçu {nombre}")
        if self.profondeur >= PROFONDEUR_MAX:
            raise ErreurRecursion(
                f"plus de {PROFONDEUR_MAX} appels de fonctions imbriqués",
                conseil="vérifiez que la fonction récursive a une condition d'arrêt")

        env = Environnement(fonction.fermeture)
        for parametre, argument in zip(fonction.parametres, arguments):
            env.declarer(parametre, argument)
        self.profondeur += 1
        try:
            for instruction in fonction.corps:
                self.executer(instruction, env)
        except SignalRetour as retour:
            return retour.valeur
        except ErreurExecution as erreur:
            erreur.pile.append((fonction.nom, noeud.ligne))
            raise
        finally:
            self.profondeur -= 1
        return None


INSTRUCTIONS = {
    ast.Declaration: Interpreteur._declaration,
    ast.Affectation: Interpreteur._affectation,
    ast.InstructionExpression: Interpreteur._instruction_expression,
    ast.Si: Interpreteur._si,
    ast.TantQue: Interpreteur._tant_que,
    ast.Pour: Interpreteur._pour,
    ast.PourChaque: Interpreteur._pour_chaque,
    ast.DefinitionFonction: Interpreteur._definition_fonction,
    ast.Retourner: Interpreteur._retourner,
    ast.Arreter: Interpreteur._arreter,
    ast.Continuer: Interpreteur._continuer,
    ast.Essayer: Interpreteur._essayer,
    ast.Lever: Interpreteur._lever,
    ast.Utiliser: Interpreteur._utiliser,
}

EXPRESSIONS = {
    ast.Litteral: Interpreteur._litteral,
    ast.Nom: Interpreteur._nom,
    ast.ListeLitterale: Interpreteur._liste,
    ast.OperationUnaire: Interpreteur._unaire,
    ast.OperationBinaire: Interpreteur._binaire,
    ast.OperationLogique: Interpreteur._logique,
    ast.AccesIndice: Interpreteur._acces_indice,
    ast.Appel: Interpreteur._appel,
}
