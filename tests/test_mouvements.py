# -*- coding: utf-8 -*-
"""
Un groupe de tests PAR MOUVEMENT (classe TestXxx) : dans PyCharm, le ▶ à côté d'une classe
lance seulement ce mouvement.

  - séquence de commandes (faux robot, sans RoboDK) ;
  - cinématique dans RoboDK : atteignable, butées, poignet, sauts (RoboDK ouvert, sinon ignoré) ;
  - simulation animée dans RoboDK : seulement avec  pytest -m simulation.
"""
import pytest

import meca500_rubiks as rubiks
from conftest import FauxRobot

ATTENTE = rubiks.pose(rubiks.H_ATTENTE)


def support_le_plus_proche(x, y):
    return min((rubiks.SOCLE, rubiks.TABLE), key=lambda s: (s[0] - x) ** 2 + (s[1] - y) ** 2)


class _Controles:
    """Contrôles communs ; chaque classe TestXxx ci-dessous choisit son mouvement."""
    mouvement = None

    def jouer(self):
        robot = FauxRobot()
        type(self).mouvement(robot)
        return robot

    def test_part_et_revient_en_position_d_attente(self):
        poses = self.jouer().poses()
        assert poses[0] == ATTENTE
        assert poses[-1] == ATTENTE

    def test_pince_ouverte_a_la_fin(self):
        etat = "ouverte"
        for nom in self.jouer().noms():
            if nom == "GripperClose":
                assert etat == "ouverte", "pince fermée deux fois de suite"
                etat = "fermee"
            elif nom == "GripperOpen":
                etat = "ouverte"
        assert etat == "ouverte"

    def test_tcp_jamais_sous_le_centre_du_cube(self):
        """Le TCP ne descend pas sous le centre du cube posé (socle ou table) : la pince ne touche pas le support."""
        for p in self.jouer().poses():
            support = support_le_plus_proche(p[0], p[1])
            assert p[2] >= support[2] + rubiks.H_CUBE - 3.0, p

    @pytest.mark.robodk
    def test_cinematique_robodk(self):
        import verifier
        v = verifier.verifier_mouvement(type(self).mouvement)
        assert not v.problemes, "\n".join(v.problemes)

    @pytest.mark.robodk
    def test_collisions_robodk(self):
        """Robot, pince, vrais doigts et cube tenu contre le vrai socle, la table, la caméra et le cube."""
        import banc_essais
        import simulateur
        banc_essais.preparer_scene([])
        try:
            problemes = simulateur.tester_collisions(type(self).mouvement.__name__)
        finally:
            banc_essais.preparer_scene([])
        assert not problemes, "\n".join("%s : %s" % (e, ", ".join(o)) for e, o in problemes)

    @pytest.mark.simulation
    def test_simulation_robodk(self):
        import simulateur
        simulateur.simuler(type(self).mouvement.__name__)


class TestVerifierOutil(_Controles):
    mouvement = rubiks.verifier_outil


class TestPrendreEtReposer(_Controles):
    mouvement = rubiks.prendre_et_reposer


class TestTournerCubeGauche(_Controles):
    mouvement = rubiks.tourner_cube_gauche


class TestTournerCubeDroite(_Controles):
    mouvement = rubiks.tourner_cube_droite


class TestBasculerGauche(_Controles):
    mouvement = rubiks.basculer_gauche


class TestBasculerDroite(_Controles):
    mouvement = rubiks.basculer_droite


class TestBasculerAvant(_Controles):
    mouvement = rubiks.basculer_avant


class TestBasculerArriere(_Controles):
    mouvement = rubiks.basculer_arriere


class TestTournerHautGauche(_Controles):
    mouvement = rubiks.tourner_haut_gauche


class TestTournerHautDroite(_Controles):
    mouvement = rubiks.tourner_haut_droite


class TestTournerHautDemiTour(_Controles):
    mouvement = rubiks.tourner_haut_demi_tour


# Toutes les étapes que le planificateur (resolution.plan_robot) peut choisir : chaque mouvement de base
# avec chaque rotation de pince permise. Testées une par une : pince tournée en l'air jusqu'à la prise,
# mouvement, retour à 0°.
def _variantes():
    from meca500_rubiks import resolution as res
    variantes = []
    for prise in rubiks.ROTATIONS_PINCE:
        for angle in res.ANGLES:
            if prise + angle in rubiks.ROTATIONS_PINCE:
                variantes += [("tourner_cube", angle, prise), ("tourner_haut", angle, prise)]
        if abs(prise) == rubiks.ROTATION_BASCULE:
            variantes += [("basculer", 1, prise), ("basculer", -1, prise)]
    return variantes


VARIANTES = _variantes()


