# -*- coding: utf-8 -*-
"""Briques de base, réutilisées par tous les mouvements (le robot est un objet mecademicpy,
ou un faux robot pour la simulation RoboDK et les tests)."""
import time

from .poses import pose
from .reglages import (DUREE_PHOTO, DUREE_PINCE, H_ATTENTE, H_CUBE, LEVEE, SOCLE, TCP, VITESSE_ANGULAIRE,
                       VITESSE_ARTICULAIRE, VITESSE_LINEAIRE)


def preparer(robot):
    """Réglages de l'outil et des vitesses, pince ouverte, position d'attente."""
    robot.SetTrf(*TCP)                   # TCP = centre des patins des doigts
    robot.SetBlending(0)                 # passer exactement par chaque point (on est près du cube)
    robot.SetCartLinVel(VITESSE_LINEAIRE)
    robot.SetCartAngVel(VITESSE_ANGULAIRE)
    robot.SetJointVel(VITESSE_ARTICULAIRE)
    robot.GripperOpen()
    position_attente(robot)
    robot.WaitIdle(60)


def position_attente(robot, lieu=SOCLE):
    """Pince verticale au-dessus du cube (posé dans le socle, ou sur la table : lieu=TABLE)."""
    robot.MovePose(*pose(H_ATTENTE, lieu=lieu))


def ouvrir_pince(robot):
    robot.GripperOpen()
    robot.Delay(DUREE_PINCE)


def fermer_pince(robot):
    robot.GripperClose()
    robot.Delay(DUREE_PINCE)


def aller(robot, hauteur, inclinaison=0.0, rotation=0.0, recul=0.0, lieu=SOCLE):
    """Déplacement en ligne droite de la pince (voir pose())."""
    robot.MoveLin(*pose(hauteur, inclinaison, rotation, recul, lieu))


def saisir(robot, hauteur, lieu=SOCLE):
    """Depuis la position d'attente : ouvre, descend à la hauteur voulue, ferme."""
    position_attente(robot, lieu)
    ouvrir_pince(robot)
    aller(robot, hauteur, lieu=lieu)
    fermer_pince(robot)


def lacher_et_remonter(robot, rotation=0.0, lieu=SOCLE):
    """Ouvre, remonte à la verticale, revient en position d'attente."""
    ouvrir_pince(robot)
    aller(robot, H_ATTENTE, rotation=rotation, lieu=lieu)
    position_attente(robot, lieu)
    robot.WaitIdle(120)


def transferer(robot, depart, arrivee):
    """Prend le cube posé en `depart` et le pose en `arrivee` (SOCLE ou TABLE), sans le tourner.

    Le trajet se fait en ligne droite, cube soulevé de LEVEE mm au-dessus du plus haut des deux.
    """
    z_trajet = max(depart[2], arrivee[2]) + H_CUBE + LEVEE      # hauteur absolue du TCP pendant le trajet
    saisir(robot, H_CUBE, depart)
    aller(robot, z_trajet - depart[2], lieu=depart)              # monte
    aller(robot, z_trajet - arrivee[2], lieu=arrivee)            # se déplace au-dessus de l'arrivée
    aller(robot, H_CUBE, lieu=arrivee)                           # pose
    lacher_et_remonter(robot, lieu=arrivee)


def photographier(robot, face):
    """Attend que le robot soit immobile, puis photographie la face tournée vers la caméra.

    face : nom de la face AVANT la séquence (dessus, dessous, avant, arriere, gauche, droite).
    Simulation RoboDK : le faux robot a une méthode prendre_photo (caméra simulée).
    Vrai robot : c'est ici qu'il faudra déclencher ta caméra ; pour l'instant, une pause.
    """
    robot.WaitIdle(60)
    prendre_photo = getattr(robot, "prendre_photo", None)
    if prendre_photo is not None:
        prendre_photo(face)
    else:
        print("Photo de la face « %s »" % face)
        time.sleep(DUREE_PHOTO)
