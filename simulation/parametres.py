# -*- coding: utf-8 -*-
"""
Paramètres de la simulation RoboDK : dimensions de la scène, réglages des modes.

C'est LE fichier à modifier pour changer la pince, les doigts, le socle ou le cube.
TCP, SOCLE et COTE_CUBE doivent rester identiques à ceux de ../meca500_rubiks/reglages.py
(la simulation refuse de démarrer sinon).

Les dimensions de la pince / de l'extension sont APPROXIMATIVES : remplace-les par les tiennes.
Aucune dépendance à RoboDK ici : ce module s'importe aussi dans les tests.
"""
import os
import sys

# ======================= Dossiers =======================

DOSSIER_SIMULATION = os.path.dirname(os.path.abspath(__file__))
DOSSIER_PROJET = os.path.dirname(DOSSIER_SIMULATION)
DOSSIER_JOURNAL = os.path.join(DOSSIER_PROJET, "journal")
DOSSIER_PROGRAMMES = os.path.join(DOSSIER_SIMULATION, "programmes")
if DOSSIER_PROJET not in sys.path:
    sys.path.insert(0, DOSSIER_PROJET)          # pour importer meca500_rubiks

# ======================= Lancement de scene.py =======================

MODE = "installer"                # "installer", "tests" ou "resolution" (voir scene.py)

VITESSE_SIMULATION = 1.0          # 1 = temps réel (RoboDK accélère souvent ×5 par défaut)

# MODE "tests" : mouvements à enchaîner (dans l'ordre). Chaque mouvement part de la position
# d'attente (pince verticale au-dessus du cube) et y revient, cube reposé dans le socle.
#   "prise"                       : saisir, sortir de 30 mm, reposer (le plus simple, à faire en 1er)
#   "rotation+90" / "-90" / "180" : tourner le cube entier autour de la verticale
#   "couche+90"   / "-90" / "180" : tourner la couche du bas (la pince tient les 2 du haut)
#   "bascule+90"  / "bascule-90"  : basculer le cube d'un quart de tour
TESTS = ["prise", "rotation+90", "couche+90", "couche-90", "bascule+90", "bascule-90"]
VERIFIER_COLLISIONS = True
PAUSE_ENTRE_TESTS = 1.0           # s

# MODE "resolution" :
# MELANGE  : coups appliqués instantanément au cube virtuel ("R U R' U'" ou un nombre → aléatoire).
# SOLUTION : coups exécutés par le robot. Vide → kociemba si installé, sinon inverse du mélange.
MELANGE = "R U F' L2 D B'"
SOLUTION = ""
GRAINE_ALEATOIRE = None

ENREGISTRER_PROJET = True
NOM_PROJET = "Rubiks_Meca500.rdk"   # dans DOSSIER_PROJET
JOURNAL = "Rubiks_Meca500_journal.txt"

# ======================= Socle =======================
# Repère placé au centre du dessus du socle.

SOCLE_X, SOCLE_Y = 170.0, 0.0     # position dans le repère de base du robot (mm)
HAUTEUR_SOCLE = 40.0
LARGEUR_SOCLE = 90.0
EPAISSEUR_MORS = 8.0
HAUTEUR_MORS = 14.0               # mors sur les faces ±Y du cube (tiennent la couche du bas)
LONGUEUR_MORS = 45.0              # socle + mors selon X, plus courts que le cube (57) : passage des doigts
JEU_SOCLE = 0.7                   # jeu entre le cube et les mors

# ======================= Cube =======================

COTE_CUBE = 57.0

# ======================= Pince MEGP 25E (forme simplifiée) =======================

EPAISSEUR_PLAQUE = 6.0
CORPS_X, CORPS_Y, CORPS_Z = 24.0, 34.0, 40.0
COURSE_MACHOIRE = 3.0             # course par mâchoire (Mecademic)
FICHIER_CAO_PINCE = ""            # fichier CAO (STEP/STL) de la pince + extension, optionnel

# Extension imprimée 3D (une par mâchoire : pont sous le boîtier + grand doigt)
LARGEUR_DOIGT = 50.0              # presque la largeur du cube
EPAISSEUR_DOIGT = 6.0
EPAISSEUR_PONT = 8.0
GARDE_HAUT = 12.0                 # dessous de l'extension → dessus du cube saisi
GARDE_BAS = HAUTEUR_MORS + 2.0    # bout des doigts → bas du cube (> HAUTEUR_MORS)
MARGE_COUCHE = 3.0                # tourner_couche : bout des doigts 3 mm au-dessus de la couche du bas
ECART_OUVERT = COTE_CUBE + 2 * COURSE_MACHOIRE - 2.0   # écart entre doigts, pince ouverte

