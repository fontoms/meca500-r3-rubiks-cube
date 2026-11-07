# -*- coding: utf-8 -*-
"""Briques de base (meca500_rubiks/briques.py), testées une par une avec un faux robot."""
import meca500_rubiks as rubiks

ATTENTE = rubiks.pose(rubiks.H_ATTENTE)


def test_preparer(robot):
    rubiks.preparer(robot)
    assert robot.commandes[0] == ("SetTrf", rubiks.TCP)
    assert ("SetBlending", (0,)) in robot.commandes
    assert ("SetCartLinVel", (rubiks.VITESSE_LINEAIRE,)) in robot.commandes
    assert "GripperOpen" in robot.noms()
    assert robot.poses()[-1] == ATTENTE


def test_position_attente(robot):
    rubiks.position_attente(robot)
    assert robot.commandes == [("MovePose", ATTENTE)]


def test_ouvrir_pince_attend(robot):
    rubiks.ouvrir_pince(robot)
    assert robot.commandes == [("GripperOpen", ()), ("Delay", (rubiks.DUREE_PINCE,))]


def test_fermer_pince_attend(robot):
    rubiks.fermer_pince(robot)
    assert robot.commandes == [("GripperClose", ()), ("Delay", (rubiks.DUREE_PINCE,))]


def test_aller_en_ligne_droite(robot):
    rubiks.aller(robot, 50, inclinaison=45)
    assert robot.commandes == [("MoveLin", rubiks.pose(50, 45))]


def test_saisir(robot):
    rubiks.saisir(robot, rubiks.H_CUBE)
    assert robot.noms() == ["MovePose", "GripperOpen", "MoveLin", "GripperClose", "Delay"]
    assert robot.poses()[-1] == rubiks.pose(rubiks.H_CUBE)


def test_saisir_pince_tournee(robot):
    rubiks.saisir(robot, rubiks.H_CUBE, rotation=-90)
    assert robot.poses() == [rubiks.pose(rubiks.H_ATTENTE, rotation=-90), rubiks.pose(rubiks.H_CUBE, rotation=-90)]


def test_lacher_et_remonter(robot):
    rubiks.lacher_et_remonter(robot, rotation=90)
    assert robot.noms()[0] == "GripperOpen"
    assert robot.poses() == [rubiks.pose(rubiks.H_ATTENTE, rotation=90)]     # la pince reste tournée


def test_etapes_de_rotation_par_quarts():
    """Jamais plus de 90° d'un coup (un demi-tour direct est ambigu pour le robot)."""
    assert rubiks.etapes_de_rotation(0, 0) == []
    assert rubiks.etapes_de_rotation(0, -90) == [-90]
    assert rubiks.etapes_de_rotation(90, -90) == [0, -90]
    assert rubiks.etapes_de_rotation(-90, 90) == [0, 90]


def test_tourner_pince(robot):
    rubiks.tourner_pince(robot, -90, depuis=90)
    assert robot.poses() == [rubiks.pose(rubiks.H_ATTENTE, rotation=0), rubiks.pose(rubiks.H_ATTENTE, rotation=-90)]
