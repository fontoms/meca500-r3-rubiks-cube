# -*- coding: utf-8 -*-
"""Briques de base, réutilisées par tous les mouvements (le robot est un objet mecademicpy,
ou un faux robot pour la simulation RoboDK et les tests).

`rotation` : rotation de la pince autour de la verticale (voir poses.pose), une des
ROTATIONS_PINCE (-90°, 0°, +90°). Entre deux mouvements de la résolution, la pince reste en position
d'attente avec la rotation où elle a lâché le cube : on ne la tourne que si le mouvement suivant en a besoin.
"""
import time

from .poses import pose
from .reglages import (DUREE_PHOTO, DUREE_PINCE, H_ATTENTE, H_CUBE, LEVEE, SOCLE, TCP, VITESSE_ANGULAIRE,
                       VITESSE_ARTICULAIRE, VITESSE_GLOBALE, VITESSE_LINEAIRE)
from .vision_capture import capturer_face


def regler_vitesse(robot, facteur=None):
    """Applique un facteur commun (0 < facteur <= 1) aux trois vitesses du robot."""
    if facteur is None:
        facteur = VITESSE_GLOBALE
    if (isinstance(facteur, bool) or not isinstance(facteur, (int, float))
            or not 0 < facteur <= 1):
        raise ValueError("Le facteur de vitesse doit être compris entre 0 (exclu) et 1.")

    robot.SetCartLinVel(VITESSE_LINEAIRE * facteur)
    robot.SetCartAngVel(VITESSE_ANGULAIRE * facteur)
    robot.SetJointVel(VITESSE_ARTICULAIRE * facteur)
    robot.SetJointVelLimit(VITESSE_ARTICULAIRE * facteur)
    return facteur


def preparer(robot, facteur_vitesse=None):
    """Réglages de l'outil et des vitesses, pince ouverte, position d'attente."""
    robot.SetTrf(*TCP)                   # TCP = centre des patins des doigts
    robot.SetBlending(0)                 # passer exactement par chaque point (on est près du cube)
    regler_vitesse(robot, facteur_vitesse)
    robot.GripperOpen()
    position_attente(robot)
    robot.WaitIdle(60)


def position_attente(robot, lieu=SOCLE, rotation=0.0):
    """Pince verticale au-dessus du cube (posé dans le socle, ou sur la table : lieu=TABLE)."""
    robot.MovePose(*pose(H_ATTENTE, rotation=rotation, lieu=lieu))


def etapes_de_rotation(depuis, vers):
    """Angles successifs pour tourner de `depuis` à `vers` par pas de 90° au plus (le dernier = vers).

    Un demi-tour en un seul déplacement est ambigu (le robot peut tourner dans un sens ou dans
    l'autre, et enrouler le câble de la pince) : on passe par les multiples de 90° intermédiaires.
    """
    pas = 90.0 if vers > depuis else -90.0
    angles, a = [], depuis
    while abs(vers - a) > 90.0:
        a += pas
        angles.append(a)
    return angles + [vers] if vers != depuis else []


def tourner_pince(robot, vers, depuis=0.0, lieu=SOCLE):
    """Pince ouverte, en position d'attente : tourne de la rotation `depuis` à la rotation `vers`."""
    for a in etapes_de_rotation(depuis, vers):
        position_attente(robot, lieu, a)


def ouvrir_pince(robot):
    robot.GripperOpen()
    robot.Delay(DUREE_PINCE)


def fermer_pince(robot):
    robot.GripperClose()
    robot.Delay(DUREE_PINCE)


def aller(robot, hauteur, inclinaison=0.0, rotation=0.0, recul=0.0, lieu=SOCLE):
    """Déplacement en ligne droite de la pince (voir pose())."""
    robot.MoveLin(*pose(hauteur, inclinaison, rotation, recul, lieu))


def aller_en_tournant(robot, hauteur, depuis, vers, lieu=SOCLE):
    """Pince verticale à `hauteur` : tourne de `depuis` à `vers`, par pas de 90° au plus."""
    for a in etapes_de_rotation(depuis, vers):
        aller(robot, hauteur, rotation=a, lieu=lieu)


def saisir(robot, hauteur, lieu=SOCLE, rotation=0.0):
    """Depuis la position d'attente (pince ouverte, déjà tournée de `rotation`) : descend, ferme.

    La pince est toujours ouverte entre deux mouvements : on renvoie GripperOpen par sécurité, sans
    attendre DUREE_PINCE (elle est déjà ouverte, et sinon elle s'ouvre pendant la descente).
    """
    position_attente(robot, lieu, rotation)
    robot.GripperOpen()
    aller(robot, hauteur, rotation=rotation, lieu=lieu)
    fermer_pince(robot)


def lacher_et_remonter(robot, rotation=0.0, lieu=SOCLE):
    """Ouvre, remonte à la verticale jusqu'à la position d'attente (la pince garde sa rotation)."""
    ouvrir_pince(robot)
    aller(robot, H_ATTENTE, rotation=rotation, lieu=lieu)
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


def photographier(robot, face, camera=None, references=None):
    """Attend que le robot soit immobile, puis photographie la face tournée vers la caméra.

    face : nom de la face AVANT la séquence (dessus, dessous, avant, arriere, gauche, droite).
    camera : flux de frames de l'aperçu ; None pour la simulation RoboDK.
    references : couleurs calibrées de rubicks-resolve, ou None.
    """
    robot.WaitIdle(60)
    prendre_photo = getattr(robot, "prendre_photo", None)
    if callable(prendre_photo):
        prendre_photo(face)
    elif camera is not None:
        time.sleep(DUREE_PHOTO)
        chemin, couleurs = capturer_face(camera, face, references)
        print("Photo enregistrée : %s" % chemin)
        return couleurs
    else:
        print("Photo de la face « %s »" % face)
        time.sleep(DUREE_PHOTO)