# ======================= Mouvements (MODE "tests" / "resolution") =======================

LEVEE = 30.0                      # hauteur de sortie du socle
DEGAGEMENT = 40.0                 # doigts au-dessus du cube, pince verticale
ANGLE_PRISE_BASCULE = 45.0        # la pince saisit à -45° et repose à +45° (ou l'inverse)
DECALAGE_BASCULE = 4.0            # cube tenu 4 mm plus près du bout des doigts pendant la bascule
RECUL_BASCULE = 40.0              # approche / dégagement le long de l'axe de la pince inclinée
VITESSE_LIN = 35.0
VITESSE_ART = 45.0

# ======================= Valeurs dérivées (ne pas modifier) =======================

h = COTE_CUBE / 2                                    # demi-côté du cube
S = COTE_CUBE / 3                                    # côté d'un cubie
Z_BAS_CORPS = EPAISSEUR_PLAQUE + CORPS_Z             # dessous du boîtier (repère bride)
TCP_Z = Z_BAS_CORPS + EPAISSEUR_PONT + GARDE_HAUT + h  # TCP au centre du cube saisi
DOIGT_SOUS_TCP = h - GARDE_BAS                       # bout des doigts sous le TCP
Z_BOUT_DOIGTS = TCP_Z + DOIGT_SOUS_TCP               # bout des doigts (repère bride)
SERRAGE = ECART_OUVERT / 2 - (h + 0.2)               # course simulée de chaque doigt

# Hauteurs du TCP dans le repère du socle
Z_PRISE = h                                          # cube entier
Z_PRISE_HAUT = S + MARGE_COUCHE + DOIGT_SOUS_TCP     # 2 couches du haut seulement
Z_APPROCHE = COTE_CUBE + DEGAGEMENT + DOIGT_SOUS_TCP # doigts DEGAGEMENT mm au-dessus du cube

# ======================= Noms et couleurs dans la station =======================

NOM_REPERE = "Socle_repere"
NOM_OUTIL = "MEGP 25E"
NOMS_SCENE = ["Socle", "Table", "Camera", "Cube", "Cube_bas", "Cube_haut"]
NOMS_PINCE = ["Pince_plaque", "Pince_corps", "Pince_CAO", "Doigt_1", "Doigt_2"]

COUL = {
    "noir": [0.05, 0.05, 0.05, 1], "gris": [0.6, 0.6, 0.62, 1], "gris_fonce": [0.3, 0.3, 0.33, 1],
    "pla": [0.95, 0.55, 0.15, 1], "alu": [0.8, 0.8, 0.82, 1], "socle": [0.45, 0.35, 0.25, 1],
    "table": [0.85, 0.85, 0.8, 1], "camera": [0.15, 0.15, 0.17, 1],
    "U": [0.95, 0.95, 0.95, 1], "D": [1.0, 0.85, 0.0, 1], "F": [0.0, 0.6, 0.2, 1],
    "B": [0.0, 0.3, 0.8, 1], "R": [0.85, 0.1, 0.1, 1], "L": [1.0, 0.45, 0.0, 1],
}

# ======================= Table et caméra (presenter_faces) =======================
# Le cube est posé sur la table, à droite du socle (= TABLE dans ../meca500_rubiks/reglages.py).
# Sur la table, il est tourné pour rester face au robot (angle = direction robot → cube).

TABLE_X, TABLE_Y = 170.0, -110.0  # point de pose sur la table (repère de base du robot, mm)
HAUTEUR_TABLE = 0.0               # dessus de la table = dessous de la base du robot
NOM_REPERE_TABLE = "Table_repere"
TABLE_DESSIN = (-120.0, 300.0, -260.0, 160.0, 6.0)   # plaque dessinée : x min, x max, y min, y max, épaisseur

# Caméra (représentation 3D seulement) : à droite du cube posé sur la table, à hauteur de son
# centre, elle regarde le cube (donc vers le socle).
NOM_REPERE_CAMERA = "Camera_repere"
DISTANCE_CAMERA = 250.0           # mm entre l'objectif et le centre du cube
BOITIER_CAMERA = (60.0, 40.0, 50.0)   # largeur, hauteur, profondeur du boîtier (mm)
OBJECTIF_CAMERA = (24.0, 20.0)        # côté, longueur de l'objectif (mm)
PAUSE_PHOTO = 1.0                 # s de pause simulée à chaque photo
