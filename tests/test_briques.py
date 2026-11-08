# -*- coding: utf-8 -*-
"""Briques de base (meca500_rubiks/briques.py), testées une par une avec un faux robot."""
import pytest

import meca500_rubiks as rubiks
import meca500_rubiks.briques as briques

ATTENTE = rubiks.pose(rubiks.H_ATTENTE)


def test_preparer(robot):
    rubiks.preparer(robot)
    assert robot.commandes[0] == ("SetTrf", rubiks.TCP)
    assert ("SetBlending", (0,)) in robot.commandes
    facteur = rubiks.VITESSE_GLOBALE
    assert ("SetCartLinVel", (rubiks.VITESSE_LINEAIRE * facteur,)) in robot.commandes
    assert ("SetCartAngVel", (rubiks.VITESSE_ANGULAIRE * facteur,)) in robot.commandes
    assert ("SetJointVel", (rubiks.VITESSE_ARTICULAIRE * facteur,)) in robot.commandes
    assert ("SetJointVelLimit", (rubiks.VITESSE_ARTICULAIRE * facteur,)) in robot.commandes
    assert "GripperOpen" in robot.noms()
    assert robot.poses()[-1] == ATTENTE


def test_preparer_applique_le_facteur_global(monkeypatch, robot):
    monkeypatch.setattr(briques, "VITESSE_GLOBALE", 0.5)

    rubiks.preparer(robot)

    assert ("SetCartLinVel", (rubiks.VITESSE_LINEAIRE * 0.5,)) in robot.commandes
    assert ("SetCartAngVel", (rubiks.VITESSE_ANGULAIRE * 0.5,)) in robot.commandes
    assert ("SetJointVel", (rubiks.VITESSE_ARTICULAIRE * 0.5,)) in robot.commandes
    assert ("SetJointVelLimit", (rubiks.VITESSE_ARTICULAIRE * 0.5,)) in robot.commandes


def test_preparer_applique_le_facteur_choisi(robot):
    rubiks.preparer(robot, 0.75)

    assert ("SetCartLinVel", (rubiks.VITESSE_LINEAIRE * 0.75,)) in robot.commandes
    assert ("SetCartAngVel", (rubiks.VITESSE_ANGULAIRE * 0.75,)) in robot.commandes
    assert ("SetJointVel", (rubiks.VITESSE_ARTICULAIRE * 0.75,)) in robot.commandes
    assert ("SetJointVelLimit", (rubiks.VITESSE_ARTICULAIRE * 0.75,)) in robot.commandes


def test_regler_vitesse_valide_et_applique_les_trois_axes(robot):
    assert rubiks.regler_vitesse(robot, 0.25) == 0.25
    assert robot.commandes == [
        ("SetCartLinVel", (rubiks.VITESSE_LINEAIRE * 0.25,)),
        ("SetCartAngVel", (rubiks.VITESSE_ANGULAIRE * 0.25,)),
        ("SetJointVel", (rubiks.VITESSE_ARTICULAIRE * 0.25,)),
        ("SetJointVelLimit", (rubiks.VITESSE_ARTICULAIRE * 0.25,)),
    ]


@pytest.mark.parametrize("facteur", [0, -0.5, 1.01, float("inf"), float("nan"), True, "0.5"])
def test_regler_vitesse_refuse_un_facteur_invalide(robot, facteur):
    with pytest.raises(ValueError, match="facteur de vitesse"):
        rubiks.regler_vitesse(robot, facteur)
    assert not robot.commandes


def test_menu_permet_de_changer_la_vitesse_globale(monkeypatch, robot):
    from meca500_rubiks.robot_reel import menu

    saisies = iter(["v", "100", ""])
    monkeypatch.setattr("builtins.input", lambda prompt: next(saisies))

    menu(robot)

    assert ("SetCartLinVel", (5000.0,)) in robot.commandes
    assert ("SetCartAngVel", (1000.0,)) in robot.commandes
    assert ("SetJointVel", (100.0,)) in robot.commandes
    assert ("SetJointVelLimit", (100.0,)) in robot.commandes


def test_vitesses_de_base_et_facteur_global():
    assert rubiks.VITESSE_LINEAIRE == 5000.0
    assert rubiks.VITESSE_ANGULAIRE == 1000.0
    assert rubiks.VITESSE_ARTICULAIRE == 100.0
    assert rubiks.VITESSE_GLOBALE == 0.1


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