# Liaisons rapides (resolution.executer) : deux prises de suite (tourner_cube, tourner_haut, basculer) sans
# que la pince remonte entre les deux. Chaque paire possible est testée.
def _liaisons():
    from meca500_rubiks import resolution as res
    return [(a, b) for a in VARIANTES for b in VARIANTES if b[2] == res.rotation_pince_apres(a)]


LIAISONS = _liaisons()


def _jouer_variante(*etapes):
    """Pince tournée en l'air jusqu'à la première prise, étapes jouées comme par la résolution, retour à 0°."""
    from meca500_rubiks import resolution as res
    plan = list(etapes)
    if plan[0][2] != 0.0:
        plan.insert(0, ("tourner_pince", plan[0][2], 0.0))
    fin = res.rotation_pince_apres(plan[-1])
    if fin != 0.0:
        plan.append(("tourner_pince", 0.0, fin))

    def mouvement(robot):
        res.executer(robot, plan, afficher=lambda *a: None)
    mouvement.__name__ = "_puis_".join("%s_%+d_pince_%+d" % e for e in etapes)
    return mouvement


def _nom(e):
    return "%s%+d@%+d" % (e[0], e[1], e[2])


def _nom_liaison(paire):
    return " puis ".join(map(_nom, paire))


@pytest.mark.parametrize("etape", VARIANTES, ids=_nom)
def test_variante_finit_pince_ouverte_en_attente(etape):
    robot = FauxRobot()
    _jouer_variante(etape)(robot)
    assert robot.poses()[-1] == ATTENTE
    assert [n for n in robot.noms() if n.startswith("Gripper")][-1] == "GripperOpen"


def test_il_y_a_des_liaisons_rapides():
    assert len(LIAISONS) >= 10


@pytest.mark.parametrize("paire", LIAISONS, ids=_nom_liaison)
def test_liaison_sans_remonter(paire):
    """Entre les deux prises, la pince ne remonte pas : elle va directement à la hauteur de la 2e prise."""
    robot = FauxRobot()
    _jouer_variante(*paire)(robot)
    noms = robot.noms()
    premiere_fermeture = noms.index("GripperClose")
    lacher = noms.index("GripperOpen", premiere_fermeture)                 # la pince lâche le cube
    suivant = next(args for n, args in robot.commandes[lacher:] if n in ("MoveLin", "MovePose"))
    assert suivant[2] < rubiks.SOCLE[2] + rubiks.H_ATTENTE - 1, "la pince est remontée entre les deux prises"
    entre = noms[lacher:noms.index("GripperClose", lacher)]
    assert entre.count("MoveLin") + entre.count("MovePose") <= 1, "un seul déplacement jusqu'à la prise suivante"
    assert noms[lacher:].count("GripperClose") == 1                      # puis elle reprend le cube
    assert robot.poses()[-1] == ATTENTE


@pytest.mark.robodk
@pytest.mark.parametrize("etape", VARIANTES, ids=_nom)
def test_variante_cinematique_robodk(etape):
    import verifier
    v = verifier.verifier_mouvement(_jouer_variante(etape))
    assert not v.problemes, "\n".join(v.problemes)


@pytest.mark.robodk
@pytest.mark.parametrize("paire", LIAISONS, ids=_nom_liaison)
def test_liaison_cinematique_robodk(paire):
    import verifier
    v = verifier.verifier_mouvement(_jouer_variante(*paire))
    assert not v.problemes, "\n".join(v.problemes)


@pytest.mark.robodk
@pytest.mark.parametrize("paire", LIAISONS, ids=_nom_liaison)
def test_liaison_collisions_robodk(paire):
    import banc_essais
    import simulateur
    banc_essais.preparer_scene([])
    try:
        problemes = simulateur.tester_collisions(_jouer_variante(*paire))
    finally:
        banc_essais.preparer_scene([])
    assert not problemes, "\n".join("%s : %s" % (e, ", ".join(o)) for e, o in problemes)


@pytest.mark.robodk
@pytest.mark.parametrize("etape", VARIANTES, ids=_nom)
def test_variante_collisions_robodk(etape):
    import banc_essais
    import simulateur
    banc_essais.preparer_scene([])
    try:
        problemes = simulateur.tester_collisions(_jouer_variante(etape))
    finally:
        banc_essais.preparer_scene([])
    assert not problemes, "\n".join("%s : %s" % (e, ", ".join(o)) for e, o in problemes)


class TestPresenterFaces(_Controles):
    mouvement = rubiks.presenter_faces

    def test_une_photo_par_face(self):
        robot = self.jouer()
        photos = [args[0] for nom, args in robot.commandes if nom == "prendre_photo"]
        assert sorted(photos) == sorted(DIRECTION_FACE)

    def test_robot_immobile_avant_chaque_photo(self):
        noms = self.jouer().noms()
        for i, nom in enumerate(noms):
            if nom == "prendre_photo":
                assert noms[i - 1] == "WaitIdle"


