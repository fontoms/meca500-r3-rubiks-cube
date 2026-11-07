# -*- coding: utf-8 -*-
"""Modèle logiciel du cube (simulation/modele_cube.py)."""
import random

import pytest

from modele_cube import DIR_FACE, ModeleCube, chemin_vers_bas, ecrire_coups, inverse, lire_coups, mul, rot_quart


def test_cube_neuf_resolu():
    assert ModeleCube().resolu()
    assert ModeleCube().facelets() == "".join(f * 9 for f in "URFDLB")


@pytest.mark.parametrize("face", "URFDLB")
def test_quatre_quarts_de_tour_reviennent_au_depart(face):
    m = ModeleCube()
    for _ in range(4):
        m.coup(face, 1)
    assert m.egal(ModeleCube())


@pytest.mark.parametrize("face", "URFDLB")
def test_un_quart_de_tour_melange(face):
    m = ModeleCube()
    m.coup(face, 1)
    assert not m.resolu()


def test_lire_ecrire_coups():
    texte = "R U' F2 L D' B"
    assert ecrire_coups(lire_coups(texte)) == texte
    with pytest.raises(ValueError):
        lire_coups("X")


@pytest.mark.parametrize("graine", range(5))
def test_inverse_du_melange_resout(graine):
    rnd = random.Random(graine)
    melange = [(rnd.choice("UDFBLR"), rnd.choice((1, -1, 2))) for _ in range(20)]
    m = ModeleCube()
    for f, k in melange + inverse(melange):
        m.coup(f, k)
    assert m.resolu()


def test_rotation_du_cube_entier_ne_le_melange_pas():
    m = ModeleCube()
    m.tourner(rot_quart(2, 1))
    assert m.resolu()


@pytest.mark.parametrize("direction", list(DIR_FACE.values()))
def test_chemin_vers_bas(direction):
    v = direction
    for op, a in chemin_vers_bas(direction):
        v = mul(rot_quart(0 if op == "B" else 2, a), v)
    assert v == (0, 0, -1)
