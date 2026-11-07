# -*- coding: utf-8 -*-
"""Calcul des poses de la pince (x, y, z, alpha, beta, gamma) pour MoveLin / MovePose."""
import math

from .reglages import SOCLE


def _rot_x(deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return [[1, 0, 0], [0, c, -s], [0, s, c]]


def _rot_y(deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return [[c, 0, s], [0, 1, 0], [-s, 0, c]]


def _rot_z(deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return [[c, -s, 0], [s, c, 0], [0, 0, 1]]


def _produit(*matrices):
    resultat = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
    for m in matrices:
        resultat = [[sum(resultat[i][k] * m[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
    return resultat


def _euler_xyz(r):
    """Angles (alpha, beta, gamma) de Mecademic : rotation = Rx(alpha)·Ry(beta)·Rz(gamma)."""
    beta = math.asin(max(-1.0, min(1.0, r[0][2])))
    alpha = math.atan2(-r[1][2], r[2][2])
    gamma = math.atan2(-r[0][1], r[0][0])
    return tuple(round(math.degrees(a), 3) + 0.0 for a in (alpha, beta, gamma))


def pose(hauteur, inclinaison=0.0, rotation=0.0, recul=0.0, lieu=SOCLE):
    """Pose de la pince (x, y, z, alpha, beta, gamma) pour MoveLin / MovePose.

    hauteur      : hauteur du TCP au-dessus de l'endroit où le cube est posé (mm)
    inclinaison  : pince penchée vers la droite (+) ou la gauche (-) du robot, en degrés
    rotation     : pince tournée autour de la verticale (+ : sens anti-horaire vu de dessus)
    recul        : TCP reculé de ce nombre de mm le long de l'axe de la pince
    lieu         : où est posé le cube : SOCLE (dessus du socle) ou TABLE (reglages.py)

    Pince de référence : verticale, bout des doigts vers le robot, mâchoires serrant les faces gauche /
    droite du cube (vu depuis le robot). C'est J6 ≈ 0° : le câble de la pince est dans sa position
    neutre (celle du montage). Loin de l'axe X du robot (table), tout le repère tourne autour de la verticale pour
    rester face au robot : sinon la pince penchée met le poignet en butée.
    """
    face_au_robot = math.degrees(math.atan2(lieu[1], lieu[0]))
    r = _produit(_rot_z(face_au_robot), _rot_x(inclinaison), _rot_z(rotation), _rot_z(180), _rot_x(180))
    axe = [r[0][2], r[1][2], r[2][2]]                 # axe de la pince (vers le cube)
    x, y, z = lieu[0], lieu[1], lieu[2] + hauteur
    position = (x - recul * axe[0], y - recul * axe[1], z - recul * axe[2])
    return tuple(round(v, 3) + 0.0 for v in position) + _euler_xyz(r)
