# -*- coding: utf-8 -*-
"""Les mouvements du cube, du point de vue du robot : avant = loin du robot, arrière = vers le robot,
gauche / droite = la gauche / la droite du robot ; tourner « à gauche » = sens anti-horaire vu de dessus.

Deux sortes de fonctions :
  - les mouvements de base tourner_cube, tourner_haut, basculer, utilisés par la résolution. Ils partent
    de la position d'attente, pince ouverte DÉJÀ TOURNÉE de `prise` (une des ROTATIONS_PINCE), et y
    reviennent avec la rotation où la pince a lâché le cube (prise + angle). Le planificateur de
    resolution.py enchaîne ainsi les mouvements sans remettre la pince à 0° à chaque fois ;
  - les mouvements du menu (tourner_cube_gauche, basculer_droite…, liste MOUVEMENTS) : partent de la
    position d'attente pince à 0° et y reviennent. Les tests et les programmes RoboDK les utilisent.
tourner_cube et basculer peuvent aussi travailler sur la table (lieu=TABLE), pour presenter_faces.
"""
from .briques import (aller, aller_en_tournant, fermer_pince, lacher_et_remonter, ouvrir_pince, photographier,
                      position_attente, saisir, tourner_pince, transferer)
from .reglages import (SOCLE, TABLE, COTE_CUBE, DECALAGE_BASCULE, H_COUCHES_HAUT, H_CUBE, H_ATTENTE, INCLINAISON,
                       LEVEE, RECUL_BASCULE, ROTATION_BASCULE, ROTATIONS_PINCE)
from .vision_capture import creer_cubestring, executer_avec_apercu


def _verifier_rotations(prise, fin):
    if prise not in ROTATIONS_PINCE or fin not in ROTATIONS_PINCE:
        raise ValueError("rotation de la pince hors de %s : prise %s, fin %s (câble de la pince)"
                         % (ROTATIONS_PINCE, prise, fin))


# ----------------------------- Mouvements de base (résolution) -----------------------------

def prendre_et_reposer(robot):
    """Saisit le cube, le soulève de LEVEE mm et le repose (test de prise)."""
    saisir(robot, H_CUBE)
    aller(robot, H_CUBE + LEVEE)
    aller(robot, H_CUBE)
    lacher_et_remonter(robot)


def tourner_cube(robot, angle, lieu=SOCLE, prise=0.0):
    """Soulève le cube, le tourne de `angle` degrés (±90 ou ±180) autour de la verticale, le repose.
    La pince saisit le cube tournée de `prise` et le lâche tournée de prise + angle."""
    fin = prise + angle
    _verifier_rotations(prise, fin)
    saisir(robot, H_CUBE, lieu, prise)
    aller(robot, H_CUBE + LEVEE, rotation=prise, lieu=lieu)
    aller_en_tournant(robot, H_CUBE + LEVEE, prise, fin, lieu)
    aller(robot, H_CUBE, rotation=fin, lieu=lieu)
    lacher_et_remonter(robot, rotation=fin, lieu=lieu)


def tourner_haut(robot, angle, prise=0.0):
    """Le socle tient la couche du bas ; la pince tourne les 2 couches du haut de `angle` degrés
    (±90, ou ±180 en une seule prise : de +90° à -90° ou l'inverse)."""
    fin = prise + angle
    _verifier_rotations(prise, fin)
    saisir(robot, H_COUCHES_HAUT, rotation=prise)
    aller_en_tournant(robot, H_COUCHES_HAUT, prise, fin)
    lacher_et_remonter(robot, rotation=fin)


def basculer(robot, sens, lieu=SOCLE, prise=ROTATION_BASCULE):
    """Bascule le cube de 90° : sens = +1 le dessus part à droite du robot, -1 à gauche.

    La pince, tournée de `prise` = ±ROTATION_BASCULE (mâchoires sur les faces avant / arrière), prend
    le cube penchée d'un côté (-45°) et le repose penchée de l'autre (+45°) : le cube a tourné de 90°
    sans que la pince se couche. (Pencher vers l'avant / l'arrière met le robot en butée.)
    La pince finit en position d'attente, toujours tournée de `prise`.
    """
    if abs(prise) != ROTATION_BASCULE:
        raise ValueError("basculer : la pince doit être tournée de ±%s° (prise = %s)" % (ROTATION_BASCULE, prise))
    depart, arrivee = -INCLINAISON * sens, INCLINAISON * sens
    d, r = DECALAGE_BASCULE, prise

    position_attente(robot, lieu, r)                                             # déjà tournée au-dessus du cube
    robot.GripperOpen()                                                          # (déjà ouverte : sans attendre)
    aller(robot, H_CUBE, depart, r, recul=d + RECUL_BASCULE, lieu=lieu)          # approche, pince penchée
    aller(robot, H_CUBE, depart, r, recul=d, lieu=lieu)                          # descente le long de son axe
    fermer_pince(robot)
    aller(robot, H_CUBE + LEVEE, depart, r, recul=d, lieu=lieu)                  # soulève le cube
    aller(robot, H_CUBE + LEVEE, arrivee, r, recul=d, lieu=lieu)                 # bascule de 90° autour du centre du cube
    aller(robot, H_CUBE, arrivee, r, recul=d, lieu=lieu)                         # repose le cube
    ouvrir_pince(robot)
    aller(robot, H_CUBE, arrivee, r, recul=d + RECUL_BASCULE, lieu=lieu)         # dégagement le long de l'axe
    aller(robot, H_ATTENTE, rotation=r, lieu=lieu)                               # redressement de la pince
    robot.WaitIdle(120)


# ----------------------------- Mouvements du menu (pince à 0° au départ et à la fin) -----------------------------

