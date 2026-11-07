# -*- coding: utf-8 -*-
"""
Construction de la scène RoboDK : robot, socle, cube (26 cubies) et pince MEGP 25E.

Les dimensions viennent de parametres.py.
"""
import math
import os

from robodk import robolink, robomath
from robodk.robomath import Mat, rotz, transl

import parametres as P
from connexion_robodk import RDK
from modele_cube import FACE_DIR, ModeleCube, nom_cubie


# ----------------------------- Maillages -----------------------------

def boite(x0, y0, z0, x1, y1, z1):
    """Liste de triangles (36 points) d'un pavé aligné sur les axes."""
    p = [[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0],
         [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]]
    faces = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4),
             (2, 3, 7), (2, 7, 6), (1, 2, 6), (1, 6, 5), (3, 0, 4), (3, 4, 7)]
    pts = []
    for a, b, c in faces:
        pts += [p[a], p[b], p[c]]
    return pts


def morceaux_cubie(p0):
    """Corps noir + un autocollant coloré par face visible du cubie de position initiale p0."""
    a, m, e = P.S / 2 - 0.3, 1.2, 0.6
    morceaux = [(boite(-a, -a, -a, a, a, a), "noir")]
    for i in range(3):
        if p0[i]:
            sg = p0[i]
            lo, hi = sorted([sg * a, sg * (a + e)])
            b = [-a + m, -a + m, -a + m, a - m, a - m, a - m]
            b[i], b[i + 3] = lo, hi
            morceaux.append((boite(*b), FACE_DIR[tuple(sg if j == i else 0 for j in range(3))]))
    return morceaux


def pose_cubie(p, R):
    """Pose RoboDK d'un cubie (repère socle) à partir de sa position grille et de son orientation."""
    return Mat([[R[0][0], R[0][1], R[0][2], p[0] * P.S],
                [R[1][0], R[1][1], R[1][2], p[1] * P.S],
                [R[2][0], R[2][1], R[2][2], P.h + p[2] * P.S],
                [0, 0, 0, 1]])


# ----------------------------- Objets de la station -----------------------------

def objet(nom, morceaux):
    """Crée un objet à la racine de la station (pose identité)."""
    donnees = []
    for pts, coul in morceaux:
        donnees += [robomath.tr(Mat(pts)), P.COUL[coul]]
    obj = RDK.AddShape(donnees)
    obj.setName(nom)
    return obj


def supprimer(noms=(), prefixe=None):
    for it in RDK.ItemList(robolink.ITEM_TYPE_OBJECT):
        n = it.Name()
        if n in noms or (prefixe and n.startswith(prefixe)):
            it.Delete()


def chercher_fichier_robot():
    maison = os.path.expanduser("~")
    dossiers = [os.path.join(P.DOSSIER_PROJET, "robot"), os.path.join(maison, "Desktop"),
                os.path.join(maison, "Documents", "RoboDK")]
    try:
        dossiers.append(RDK.getParam(robolink.PATH_LIBRARY))
    except Exception:
        pass
    dossiers.append(os.path.join(maison, "RoboDK"))
    for dossier in dossiers:
        if not dossier or not os.path.isdir(dossier):
            continue
        for racine, _, fichiers in os.walk(dossier):
            for f in fichiers:
                nom = f.lower()
                if nom.endswith(".robot") and "meca500" in nom and "r3" in nom:
                    return os.path.join(racine, f)
    return None


def masquer_axes(robot, *reperes):
    """Cache les grosses flèches d'axes : repères (leurs objets restent visibles) et références du robot.
    Dans RoboDK, Alt+/ les réaffiche toutes."""
    for repere in reperes + (robot.Parent(),):
        repere.setVisible(False)
    robot.setVisible(True, robolink.VISIBLE_ROBOT_DEFAULT & ~robolink.VISIBLE_ROBOT_ALL_REFS)


def obtenir_robot():
    robot = RDK.Item("", robolink.ITEM_TYPE_ROBOT)
    if robot.Valid():
        return robot
    chemin = chercher_fichier_robot()
    if chemin:
        robot = RDK.AddFile(chemin)
        if robot.Valid():
            return robot
    raise RuntimeError("Meca500 R3 introuvable. Télécharge-le depuis la bibliothèque RoboDK puis relance.")


def construire_socle_et_cube(robot):
    supprimer(P.NOMS_SCENE, prefixe="Cubie_")
    repere = RDK.Item(P.NOM_REPERE, robolink.ITEM_TYPE_FRAME)
    if not repere.Valid():
        repere = RDK.AddFrame(P.NOM_REPERE, robot.Parent())
    repere.setPose(transl(P.SOCLE_X, P.SOCLE_Y, P.HAUTEUR_SOCLE))
    masquer_axes(robot, repere)

    h = P.h
    L, lm, j = P.LARGEUR_SOCLE / 2, P.LONGUEUR_MORS / 2, P.JEU_SOCLE
    socle = objet("Socle", [
        (boite(-lm, -L, -P.HAUTEUR_SOCLE, lm, L, -j), "socle"),
        (boite(-lm, h + j, -j, lm, h + j + P.EPAISSEUR_MORS, P.HAUTEUR_MORS), "gris"),
        (boite(-lm, -h - j - P.EPAISSEUR_MORS, -j, lm, -h - j, P.HAUTEUR_MORS), "gris"),
    ])
    socle.setParent(repere)
    socle.setPose(robomath.eye(4))

    construire_table(robot)

    cubies = {}
    for p0 in ModeleCube().c:
        it = objet(nom_cubie(p0), morceaux_cubie(p0))
        it.setParent(repere)
        cubies[p0] = it
    return repere, socle, cubies