# Effet de chaque mouvement sur l'orientation du cube (quarts de tour autour de X / Y / Z)
ROTATIONS = {"tourner_gauche": (2, 1), "tourner_droite": (2, -1), "basculer_droite": (0, 1), "basculer_gauche": (0, -1)}
DIRECTION_FACE = {"dessus": (0, 0, 1), "dessous": (0, 0, -1), "vers_robot": (-1, 0, 0),
                  "loin_du_robot": (1, 0, 0), "gauche": (0, 1, 0), "droite": (0, -1, 0)}


def test_sequence_photo_montre_vraiment_chaque_face():
    """Avec le modèle du cube : à chaque photo, la face annoncée est bien tournée vers la caméra (à droite)."""
    from modele_cube import mul, mulm, rot_quart, transp
    vers_camera = DIRECTION_FACE["droite"]
    orientation = rot_quart(0, 0)
    vues = []
    for mouvement, face in [(None, rubiks.FACE_VUE_AU_DEPART)] + rubiks.ETAPES_PHOTO:
        if mouvement is not None:
            orientation = mulm(rot_quart(*ROTATIONS[mouvement]), orientation)
        if face is None:
            continue
        assert mul(transp(orientation), vers_camera) == DIRECTION_FACE[face], (mouvement, face)
        vues.append(face)
    assert sorted(vues) == sorted(DIRECTION_FACE)


@pytest.mark.parametrize("nom, attendu", [
    ("tourner_cube_gauche", ((2, 1),)), ("tourner_cube_droite", ((2, -1),)),
    ("basculer_droite", ((0, 1),)), ("basculer_gauche", ((0, -1),)),
    ("basculer_avant", ((2, -1), (0, 1), (2, 1))), ("basculer_arriere", ((2, -1), (0, -1), (2, 1))),
])
def test_sens_des_mouvements_point_de_vue_du_robot(nom, attendu):
    """Gauche = +Y, avant = +X (loin du robot) : vérifié sur la face du dessus / la face avant."""
    from modele_cube import mul, mulm, rot_quart
    o = rot_quart(0, 0)
    for q in attendu:
        o = mulm(rot_quart(*q), o)
    dessus, loin = mul(o, (0, 0, 1)), mul(o, (1, 0, 0))
    if nom.startswith("basculer"):
        cible = {"avant": (1, 0, 0), "arriere": (-1, 0, 0), "gauche": (0, 1, 0), "droite": (0, -1, 0)}
        assert dessus == cible[nom.split("_")[1]]
    else:                                   # tourner à gauche : la face loin du robot part à gauche
        assert loin == ((0, 1, 0) if nom.endswith("gauche") else (0, -1, 0))


def test_presenter_faces_pose_le_cube_sur_la_table():
    robot = FauxRobot()
    rubiks.presenter_faces(robot)
    table = [p for p in robot.poses() if support_le_plus_proche(p[0], p[1]) == rubiks.TABLE]
    assert table, "le cube n'est jamais allé sur la table"
    assert min(p[2] for p in table) == pytest.approx(rubiks.TABLE[2] + rubiks.H_CUBE)


def test_dimensions_identiques_robot_et_simulation():
    """La simulation reprend la géométrie de meca500_rubiks/reglages.py (source unique)."""
    import parametres as P
    assert P.TCP == rubiks.TCP
    assert (P.SOCLE_X, P.SOCLE_Y, P.HAUTEUR_SOCLE) == rubiks.SOCLE
    assert (P.TABLE_X, P.TABLE_Y, P.HAUTEUR_TABLE) == rubiks.TABLE
    assert P.COTE_CUBE == rubiks.COTE_CUBE


def test_maillages_presents():
    import os
    import parametres as P
    for f in (P.FICHIER_SOCLE, P.FICHIER_DOIGT_1, P.FICHIER_DOIGT_2):
        assert os.path.isfile(f), f


def test_programmes_robodk_lisibles_par_python():
    """Les programmes de la station (simulation/programmes) sont en UTF-8 et compilent : sinon RoboDK
    affiche « SyntaxError: Non-UTF-8 code » quand on clique dessus (fichiers écrits sous Windows en cp1252)."""
    import glob
    import os
    import parametres as P
    fichiers = glob.glob(os.path.join(P.DOSSIER_PROGRAMMES, "*.py"))
    assert fichiers
    for f in fichiers:
        with open(f, "rb") as fichier:
            compile(fichier.read(), f, "exec")         # comme Python : UTF-8 par défaut


def test_programmes_robodk_sans_chemin_ecrit_en_dur():
    """Les programmes de la station marchent sur tous les ordinateurs (Mac et Windows)."""
    import glob
    import os
    import parametres as P
    for f in glob.glob(os.path.join(P.DOSSIER_PROGRAMMES, "*.py")):
        texte = open(f, encoding="utf-8").read()
        assert P.DOSSIER_PROJET not in texte and "/Users/" not in texte and "C:\\\\" not in texte, f
