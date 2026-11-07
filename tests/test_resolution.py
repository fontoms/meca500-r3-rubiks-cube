# -*- coding: utf-8 -*-
"""Résolution (meca500_rubiks/resolution.py) : cubestring → solution → mouvements du robot.

Les tests qui appellent le solveur twophase sont ignorés si ses tables ne sont pas installées
(python installer_solveur.py)."""
import random

import pytest

from conftest import FauxRobot
from meca500_rubiks import resolution as res
from meca500_rubiks.modele_cube import ModeleCube, rot_quart

avec_solveur = pytest.mark.skipif(not res.tables_installees(), reason="solveur non installé (installer_solveur.py)")


def cube_melange(graine, n=25):
    rnd = random.Random(graine)
    m = ModeleCube()
    for _ in range(n):
        m.coup(rnd.choice("URFDLB"), rnd.choice((1, -1, 2)))
    return m


def jouer_plan(modele, etapes):
    """Applique au modèle les mouvements PHYSIQUES du robot (cube entier ou 2 couches du haut)."""
    for nom, a in etapes:
        if nom == "basculer":
            modele.tourner(rot_quart(0, a))
        elif nom == "tourner_cube":
            modele.tourner(rot_quart(2, a // 90))
        else:
            modele.tourner(rot_quart(2, a // 90), lambda p: p[2] >= 0)


def test_lire_solution():
    assert res.lire_solution("R1 U3 F2 (3f)") == [("R", 1), ("U", -1), ("F", 2)]
    assert res.lire_solution("(0f)") == []
    with pytest.raises(res.ErreurResolution):
        res.lire_solution("Error: Some corners are undefined.")


@pytest.mark.parametrize("mauvais", ["", "U" * 54, res.CUBE_RESOLU[:-1], res.CUBE_RESOLU[:-1] + "X",
                                     "R" + res.CUBE_RESOLU[1:-1] + "U"[:0] + "B"])
def test_cubestring_invalide_refuse(mauvais):
    with pytest.raises(res.ErreurResolution):
        res.verifier_cubestring(mauvais)


def test_cubestring_accepte_minuscules_et_espaces():
    assert res.verifier_cubestring(" ".join(res.CUBE_RESOLU.lower())) == res.CUBE_RESOLU


@pytest.mark.parametrize("graine", range(10))
def test_plan_du_robot_joue_bien_les_coups(graine):
    """Les mouvements physiques du robot (orientation suivie) produisent exactement les coups demandés."""
    rnd = random.Random(100 + graine)
    coups = [(rnd.choice("URFDLB"), rnd.choice((1, -1, 2))) for _ in range(20)]
    attendu, robot = ModeleCube(), ModeleCube()
    for f, k in coups:
        attendu.coup(f, k)
    jouer_plan(robot, res.plan_robot(coups))
    assert robot.egal(attendu)


def test_plan_court():
    """1 à 3 mouvements par quart de tour (pas de remise à plat du cube entre deux coups)."""
    for f in "URFDLB":
        assert 1 <= len(res.plan_robot([(f, 1)])) <= 3


def test_executer_appelle_les_mouvements_du_robot():
    robot = FauxRobot()
    res.executer(robot, [("tourner_haut", -90)], afficher=lambda *a: None)
    assert "GripperClose" in robot.noms()


@avec_solveur
@pytest.mark.parametrize("graine", range(5))
def test_solveur_et_robot_resolvent_le_cube(graine):
    """Chaîne complète : cubestring du cube mélangé → twophase → plan du robot → cube résolu."""
    m = cube_melange(graine)
    coups = res.calculer_solution(m.facelets(), temps_max=5)
    jouer_plan(m, res.plan_robot(coups))
    assert m.resolu()


@avec_solveur
def test_solveur_refuse_un_cube_impossible():
    impossible = "UUUUUUUURRRRRRRRRUFFFFFFFFFDDDDDDDDDLLLLLLLLLBBBBBBBBB"
    with pytest.raises(res.ErreurResolution):
        res.calculer_solution(impossible)


# ----------------------------- Cube tourné en entier (presenter_faces) -----------------------------

def test_tourner_cube_resolu_reste_resolu():
    for axe in range(3):
        assert res.tourner_cubestring(res.CUBE_RESOLU, rot_quart(axe, 1)) == res.CUBE_RESOLU


def test_tourner_quatre_fois_revient_au_depart():
    s = cube_melange(3).facelets()
    for axe in range(3):
        t = s
        for _ in range(4):
            t = res.tourner_cubestring(t, rot_quart(axe, 1))
        assert t == s


@avec_solveur
@pytest.mark.parametrize("graine", range(3))
def test_resolution_apres_presenter_faces(graine):
    """Cubestring construit AVANT presenter_faces → converti → solveur → robot : le cube, remis dans le
    socle tourné par presenter_faces, est bien résolu."""
    m = cube_melange(graine)
    avant = m.facelets()                                   # orientation de départ : faces bien nommées
    m.tourner(res.orientations_presenter_faces()[-1][1])   # ce que fait presenter_faces au cube
    coups = res.calculer_solution(res.cubestring_apres_presenter_faces(avant), temps_max=5)
    jouer_plan(m, res.plan_robot(coups))
    assert m.resolu()


@avec_solveur
def test_sans_conversion_le_robot_se_tromperait():
    """Garde-fou : la conversion est nécessaire (sinon le cube n'est pas résolu)."""
    m = cube_melange(11)
    avant = m.facelets()
    m.tourner(res.orientations_presenter_faces()[-1][1])
    jouer_plan(m, res.plan_robot(res.calculer_solution(avant, temps_max=5)))
    assert not m.resolu()


def test_vues_camera_presenter_faces():
    vues = [res.vue_camera(o) for _, o in res.orientations_presenter_faces()]
    assert vues[0] == ("droite", "dessus", "loin_du_robot")
    assert sorted(v[0] for v in vues) == sorted(["droite", "loin_du_robot", "gauche", "dessus", "vers_robot",
                                                 "dessous"])
