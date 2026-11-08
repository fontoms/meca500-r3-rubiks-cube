# -*- coding: utf-8 -*-
"""Connexion au vrai Meca500 (mecademicpy) et menu."""
from .briques import preparer, regler_vitesse
from .mouvements import MOUVEMENTS
from .reglages import ADRESSE_IP, VITESSE_GLOBALE


def connecter(adresse_ip=ADRESSE_IP, facteur_vitesse=None):
    """Connecte, active et règle le robot, puis le place en position d'attente."""
    import mecademicpy.robot as mdr
    robot = mdr.Robot()
    robot.Connect(address=adresse_ip)
    robot.ActivateAndHome()
    robot.WaitHomed()
    preparer(robot, facteur_vitesse)
    return robot


def deconnecter(robot):
    """Attend la fin des mouvements, désactive et déconnecte — même si le robot est en erreur."""
    try:
        robot.WaitIdle(120)
    except Exception as e:                 # robot en erreur, arrêt d'urgence, timeout…
        print("Le robot ne termine pas normalement :", e)
    try:
        robot.DeactivateRobot()
    finally:
        robot.Disconnect()


def demander_facteur_vitesse(facteur_actuel=VITESSE_GLOBALE):
    """Demande un pourcentage des limites du robot ; Entrée conserve le facteur courant."""
    while True:
        saisie = input("Vitesse globale en %% des limites du Meca500 R3 (1 à 100, Entrée = %g%%) : "
                       % (facteur_actuel * 100)).strip()
        if not saisie:
            return facteur_actuel
        try:
            pourcentage = float(saisie)
        except ValueError:
            print("Valeur invalide : saisis un nombre entre 1 et 100.")
            continue
        if not 1 <= pourcentage <= 100:
            print("Vitesse invalide : le pourcentage doit être entre 1 et 100.")
            continue
        return pourcentage / 100


def menu(robot):
    facteur_vitesse = VITESSE_GLOBALE
    while True:
        print()
        for i, mouvement in enumerate(MOUVEMENTS, 1):
            print("%d - %-22s %s" % (i, mouvement.__name__, mouvement.__doc__.splitlines()[0]))
        choix = input("Numéro du mouvement, v pour régler la vitesse (%g%% des limites R3), "
                      "Entrée pour quitter : " % (facteur_vitesse * 100)).strip()
        if not choix:
            return
        if choix.lower() == "v":
            try:
                facteur_vitesse = regler_vitesse(robot, demander_facteur_vitesse(facteur_vitesse))
            except ValueError as e:
                print("Vitesse invalide :", e)
                continue
            print("Vitesse globale réglée à %g%%." % (facteur_vitesse * 100))
            continue
        if not choix.isdigit() or not 1 <= int(choix) <= len(MOUVEMENTS):
            print("Choix invalide : tape un numéro entre 1 et %d." % len(MOUVEMENTS))
            continue
        mouvement = MOUVEMENTS[int(choix) - 1]
        print("->", mouvement.__name__)
        mouvement(robot)
