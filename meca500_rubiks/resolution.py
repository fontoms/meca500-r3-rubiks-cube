# -*- coding: utf-8 -*-
"""
Résolution du cube : cubestring → solution (solveur « twophase » de Kociemba) → mouvements du robot.

    from meca500_rubiks import resolution
    coups = resolution.resoudre(robot, cubestring)        # calcule puis exécute (robot connecté)

CUBESTRING (54 lettres, format Kociemba, fourni par le groupe caméra) : les faces dans l'ordre
U R F D L B, 9 lettres par face, chaque lettre = la face dont la couleur est celle de ce centre.
Il décrit le cube TEL QU'IL EST POSÉ DANS LE SOCLE :
    U = dessus, D = dessous, F = face tournée vers le robot, B = face opposée au robot,
    R = face à droite du robot, L = face à gauche du robot.
Exemple, cube résolu : "UUUUUUUUURRRRRRRRRFFFFFFFFFDDDDDDDDDLLLLLLLLLBBBBBBBBB".

Le robot ne sait tourner que les 2 couches du haut (le socle tient celle du bas) : pour chaque coup,
il amène la face à tourner EN BAS (bascules / rotations du cube entier), puis tourne les 2 couches du
haut. L'orientation du cube est suivie d'un coup à l'autre (on ne le remet pas droit) : 1 à 3 prises
par coup. Les tables du solveur (~80 Mo) sont dans solveur_tables/ : python installer_solveur.py.
"""
import contextlib
import io
import os
import re

from .modele_cube import DIR_FACE, FACE_DIR, chemin_vers_bas, cross, mul, mulm, rot_quart, transp
from .mouvements import ETAPES_PHOTO, basculer, tourner_cube, tourner_haut

DOSSIER_PROJET = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOSSIER_TABLES = os.path.join(DOSSIER_PROJET, "solveur_tables")   # contient twophase/ (les tables)
TABLES = ["co_classidx", "co_rep", "co_sym", "conj_twist", "conj_ud_edges", "fs_classidx", "fs_rep", "fs_sym",
          "move_corners", "move_d_edges", "move_flip", "move_slice_sorted", "move_twist", "move_u_edges",
          "move_ud_edges", "phase1_prun", "phase2_cornsliceprun", "phase2_edgemerge", "phase2_prun"]

MAX_COUPS = 20          # le solveur s'arrête dès qu'il trouve une solution de 20 coups ou moins
TEMPS_MAX = 15.0        # s : au-delà, il renvoie la meilleure solution trouvée

CUBE_RESOLU = "".join(f * 9 for f in "URFDLB")


class ErreurResolution(RuntimeError):
    pass


# ----------------------------- Solveur -----------------------------

def tables_installees():
    dossier = os.path.join(DOSSIER_TABLES, "twophase")
    return all(os.path.isfile(os.path.join(dossier, t)) for t in TABLES)


_solveur = None


def charger_solveur():
    """Importe twophase.solver. Il lit ses tables dans ./twophase au moment de l'import : on se place
    donc dans solveur_tables/ le temps de l'import."""
    global _solveur
    if _solveur is not None:
        return _solveur
    if not tables_installees():
        raise ErreurResolution("Tables du solveur absentes : lance  python installer_solveur.py")
    dossier = os.getcwd()
    os.chdir(DOSSIER_TABLES)
    try:
        with contextlib.redirect_stdout(io.StringIO()):          # « loading … table » × 15
            import twophase.solver as sv
    except ImportError:
        raise ErreurResolution("Librairie RubikTwoPhase absente : lance  python installer_solveur.py")
    finally:
        os.chdir(dossier)
    _solveur = sv
    return sv


def verifier_cubestring(cubestring):
    """Renvoie le cubestring nettoyé (majuscules, sans espaces) ou lève ErreurResolution."""
    s = re.sub(r"\s", "", cubestring).upper()
    if len(s) != 54 or set(s) - set("URFDLB"):
        raise ErreurResolution("cubestring invalide : 54 lettres parmi U R F D L B attendues (%d reçues)" % len(s))
    for f in "URFDLB":
        if s.count(f) != 9:
            raise ErreurResolution("cubestring invalide : %d fois « %s » au lieu de 9" % (s.count(f), f))
    centres = s[4::9]
    if centres != "URFDLB":
        raise ErreurResolution("cubestring invalide : centres %s au lieu de URFDLB (ordre des faces U R F D L B)"
                               % centres)
    return s


def lire_solution(texte):
    """« R1 U3 F2 (3f) » → [("R", 1), ("U", -1), ("F", 2)] (1 = quart de tour horaire, 3 = anti-horaire)."""
    coups = []
    for jeton in texte.split():
        if jeton.startswith("("):                 # « (20f) » : nombre de coups
            continue
        m = re.fullmatch(r"([URFDLB])([123])", jeton)
        if not m:
            raise ErreurResolution("réponse du solveur incompréhensible : %s" % texte)
        coups.append((m.group(1), {1: 1, 2: 2, 3: -1}[int(m.group(2))]))
    return coups


def calculer_solution(cubestring, max_coups=MAX_COUPS, temps_max=TEMPS_MAX):
    """Solution (liste de (face, k)) pour amener le cube décrit par `cubestring` à l'état résolu."""
    s = verifier_cubestring(cubestring)
    texte = charger_solveur().solve(s, max_coups, temps_max)
    if texte.lower().startswith("error") or "(" not in texte:
        raise ErreurResolution("le solveur refuse ce cube (couleurs mal lues ?) : %s" % texte)
    return lire_solution(texte)


# ----------------------------- Cube tourné en entier (presenter_faces) -----------------------------

