# -*- coding: utf-8 -*-
"""Briques de base, réutilisées par tous les mouvements (le robot est un objet mecademicpy,
ou un faux robot pour la simulation RoboDK et les tests).

`rotation` : rotation de la pince autour de la verticale (voir poses.pose), une des
ROTATIONS_PINCE (-90°, 0°, +90°). Entre deux mouvements de la résolution, la pince garde la rotation
où elle a lâché le cube : on ne la tourne que si le mouvement suivant en a besoin.

Pas de WaitIdle entre les mouvements : les commandes s'enchaînent dans la file du robot, sans arrêt
ni aller-retour avec le PC. Seules les pinces (attendre_pince) et les photos synchronisent le PC.
"""
import time

from .poses import pose
from .reglages import (ACCELERATION_ARTICULAIRE, ACCELERATION_CARTESIENNE, ATTENDRE_FIN_PINCE, DUREE_PHOTO,
                       DUREE_PINCE, H_ATTENTE, H_CUBE, LEVEE, RECUL_BASCULE, ROTATION_BASCULE, SOCLE, TCP,
                       VITESSE_ANGULAIRE, VITESSE_ARTICULAIRE, VITESSE_LINEAIRE, VITESSE_PINCE)

MARGE_DEMI_TOUR = 1.0       # ° : un demi-tour se fait en 179°, puis 1° (voir etapes_de_rotation)


def preparer(robot):
    """Réglages de l'outil, des vitesses et accélérations, pince ouverte, position d'attente."""
    robot.SetTrf(*TCP)                   # TCP = centre des patins des doigts
    robot.SetBlending(0)                 # passer exactement par chaque point (on est près du cube ;
    #                                      et une commande de pince démarre dès le début du lissage)
    robot.SetCartLinVel(VITESSE_LINEAIRE)
    robot.SetCartAngVel(VITESSE_ANGULAIRE)
    robot.SetJointVel(VITESSE_ARTICULAIRE)
    robot.SetCartAcc(ACCELERATION_CARTESIENNE)
    robot.SetJointAcc(ACCELERATION_ARTICULAIRE)
    robot.SetGripperVel(VITESSE_PINCE)
    robot.GripperOpen()
    position_attente(robot)
    robot.WaitIdle(60)


def position_attente(robot, lieu=SOCLE, rotation=0.0):
    """Pince verticale au-dessus du cube (posé dans le socle, ou sur la table : lieu=TABLE)."""
    robot.MovePose(*pose(H_ATTENTE, rotation=rotation, lieu=lieu))


def etapes_de_rotation(depuis, vers):
    """Angles successifs pour tourner de `depuis` à `vers` (le dernier = vers), 180° au plus.

    Le robot tourne toujours par le plus court chemin : un demi-tour pile (180°) est ambigu (il peut
    tourner dans un sens ou dans l'autre, et enrouler le câble de la pince). On tourne donc de 179° (le
    plus court chemin passe par l'angle du milieu, ex. de +90° à -90° par 0°), puis du dernier degré :
    un grand déplacement et un tout petit, au lieu de deux quarts de tour avec un arrêt au milieu.
    """
    if abs(vers - depuis) > 180.0:
        raise ValueError("rotation de plus d'un demi-tour : de %s° à %s°" % (depuis, vers))
    if vers == depuis:
        return []
    if abs(vers - depuis) <= 90.0:
        return [vers]
    pas = 1.0 if vers > depuis else -1.0
    return [vers - pas * MARGE_DEMI_TOUR, vers]


def tourner_pince(robot, vers, depuis=0.0, lieu=SOCLE):
    """Pince ouverte, en position d'attente : tourne de la rotation `depuis` à la rotation `vers`."""
    for a in etapes_de_rotation(depuis, vers):
        position_attente(robot, lieu, a)


def attendre_pince(robot):
    """Le robot reste immobile jusqu'à la fin de l'ouverture / fermeture de la pince.

    Vrai robot (firmware ≥ 9.1, robot.capteur_pince mis à True par robot_reel.connecter) : on attend
    que la pince signale la fin de son mouvement (cube tenu ou fin de course), puis le robot repart
    aussitôt. Sinon : pause fixe de DUREE_PINCE.
    """
    if ATTENDRE_FIN_PINCE and getattr(robot, "capteur_pince", False) is True:
        robot.WaitGripperMoveCompletion(5)
    else:
        robot.Delay(DUREE_PINCE)


