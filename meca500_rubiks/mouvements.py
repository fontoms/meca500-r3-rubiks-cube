# -*- coding: utf-8 -*-
"""Les mouvements du cube, du point de vue du robot : avant = loin du robot, arrière = vers le robot,
gauche / droite = la gauche / la droite du robot ; tourner « à gauche » = sens anti-horaire vu de dessus.

Chaque fonction part de la position d'attente et y revient, cube reposé dans le socle, pince ouverte.
tourner_cube et basculer peuvent aussi travailler sur la table (lieu=TABLE), pour presenter_faces.
"""
from .briques import (aller, fermer_pince, lacher_et_remonter, ouvrir_pince, photographier,
                      position_attente, saisir, transferer)
from .reglages import (SOCLE, TABLE, COTE_CUBE, DECALAGE_BASCULE, H_ATTENTE, H_COUCHES_HAUT, H_CUBE, INCLINAISON, LEVEE,
                       RECUL_BASCULE, ROTATION_BASCULE)


def prendre_et_reposer(robot):
    """Saisit le cube, le soulève de LEVEE mm et le repose (test de prise)."""
    saisir(robot, H_CUBE)
    aller(robot, H_CUBE + LEVEE)
    aller(robot, H_CUBE)
    lacher_et_remonter(robot)


def tourner_cube(robot, angle, lieu=SOCLE):
    """Soulève le cube, le tourne de `angle` degrés autour de la verticale, le repose."""
    saisir(robot, H_CUBE, lieu)
    aller(robot, H_CUBE + LEVEE, lieu=lieu)
    aller(robot, H_CUBE + LEVEE, rotation=angle, lieu=lieu)
    aller(robot, H_CUBE, rotation=angle, lieu=lieu)
    lacher_et_remonter(robot, rotation=angle, lieu=lieu)


def basculer(robot, sens, lieu=SOCLE):
    """Bascule le cube de 90° : sens = +1 le dessus part à droite du robot, -1 à gauche.

    La pince tourne de ROTATION_BASCULE (mâchoires sur les faces avant / arrière), prend le cube
    penchée d'un côté (-45°) et le repose penchée de l'autre (+45°) : le cube a tourné de 90° sans
    que la pince se couche. (Pencher vers l'avant / l'arrière met le robot en butée.)
    """
    depart, arrivee = -INCLINAISON * sens, INCLINAISON * sens
    d, r = DECALAGE_BASCULE, ROTATION_BASCULE

    position_attente(robot, lieu)
    aller(robot, H_ATTENTE, rotation=r, lieu=lieu)                               # tourne au-dessus du cube
    ouvrir_pince(robot)
    aller(robot, H_CUBE, depart, r, recul=d + RECUL_BASCULE, lieu=lieu)          # approche, pince penchée
    aller(robot, H_CUBE, depart, r, recul=d, lieu=lieu)                          # descente le long de son axe
    fermer_pince(robot)
    aller(robot, H_CUBE + LEVEE, depart, r, recul=d, lieu=lieu)                  # soulève le cube
    aller(robot, H_CUBE + LEVEE, arrivee, r, recul=d, lieu=lieu)                 # bascule de 90° autour du centre du cube
    aller(robot, H_CUBE, arrivee, r, recul=d, lieu=lieu)                         # repose le cube
    ouvrir_pince(robot)
    aller(robot, H_CUBE, arrivee, r, recul=d + RECUL_BASCULE, lieu=lieu)         # dégagement le long de l'axe
    aller(robot, H_ATTENTE, rotation=r, lieu=lieu)                               # redressement de la pince
    position_attente(robot, lieu)
    robot.WaitIdle(120)


def tourner_haut(robot, angle):
    """Le socle tient la couche du bas ; la pince tourne les 2 couches du haut de `angle` degrés."""
    saisir(robot, H_COUCHES_HAUT)
    aller(robot, H_COUCHES_HAUT, rotation=angle)
    lacher_et_remonter(robot, rotation=angle)


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
    tourner_cube(robot, +90)


def tourner_cube_droite(robot):
    """Le cube entier tourne de 90° vers la droite (sens horaire vu de dessus)."""
    tourner_cube(robot, -90)


def basculer_droite(robot):
    """La face du dessus part à droite du robot."""
    basculer(robot, +1)


def basculer_gauche(robot):
    """La face du dessus part à gauche du robot."""
    basculer(robot, -1)


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


def tourner_haut_droite(robot):
    """Les 2 couches du haut tournent de 90° vers la droite (sens horaire vu de dessus)."""
    tourner_haut(robot, -90)


# Présentation des 6 faces à la caméra, cube posé sur la table (la caméra est à sa droite).
# Faces nommées selon leur position AVANT la séquence, du point de vue du robot.
# Séquence la plus courte (5 prises) ; tests/test_mouvements.py vérifie qu'on voit bien les 6 faces.
FACE_VUE_AU_DEPART = "droite"
ETAPES_PHOTO = [                    # (mouvement fait sur la table, face alors tournée vers la caméra)
    ("tourner_droite", "loin_du_robot"),
    ("tourner_droite", "gauche"),
    ("basculer_droite", "dessus"),
    ("tourner_droite", "vers_robot"),
    ("tourner_droite", "dessous"),
]
MOUVEMENTS_SUR_TABLE = {
    "tourner_gauche": lambda robot: tourner_cube(robot, +90, TABLE),
    "tourner_droite": lambda robot: tourner_cube(robot, -90, TABLE),
    "basculer_droite": lambda robot: basculer(robot, +1, TABLE),
    "basculer_gauche": lambda robot: basculer(robot, -1, TABLE),
}


def presenter_faces(robot):
    """Pose le cube sur la table devant la caméra, photographie ses 6 faces, le remet dans le socle.

    Le cube revient dans le socle dans une autre orientation qu'au départ.
    Renvoie les faces dans l'ordre des photos.
    """
    transferer(robot, SOCLE, TABLE)
    photographier(robot, FACE_VUE_AU_DEPART)
    for mouvement, face in ETAPES_PHOTO:
        MOUVEMENTS_SUR_TABLE[mouvement](robot)
        if face is not None:
            photographier(robot, face)
    transferer(robot, TABLE, SOCLE)
    return [FACE_VUE_AU_DEPART] + [face for _, face in ETAPES_PHOTO if face is not None]


MOUVEMENTS = [
    verifier_outil,
    prendre_et_reposer,
    tourner_cube_gauche, tourner_cube_droite,
    basculer_gauche, basculer_droite,
    basculer_avant, basculer_arriere,
    tourner_haut_gauche, tourner_haut_droite,
    presenter_faces,
]
