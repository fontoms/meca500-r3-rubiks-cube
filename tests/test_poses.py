# -*- coding: utf-8 -*-
"""Calcul des poses (meca500_rubiks/poses.py) (sans RoboDK ni robot)."""
import math

import pytest
from robodk.robomath import TxyzRxyz_2_Pose, pi

import meca500_rubiks as rubiks
from meca500_rubiks import poses


def test_position_attente():
    assert rubiks.pose(rubiks.H_ATTENTE) == (170.0, 0.0, 116.5, 180.0, 0.0, -90.0)


def test_pose_penchee_avec_recul():
    assert rubiks.pose(rubiks.H_CUBE, 45, 0, 4) == (170.0, -2.828, 38.328, -135.0, 0.0, -90.0)


@pytest.mark.parametrize("inclinaison", [-45, 0, 45])
@pytest.mark.parametrize("rotation", [-90, 0, 90])
def test_angles_euler_coherents_avec_robodk(inclinaison, rotation):
    """Les angles (alpha, beta, gamma) renvoyés redonnent bien la matrice de rotation calculée."""
    r = poses._produit(poses._rot_x(inclinaison), poses._rot_z(rotation), poses._rot_z(90), poses._rot_x(180))
    x, y, z, a, b, g = rubiks.pose(rubiks.H_CUBE, inclinaison, rotation)
    m = TxyzRxyz_2_Pose([x, y, z, a * pi / 180, b * pi / 180, g * pi / 180])
    for i in range(3):
        for j in range(3):
            assert m[i, j] == pytest.approx(r[i][j], abs=1e-4)


@pytest.mark.parametrize("recul", [0.0, 4.0, 44.0])
def test_recul_le_long_de_l_axe_de_la_pince(recul):
    """Le recul éloigne le TCP du centre du cube exactement de `recul` mm."""
    x, y, z = rubiks.pose(rubiks.H_CUBE, 45, 0, recul)[:3]
    cx, cy, cz = rubiks.SOCLE[0], rubiks.SOCLE[1], rubiks.SOCLE[2] + rubiks.H_CUBE
    assert math.dist((x, y, z), (cx, cy, cz)) == pytest.approx(recul, abs=0.01)
    assert z >= cz - 0.01                     # on recule vers le haut, jamais dans la table
