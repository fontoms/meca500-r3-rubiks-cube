# -*- coding: utf-8 -*-
"""Connexion au vrai Meca500 (mecademicpy) et menu."""
from .briques import preparer
from .mouvements import MOUVEMENTS
from .reglages import ADRESSE_IP


def connecter(adresse_ip=ADRESSE_IP):
    """Connecte, active et règle le robot, puis le place en position d'attente."""
    import mecademicpy.robot as mdr
    robot = mdr.Robot()
    robot.Connect(address=adresse_ip)
    robot.ActivateAndHome()
    robot.WaitHomed()
    preparer(robot)
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


def menu(robot):
    while True:
        print()
        for i, mouvement in enumerate(MOUVEMENTS, 1):
            print("%d - %-22s %s" % (i, mouvement.__name__, mouvement.__doc__.splitlines()[0]))
        choix = input("Numéro du mouvement (Entrée pour quitter) : ").strip()
        if not choix:
            return
        if not choix.isdigit() or not 1 <= int(choix) <= len(MOUVEMENTS):
            print("Choix invalide : tape un numéro entre 1 et %d." % len(MOUVEMENTS))
            continue
        mouvement = MOUVEMENTS[int(choix) - 1]
        print("->", mouvement.__name__)
        mouvement(robot)