def ouvrir_pince(robot):
    robot.GripperOpen()
    attendre_pince(robot)


def fermer_pince(robot):
    robot.GripperClose()
    attendre_pince(robot)


def aller(robot, hauteur, inclinaison=0.0, rotation=0.0, recul=0.0, lieu=SOCLE):
    """Déplacement en ligne droite de la pince (voir pose())."""
    robot.MoveLin(*pose(hauteur, inclinaison, rotation, recul, lieu))


def aller_en_tournant(robot, hauteur, depuis, vers, lieu=SOCLE):
    """Pince verticale à `hauteur` : tourne de `depuis` à `vers`, par pas de 90° au plus."""
    for a in etapes_de_rotation(depuis, vers):
        aller(robot, hauteur, rotation=a, lieu=lieu)


# LIAISONS RAPIDES (résolution) : après avoir lâché le cube, la pince peut rester EN BAS, ouverte autour
# de lui. `depuis` = (hauteur, inclinaison, recul) de la pince à cet endroit (voir poses.pose), ou None si
# elle est en position d'attente. Le mouvement suivant part de là :
#   - pince verticale → autre hauteur de prise : les doigts glissent le long des faces du cube ;
#   - pince tournée de ±90° (mâchoires sur les faces avant / arrière) → penchée (bascule), ou l'inverse :
#     elle penche autour de l'axe X, les doigts restent dans leur plan, le long de ces faces.
# Pour tourner la pince autour de la verticale, il faut d'abord remonter (remonter) : les doigts
# toucheraient les coins du cube.

def verifier_liaison(depuis, rotation, inclinaison=0.0):
    """Lève ValueError si la pince ne peut pas aller de `depuis` (en bas) à une prise penchée de
    `inclinaison` sans remonter : pencher n'est possible que mâchoires sur les faces avant / arrière."""
    if depuis is not None and (depuis[1] or inclinaison) and abs(rotation) != ROTATION_BASCULE:
        raise ValueError("liaison impossible : pince penchée avec une rotation de %s°" % rotation)


def remonter(robot, depuis, rotation=0.0, lieu=SOCLE):
    """Pince ouverte restée en bas autour du cube (depuis, voir LIAISONS) → position d'attente."""
    if depuis is None:
        return
    hauteur, inclinaison, recul = depuis
    if inclinaison:                                   # pince penchée : dégagement le long de son axe
        aller(robot, hauteur, inclinaison, rotation, recul + RECUL_BASCULE, lieu)
    aller(robot, H_ATTENTE, rotation=rotation, lieu=lieu)


def saisir(robot, hauteur, lieu=SOCLE, rotation=0.0, depuis=None):
    """Pince ouverte, déjà tournée de `rotation`, verticale : va à `hauteur`, ferme.

    depuis = None : la pince part de la position d'attente. On renvoie GripperOpen par sécurité, sans
    attendre (elle est déjà ouverte, et sinon elle s'ouvre pendant la descente).
    depuis = (hauteur, inclinaison, recul) : la pince vient de lâcher le cube là, ouverte autour de lui,
    avec la même rotation (voir LIAISONS). Elle va directement à `hauteur`, sans remonter.
    """
    verifier_liaison(depuis, rotation)
    if depuis is None:
        position_attente(robot, lieu, rotation)
        robot.GripperOpen()
    aller(robot, hauteur, rotation=rotation, lieu=lieu)
    fermer_pince(robot)


def lacher_et_remonter(robot, rotation=0.0, lieu=SOCLE, remonter=True):
    """Ouvre, remonte à la verticale jusqu'à la position d'attente (la pince garde sa rotation).
    remonter=False : la pince reste ouverte autour du cube (le mouvement suivant part de là)."""
    ouvrir_pince(robot)
    if remonter:
        aller(robot, H_ATTENTE, rotation=rotation, lieu=lieu)


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
