# -*- coding: utf-8 -*-
"""
Estimation de la durée d'un mouvement du robot, SANS robot ni RoboDK.

Chronometre est un faux robot mecademicpy : au lieu de bouger, il additionne le temps que prendrait
chaque commande avec les vitesses de reglages.py. C'est une ESTIMATION (accélérations simplifiées),
utile pour COMPARER deux façons de faire ; le planificateur de resolution.py s'en sert pour choisir
la suite de mouvements la plus rapide.

    from meca500_rubiks import duree, tourner_cube_gauche
    print(duree.estimer(tourner_cube_gauche))          # secondes
"""
import math

from .reglages import DUREE_PHOTO

# Meca500 R3 (fiche technique Mecademic) : vitesse maximale de chaque articulation, en °/s.
VITESSE_MAX_ARTICULATIONS = (150.0, 150.0, 180.0, 300.0, 300.0, 500.0)
RAYON_BRAS = 200.0      # mm : distance typique entre l'axe J1 et la pince (pour estimer les MovePose)
T_ACCELERATION = 0.15   # s ajoutées à chaque déplacement (accélération + décélération + arrêt)


def _matrice(alpha, beta, gamma):
    """Rotation Mecademic Rx(alpha)·Ry(beta)·Rz(gamma) (degrés)."""
    a, b, g = (math.radians(v) for v in (alpha, beta, gamma))
    ca, sa, cb, sb, cg, sg = math.cos(a), math.sin(a), math.cos(b), math.sin(b), math.cos(g), math.sin(g)
    return [[cb * cg, -cb * sg, sb],
            [ca * sg + sa * sb * cg, ca * cg - sa * sb * sg, -sa * cb],
            [sa * sg - ca * sb * cg, sa * cg + ca * sb * sg, ca * cb]]


def angle_entre(p1, p2):
    """Angle (°) de la rotation qui fait passer de l'orientation de la pose p1 à celle de p2."""
    r1, r2 = _matrice(*p1[3:]), _matrice(*p2[3:])
    trace = sum(r1[k][i] * r2[k][i] for i in range(3) for k in range(3))
    return math.degrees(math.acos(max(-1.0, min(1.0, (trace - 1) / 2))))


class Chronometre:
    """Faux robot : self.temps = durée estimée (s) des commandes reçues."""

    def __init__(self):
        self.temps = 0.0
        self.pose = None
        self.v_lin, self.v_ang, self.v_art = 150.0, 45.0, 25.0      # valeurs par défaut du Meca500

    def _deplacement(self, p, duree):
        if self.pose is not None:
            self.temps += duree + T_ACCELERATION
        self.pose = p

    def MoveLin(self, *p):
        if self.pose is None:
            self.pose = p
            return
        d, a = math.dist(self.pose[:3], p[:3]), angle_entre(self.pose, p)
        self._deplacement(p, max(d / self.v_lin, a / self.v_ang))

    def MovePose(self, *p):
        """Mouvement articulaire : la pince tourne surtout avec J6, le bras se déplace avec J1-J3."""
        if self.pose is None:
            self.pose = p
            return
        pct = self.v_art / 100.0
        d, a = math.dist(self.pose[:3], p[:3]), angle_entre(self.pose, p)
        v_bras = RAYON_BRAS * math.radians(VITESSE_MAX_ARTICULATIONS[0]) * pct
        self._deplacement(p, max(d / v_bras, a / (VITESSE_MAX_ARTICULATIONS[5] * pct)))

    def Delay(self, secondes):
        self.temps += secondes

    def prendre_photo(self, face):
        self.temps += DUREE_PHOTO

    def SetCartLinVel(self, v):
        self.v_lin = v

    def SetCartAngVel(self, v):
        self.v_ang = v

    def SetJointVel(self, v):
        self.v_art = v

    def _rien(self, *args, **kwargs):
        pass

    SetTrf = SetBlending = GripperOpen = GripperClose = WaitIdle = _rien


def estimer(mouvement, *args):
    """Durée estimée (s) de mouvement(robot, *args), robot préparé (vitesses, position d'attente)."""
    from .briques import preparer
    robot = Chronometre()
    preparer(robot)
    robot.temps = 0.0
    mouvement(robot, *args)
    return robot.temps