# Haut de chaque face quand on la regarde de l'extérieur (convention Kociemba) : les 9 cases sont lues
# ligne par ligne, de gauche à droite, en commençant en haut à gauche.
HAUT_FACE = {"U": "B", "R": "U", "F": "U", "D": "F", "L": "U", "B": "U"}


def _cases():
    """[(position, normale)] des 54 cases dans l'ordre du cubestring (repère du socle, centre du cube)."""
    cases = []
    for f in "URFDLB":
        n, u = DIR_FACE[f], DIR_FACE[HAUT_FACE[f]]
        r = cross(tuple(-v for v in n), u)
        for i in range(3):
            for j in range(3):
                cases.append((tuple(n[a] + u[a] * (1 - i) + r[a] * (j - 1) for a in range(3)), n))
    return cases


def tourner_cubestring(cubestring, rotation):
    """Cubestring du même cube après l'avoir tourné EN ENTIER de `rotation` (matrice 3x3 entière,
    repère du socle). Les lettres sont renommées d'après les nouveaux centres (format Kociemba)."""
    s = verifier_cubestring(cubestring)
    cases = _cases()
    indice = {c: i for i, c in enumerate(cases)}
    nouveau = [""] * 54
    for i, (p, n) in enumerate(cases):
        nouveau[indice[(mul(rotation, p), mul(rotation, n))]] = s[i]
    renomme = {nouveau[9 * k + 4]: f for k, f in enumerate("URFDLB")}     # couleur du centre → face
    return "".join(renomme[c] for c in nouveau)


ROTATIONS_TABLE = {"tourner_gauche": (2, 1), "tourner_droite": (2, -1), "basculer_droite": (0, 1),
                   "basculer_gauche": (0, -1)}


def orientations_presenter_faces():
    """Orientation du cube (matrice 3x3, par rapport au départ) à chaque photo de presenter_faces,
    puis à la fin (cube revenu dans le socle). Liste de (face photographiée ou None, orientation)."""
    o = rot_quart(0, 0)
    resultat = [("droite", o)]
    for mouvement, face in ETAPES_PHOTO:
        o = mulm(rot_quart(*ROTATIONS_TABLE[mouvement]), o)
        resultat.append((face, o))
    return resultat


def cubestring_apres_presenter_faces(cubestring_avant):
    """presenter_faces remet le cube dans le socle TOURNÉ par rapport au départ. Si le cubestring a été
    construit avec les faces nommées comme au départ (dessus = U, vers le robot = F…), cette fonction
    donne celui du cube tel qu'il est dans le socle APRÈS presenter_faces, à passer au solveur."""
    return tourner_cubestring(cubestring_avant, orientations_presenter_faces()[-1][1])


def vue_camera(orientation):
    """Pour une photo : (face au centre de l'image, face en haut de l'image, face à droite de l'image),
    faces nommées comme AU DÉPART. Caméra à droite du cube (-Y), qui regarde vers +Y, haut = +Z :
    la droite de l'image est +X (loin du robot)."""
    retour = transp(orientation)
    nom = {"U": "dessus", "D": "dessous", "F": "vers_robot", "B": "loin_du_robot", "R": "droite", "L": "gauche"}
    return tuple(nom[FACE_DIR[mul(retour, d)]] for d in ((0, -1, 0), (0, 0, 1), (1, 0, 0)))


# ----------------------------- Traduction en mouvements du robot -----------------------------

def plan_robot(coups):
    """Mouvements du robot pour jouer `coups` : liste de (fonction, argument), fonction parmi
    "basculer" (±1, autour de X), "tourner_cube" (±90°) et "tourner_haut" (±90°).

    On suit l'orientation du cube : pour chaque coup, on amène la face en bas par le plus court chemin,
    puis tourner la face du bas de k quarts (sens horaire vu de dessous) revient, à l'orientation près,
    à tourner les 2 couches du haut de -k quarts autour de la verticale.
    """
    orientation = rot_quart(0, 0)
    etapes = []
    for face, k in coups:
        for op, a in chemin_vers_bas(mul(orientation, DIR_FACE[face])):
            if op == "B":
                etapes.append(("basculer", a))
                orientation = mulm(rot_quart(0, a), orientation)
            else:
                etapes.append(("tourner_cube", 90 * a))
                orientation = mulm(rot_quart(2, a), orientation)
        for q in ([-1, -1] if k == 2 else [-k]):           # demi-tour : 2 quarts (câble : J6 limité)
            etapes.append(("tourner_haut", 90 * q))
            orientation = mulm(rot_quart(2, q), orientation)
    return etapes


MOUVEMENTS_ROBOT = {"basculer": basculer, "tourner_cube": tourner_cube, "tourner_haut": tourner_haut}


def decrire(etape):
    nom, arg = etape
    if nom == "basculer":
        return "basculer_%s" % ("droite" if arg > 0 else "gauche")
    return "%s_%s" % (nom, "gauche" if arg > 0 else "droite")


def executer(robot, etapes, afficher=print):
    """Fait jouer les étapes au robot (vrai robot ou simulation), une par une."""
    for i, etape in enumerate(etapes, 1):
        afficher("  %2d/%d  %s" % (i, len(etapes), decrire(etape)))
        nom, arg = etape
        MOUVEMENTS_ROBOT[nom](robot, arg)


def ecrire(coups):
    return " ".join(f + {1: "", -1: "'", 2: "2"}[k] for f, k in coups) or "(déjà résolu)"


def resoudre(robot, cubestring, afficher=print):
    """Calcule la solution du cube décrit par `cubestring` et la fait jouer au robot. Renvoie les coups."""
    coups = calculer_solution(cubestring)
    etapes = plan_robot(coups)
    afficher("Solution (%d coups) : %s — %d mouvements du robot" % (len(coups), ecrire(coups), len(etapes)))
    executer(robot, etapes, afficher)
    return coups