def tourner_cube_et_revenir(robot, angle, lieu=SOCLE):
    tourner_cube(robot, angle, lieu)
    tourner_pince(robot, 0.0, angle, lieu)


def basculer_et_revenir(robot, sens, lieu=SOCLE):
    position_attente(robot, lieu)
    tourner_pince(robot, ROTATION_BASCULE, 0.0, lieu)
    basculer(robot, sens, lieu)
    tourner_pince(robot, 0.0, ROTATION_BASCULE, lieu)


def verifier_outil(robot):
    """Contrôle du TCP, SANS le cube : pince ouverte descendue juste au-dessus du socle, pause 10 s.

    Les patins doivent être de part et d'autre de la poche (ouvertures gauche / droite), 10 mm au-dessus
    du haut d'un cube posé. Sinon : TCP ou SOCLE (reglages.py) faux, ne pas continuer.
    """
    position_attente(robot)
    ouvrir_pince(robot)
    aller(robot, COTE_CUBE + 15.0)                # bas des patins (5 mm sous le TCP) 10 mm au-dessus du cube
    robot.WaitIdle(60)
    robot.Delay(10.0)
    position_attente(robot)
    robot.WaitIdle(60)


def tourner_cube_gauche(robot):
    """Le cube entier tourne de 90° vers la gauche (sens anti-horaire vu de dessus)."""
    tourner_cube_et_revenir(robot, +90)


def tourner_cube_droite(robot):
    """Le cube entier tourne de 90° vers la droite (sens horaire vu de dessus)."""
    tourner_cube_et_revenir(robot, -90)


def basculer_droite(robot):
    """La face du dessus part à droite du robot."""
    basculer_et_revenir(robot, +1)


def basculer_gauche(robot):
    """La face du dessus part à gauche du robot."""
    basculer_et_revenir(robot, -1)


def basculer_avant(robot):
    """La face du dessus part vers l'avant, loin du robot (3 prises)."""
    tourner_cube_droite(robot)
    basculer_droite(robot)
    tourner_cube_gauche(robot)


def basculer_arriere(robot):
    """La face du dessus vient vers le robot (3 prises)."""
    tourner_cube_droite(robot)
    basculer_gauche(robot)
    tourner_cube_gauche(robot)


def tourner_haut_gauche(robot):
    """Les 2 couches du haut tournent de 90° vers la gauche (sens anti-horaire vu de dessus)."""
    tourner_haut(robot, +90)
    tourner_pince(robot, 0.0, +90)


def tourner_haut_droite(robot):
    """Les 2 couches du haut tournent de 90° vers la droite (sens horaire vu de dessus)."""
    tourner_haut(robot, -90)
    tourner_pince(robot, 0.0, -90)


def tourner_haut_demi_tour(robot):
    """Les 2 couches du haut tournent de 180° en une seule prise (pince de +90° à -90°)."""
    position_attente(robot)
    tourner_pince(robot, +90, 0.0)
    tourner_haut(robot, -180, prise=+90)
    tourner_pince(robot, 0.0, -90)


# Présentation des 6 faces à la caméra, cube posé sur la table (la caméra est à sa droite).
# Faces nommées selon leur position AVANT la séquence, du point de vue du robot.
# Séquence la plus courte (5 prises) ; tests/test_mouvements.py vérifie qu'on voit bien les 6 faces.
# Chaque photo est prise pince à 0° (comme lors de la mise au point de la caméra).
FACE_VUE_AU_DEPART = "droite"
ETAPES_PHOTO = [                    # (mouvement fait sur la table, face alors tournée vers la caméra)
    ("tourner_droite", "loin_du_robot"),
    ("tourner_droite", "gauche"),
    ("basculer_droite", "dessus"),
    ("tourner_droite", "vers_robot"),
    ("tourner_droite", "dessous"),
]
MOUVEMENTS_SUR_TABLE = {
    "tourner_gauche": lambda robot: tourner_cube_et_revenir(robot, +90, TABLE),
    "tourner_droite": lambda robot: tourner_cube_et_revenir(robot, -90, TABLE),
    "basculer_droite": lambda robot: basculer_et_revenir(robot, +1, TABLE),
    "basculer_gauche": lambda robot: basculer_et_revenir(robot, -1, TABLE),
}


def presenter_faces(robot, selection_camera=None, callback_apercu=None, afficher_fenetre=True,
                    callback_erreur_vision=None):
    """Pose le cube sur la table devant la caméra, photographie ses 6 faces, le remet dans le socle.

    Le cube revient dans le socle dans une autre orientation qu'au départ.
    Renvoie les faces dans l'ordre des photos et génère cubestring.txt sur le vrai robot.
    """
    def presenter(camera, references):
        photos = {}

        def capturer(face):
            couleurs = photographier(robot, face, camera, references)
            if camera is not None:
                photos[face] = couleurs

        transferer(robot, SOCLE, TABLE)
        capturer(FACE_VUE_AU_DEPART)
        for mouvement, face in ETAPES_PHOTO:
            MOUVEMENTS_SUR_TABLE[mouvement](robot)
            if face is not None:
                capturer(face)
        transferer(robot, TABLE, SOCLE)
        if camera is not None:
            creer_cubestring(photos)
        return [FACE_VUE_AU_DEPART] + [face for _, face in ETAPES_PHOTO if face is not None]

    return executer_avec_apercu(
        robot, presenter, selection_camera, callback_apercu, afficher_fenetre,
        callback_erreur_vision)


MOUVEMENTS = [
    verifier_outil,
    prendre_et_reposer,
    tourner_cube_gauche, tourner_cube_droite,
    basculer_gauche, basculer_droite,
    basculer_avant, basculer_arriere,
    tourner_haut_gauche, tourner_haut_droite, tourner_haut_demi_tour,
    presenter_faces,
]