def pose_table():
    """Repère du point de pose sur la table : tourné pour être face au robot (comme dans poses.py)."""
    angle = math.atan2(P.TABLE_Y, P.TABLE_X)
    return transl(P.TABLE_X, P.TABLE_Y, P.HAUTEUR_TABLE) * rotz(angle)


def construire_table(robot):
    """Plaque de table sous la cellule et repère du point de pose du cube (presenter_faces)."""
    x0, x1, y0, y1, ep = P.TABLE_DESSIN
    table = objet("Table", [(boite(x0, y0, P.HAUTEUR_TABLE - ep, x1, y1, P.HAUTEUR_TABLE), "table")])
    table.setParent(robot.Parent())
    table.setPose(robomath.eye(4))
    repere = RDK.Item(P.NOM_REPERE_TABLE, robolink.ITEM_TYPE_FRAME)
    if not repere.Valid():
        repere = RDK.AddFrame(P.NOM_REPERE_TABLE, robot.Parent())
    repere.setPose(pose_table())
    masquer_axes(robot, repere)
    construire_camera(repere)
    return repere


def pose_camera():
    """Repère de la caméra dans celui de la table : à DISTANCE_CAMERA à droite du cube (-Y),
    à hauteur de son centre ; son Z (axe de visée) regarde le cube (+Y), son Y pointe vers le bas."""
    return Mat([[1, 0, 0, 0],
                [0, 0, 1, -P.DISTANCE_CAMERA],
                [0, -1, 0, P.h],
                [0, 0, 0, 1]])


def construire_camera(repere_table):
    """Représentation 3D de la caméra (boîtier + objectif + pied jusqu'à la table)."""
    repere = RDK.Item(P.NOM_REPERE_CAMERA, robolink.ITEM_TYPE_FRAME)
    if not repere.Valid():
        repere = RDK.AddFrame(P.NOM_REPERE_CAMERA, repere_table)
    repere.setParentStatic(repere_table)
    repere.setPose(pose_camera())
    repere.setVisible(False)                      # repère sans flèches (la caméra reste visible)

    # Dans le repère caméra : Z = vers le cube, Y = vers le bas, X = sur le côté.
    l, hb, prof = P.BOITIER_CAMERA
    o, lo = P.OBJECTIF_CAMERA
    pied = 8.0
    camera = objet("Camera", [
        (boite(-l / 2, -hb / 2, -lo - prof, l / 2, hb / 2, -lo), "camera"),       # boîtier
        (boite(-o / 2, -o / 2, -lo, o / 2, o / 2, 0), "noir"),                     # objectif
        (boite(-pied / 2, hb / 2, -lo - prof / 2 - pied / 2,                       # pied jusqu'à la table
               pied / 2, P.h, -lo - prof / 2 + pied / 2), "gris"),
    ])
    camera.setParent(repere)
    camera.setPose(robomath.eye(4))
    return camera


def construire_pince(robot):
    outil = RDK.Item(P.NOM_OUTIL, robolink.ITEM_TYPE_TOOL)
    if not outil.Valid():
        outil = robot.AddTool(transl(0, 0, P.TCP_Z), P.NOM_OUTIL)
    outil.setPoseTool(transl(0, 0, P.TCP_Z))
    outil.setVisible(True, False)                 # pas de flèches au bout de la pince
    supprimer(P.NOMS_PINCE)

    # Géométries exprimées dans le repère de la BRIDE (Z sort de la bride)
    pieces = []
    if P.FICHIER_CAO_PINCE and os.path.isfile(P.FICHIER_CAO_PINCE):
        cao = RDK.AddFile(P.FICHIER_CAO_PINCE)
        cao.setName("Pince_CAO")
        pieces.append(cao)
    else:
        pieces.append(objet("Pince_plaque", [(boite(-16, -16, 0, 16, 16, P.EPAISSEUR_PLAQUE), "alu")]))
        pieces.append(objet("Pince_corps", [(boite(-P.CORPS_X / 2, -P.CORPS_Y / 2, P.EPAISSEUR_PLAQUE,
                                                   P.CORPS_X / 2, P.CORPS_Y / 2, P.Z_BAS_CORPS), "gris_fonce")]))

    yi = P.ECART_OUVERT / 2
    yo = yi + P.EPAISSEUR_DOIGT
    w = P.LARGEUR_DOIGT / 2
    z_pont = P.Z_BAS_CORPS + P.EPAISSEUR_PONT
    doigts = []
    for nom, sg in (("Doigt_1", 1), ("Doigt_2", -1)):
        y_a, y_b = sorted([sg * 4, sg * yo])
        pts = boite(-w, y_a, P.Z_BAS_CORPS, w, y_b, z_pont)                 # pont sous le boîtier
        y_a, y_b = sorted([sg * yi, sg * yo])
        pts += boite(-w, y_a, z_pont, w, y_b, P.Z_BOUT_DOIGTS)              # grand doigt
        d = objet(nom, [(pts, "pla")])
        pieces.append(d)
        doigts.append((d, sg))

    # Les enfants d'un outil sont positionnés par rapport au TCP (pas à la bride) :
    # la bride vue depuis le TCP = transl(0, 0, -TCP_Z).
    for p in pieces:
        p.setParent(outil)
        p.setPose(transl(0, 0, -P.TCP_Z))
    return outil, pieces, doigts
