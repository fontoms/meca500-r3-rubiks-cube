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
import functools
import heapq
import io
import os
import re
import time

from .briques import preparer, remonter, tourner_pince
from .duree import Chronometre
from .modele_cube import DIR_FACE, FACE_DIR, chemin_vers_bas, cross, mul, mulm, rot_quart, transp
from .mouvements import ETAPES_PHOTO, basculer, pose_lacher, tourner_cube, tourner_haut
from .poses import pose
from .reglages import H_ATTENTE, ROTATION_BASCULE, ROTATIONS_PINCE

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


def _toutes_les_rotations():
    """Les 24 orientations d'un cube (matrices 3x3 entières), l'identité en premier."""
    vues, file = [], [rot_quart(0, 0)]
    while file:
        m = file.pop(0)
        if m not in vues:
            vues.append(m)
            file += [mulm(rot_quart(axe, 1), m) for axe in range(3)]
    return vues


ROTATIONS_CUBE = _toutes_les_rotations()
BUDGET_RECHERCHE = 10.0     # s : temps de calcul max pour chercher la solution la plus rapide à jouer


def meilleure_solution(cubestring, budget=BUDGET_RECHERCHE, rotations=None):
    """(coups, étapes) : la solution la plus RAPIDE À JOUER pour le robot, pas forcément la plus courte.

    Le solveur ne trouve qu'une solution parmi beaucoup d'autres, et ne sait rien du robot. On lui
    donne donc le même cube vu sous plusieurs orientations (comme si on le tournait en entier) : il
    trouve à chaque fois une autre solution, qu'on traduit pour le cube réel ; on garde celle dont le
    plan du robot (plan_robot) est le plus rapide. On s'arrête après `budget` secondes de calcul.
    """
    s = verifier_cubestring(cubestring)
    debut = time.time()
    meilleur = None
    for rotation in (rotations or ROTATIONS_CUBE):
        reste = budget - (time.time() - debut)
        if meilleur is not None and reste <= 0:
            break
        coups_tournes = calculer_solution(tourner_cubestring(s, rotation), temps_max=max(reste, 1.0))
        retour = transp(rotation)                 # face du cube tourné → face du cube réel
        coups = [(FACE_DIR[mul(retour, DIR_FACE[f])], k) for f, k in coups_tournes]
        etapes = plan_robot(coups)
        if meilleur is None or duree_plan(etapes) < duree_plan(meilleur[1]):
            meilleur = (coups, etapes)
    return meilleur


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
#
# Une ÉTAPE du plan est un triplet (nom, argument, prise) :
#   ("tourner_haut", angle, prise)   2 couches du haut tournées de angle (±90, ±180)
#   ("tourner_cube", angle, prise)   cube entier tourné de angle autour de la verticale (±90, ±180)
#   ("basculer", sens, prise)        bascule (±1, autour de X), pince tournée de prise = ±90°
#   ("tourner_pince", vers, depuis)  pince ouverte, en l'air : tourne de `depuis` à `vers`
# prise = rotation de la pince quand elle saisit le cube ; elle le lâche tournée de prise + angle.
#
# LIAISONS (voir briques.py) : après chaque prise, la pince lâche le cube et RESTE EN BAS, ouverte autour
# de lui (`bas` = (hauteur, inclinaison, recul) de la pince, voir mouvements.pose_lacher). La prise suivante
# part directement de là : autre hauteur (tourner_cube / tourner_haut) ou pince penchée (basculer), sans
# remonter à la position d'attente. On ne remonte que pour tourner la pince en l'air, et à la fin.
# Chaque fonction ci-dessous joue une étape en partant de `bas` (None = position d'attente) et renvoie
# le nouveau `bas`.

def _tourner_pince(robot, vers, depuis, bas=None):
    remonter(robot, bas, depuis)
    tourner_pince(robot, vers, depuis)
    return None


def _tourner_cube(robot, angle, prise, bas=None):
    tourner_cube(robot, angle, prise=prise, depuis=bas, remonter=False)
    return pose_lacher("tourner_cube", angle)


def _tourner_haut(robot, angle, prise, bas=None):
    tourner_haut(robot, angle, prise=prise, depuis=bas, remonter=False)
    return pose_lacher("tourner_haut", angle)


def _basculer(robot, sens, prise, bas=None):
    basculer(robot, sens, prise=prise, depuis=bas, remonter=False)
    return pose_lacher("basculer", sens)


def bas_apres(etape):
    """Où reste la pince (ouverte, en bas) après l'étape jouée par executer ; None : position d'attente."""
    nom, arg, _ = etape
    return None if nom == "tourner_pince" else pose_lacher(nom, arg)


MOUVEMENTS_ROBOT = {"tourner_pince": _tourner_pince, "tourner_cube": _tourner_cube,
                    "tourner_haut": _tourner_haut, "basculer": _basculer}


def rotation_pince_apres(etape):
    """Rotation de la pince (position d'attente) à la fin de l'étape."""
    nom, arg, prise = etape
    if nom == "tourner_pince":
        return arg
    return prise if nom == "basculer" else prise + arg


def _chronometre(bas, rotation):
    """Chronomètre préparé, pince ouverte à la hauteur `bas` (None = position d'attente), temps à 0."""
    robot = Chronometre()
    preparer(robot)
    hauteur, inclinaison, recul = (H_ATTENTE, 0.0, 0.0) if bas is None else bas
    robot.MovePose(*pose(hauteur, inclinaison, rotation, recul))
    robot.temps = 0.0
    return robot


@functools.lru_cache(maxsize=None)
def duree_etape(etape, bas=None):
    """Durée estimée (s) d'une étape, pince partant de la hauteur `bas` (None = position d'attente).
    Pour tourner_pince, prise = rotation de départ."""
    nom, arg, prise = etape
    robot = _chronometre(bas, prise)
    MOUVEMENTS_ROBOT[nom](robot, arg, prise, bas)
    return robot.temps


@functools.lru_cache(maxsize=None)
def duree_remontee(bas, rotation):
    """Durée estimée (s) pour remonter de `bas` à la position d'attente (0 si la pince y est déjà)."""
    robot = _chronometre(bas, rotation)
    remonter(robot, bas, rotation)
    return robot.temps


def fin_en_bas(etapes):
    """(bas, rotation de la pince) à la fin des étapes jouées par executer, avant la remontée finale."""
    if not etapes:
        return None, 0.0
    return bas_apres(etapes[-1]), rotation_pince_apres(etapes[-1])


def duree_plan(etapes):
    """Durée estimée (s) du plan joué par executer (liaisons rapides et remontée finale comprises)."""
    total, bas = 0.0, None
    for etape in etapes:
        total += duree_etape(etape, bas)
        bas = bas_apres(etape)
    return total + duree_remontee(*fin_en_bas(etapes))


def nombre_de_prises(etapes):
    return sum(1 for nom, _, _ in etapes if nom != "tourner_pince")


FACE_OPPOSEE = {"U": "D", "D": "U", "R": "L", "L": "R", "F": "B", "B": "F"}
ANGLES = (-180, -90, 90, 180)
BAS = (0, 0, -1)


def _cle(orientation):
    return tuple(tuple(ligne) for ligne in orientation)


def _groupes(coups):
    """Coups regroupés quand ils peuvent se jouer dans n'importe quel ordre : deux coups de suite
    sur des faces opposées (ex. U puis D') commutent."""
    groupes, i = [], 0
    while i < len(coups):
        n = 2 if i + 1 < len(coups) and coups[i + 1][0] == FACE_OPPOSEE[coups[i][0]] else 1
        groupes.append(tuple(coups[i:i + n]))
        i += n
    return groupes


def _transitions(groupe, g, faits, cle, pince):
    """Étapes possibles depuis un état (g, faits, orientation, pince) : (étape, nouvel état sans `bas`)."""
    orientation = [list(ligne) for ligne in cle]
    for vers in ROTATIONS_PINCE:                                   # tourner la pince en l'air
        if vers != pince:
            yield ("tourner_pince", vers, pince), (g, faits, cle, vers)
    for angle in ANGLES:                                           # tourner le cube entier
        if pince + angle in ROTATIONS_PINCE:
            o = mulm(rot_quart(2, angle // 90), orientation)
            yield ("tourner_cube", angle, pince), (g, faits, _cle(o), pince + angle)
    if abs(pince) == ROTATION_BASCULE:                             # basculer
        for sens in (1, -1):
            o = mulm(rot_quart(0, sens), orientation)
            yield ("basculer", sens, pince), (g, faits, _cle(o), pince)
    for j, (face, k) in enumerate(groupe):                         # jouer un coup du groupe (face en bas)
        if faits & (1 << j) or mul(orientation, DIR_FACE[face]) != BAS:
            continue
        nouveaux = faits | (1 << j)
        suite = (g + 1, 0) if nouveaux == (1 << len(groupe)) - 1 else (g, nouveaux)
        for angle in ((-180, 180) if k == 2 else (-90 * k,)):
            if pince + angle in ROTATIONS_PINCE:
                o = mulm(rot_quart(2, angle // 90), orientation)
                yield ("tourner_haut", angle, pince), suite + (_cle(o), pince + angle)


def plan_robot(coups, rotation_pince=0.0, finir_a_zero=True):
    """Mouvements du robot (liste d'étapes, voir plus haut) qui jouent `coups` LE PLUS VITE POSSIBLE.

    Le robot ne tourne que la face du bas (en tournant les 2 couches du haut, le socle tient celle du
    bas) : tourner la face du bas de k quarts (sens horaire vu de dessous) revient, à l'orientation près,
    à tourner les 2 couches du haut de -k quarts. Avant chaque coup, il faut donc amener la face en bas
    (bascules, rotations du cube entier).

    Recherche du plus court chemin (algorithme de Dijkstra) : un ÉTAT est (coups déjà joués,
    orientation du cube, rotation de la pince, pince restée en bas ou non) ; passer d'un état à un autre
    = une étape, qui coûte sa durée estimée (elle part d'en bas, voir LIAISONS).
    On obtient la suite d'étapes la plus rapide, en choisissant :
      - comment amener chaque face en bas (bascule à gauche ou à droite, tourner le cube avant…) ;
      - la rotation de la pince à chaque prise (-90°, 0°, +90°), pour ne pas la remettre à 0° à chaque fois ;
      - l'ordre de deux coups sur des faces opposées (ils commutent) ;
      - le sens des demi-tours (+180° ou -180°, en une seule prise) ;
      - des enchaînements où la pince n'a pas besoin de remonter entre deux prises.
    rotation_pince : rotation de la pince au départ ; finir_a_zero : remettre la pince à 0° à la fin.
    """
    groupes = _groupes(coups)
    depart = (0, 0, _cle(rot_quart(0, 0)), rotation_pince, None)
    meilleur, precedent = {depart: 0.0}, {}
    tas, compteur, fin = [(0.0, 0, depart)], 1, None
    while tas:
        cout, _, etat = heapq.heappop(tas)
        if cout > meilleur[etat]:
            continue                                               # déjà atteint plus vite
        g, faits, cle, pince, bas = etat
        if g == len(groupes):
            if not finir_a_zero or pince == 0.0:
                if bas is None:
                    fin = etat
                    break
                suivants = [(None, (g, faits, cle, pince))]        # remontée finale (pas une étape)
            else:
                suivants = [(("tourner_pince", 0.0, pince), (g, faits, cle, 0.0))]
        else:
            suivants = _transitions(groupes[g], g, faits, cle, pince)
        for etape, nouvel in suivants:
            if etape is None:
                c = cout + duree_remontee(bas, pince)
                nouvel += (None,)
            else:
                c = cout + duree_etape(etape, bas)
                nouvel += (bas_apres(etape),)
            if c < meilleur.get(nouvel, float("inf")) - 1e-9:
                meilleur[nouvel], precedent[nouvel] = c, (etat, etape)
                heapq.heappush(tas, (c, compteur, nouvel))
                compteur += 1
    etapes = []
    while fin != depart:
        fin, etape = precedent[fin]
        if etape is not None:
            etapes.append(etape)
    return etapes[::-1]


def plan_simple(coups):
    """Plan d'avant l'optimisation, gardé pour comparer : face amenée en bas par le plus court chemin,
    demi-tour en 2 quarts, pince remise à 0° après chaque mouvement."""
    orientation = rot_quart(0, 0)
    etapes = []

    def ajouter(nom, arg, prise):
        etapes.append((nom, arg, prise))
        fin = rotation_pince_apres(etapes[-1])
        if fin != 0.0:
            etapes.append(("tourner_pince", 0.0, fin))

    for face, k in coups:
        for op, a in chemin_vers_bas(mul(orientation, DIR_FACE[face])):
            if op == "B":
                etapes.append(("tourner_pince", ROTATION_BASCULE, 0.0))
                ajouter("basculer", a, ROTATION_BASCULE)
                orientation = mulm(rot_quart(0, a), orientation)
            else:
                ajouter("tourner_cube", 90 * a, 0.0)
                orientation = mulm(rot_quart(2, a), orientation)
        for q in ([-1, -1] if k == 2 else [-k]):
            ajouter("tourner_haut", 90 * q, 0.0)
            orientation = mulm(rot_quart(2, q), orientation)
    return etapes


def decrire(etape):
    nom, arg, prise = etape
    if nom == "tourner_pince":
        return "tourner_pince  %+.0f° -> %+.0f°" % (prise, arg)
    if nom == "basculer":
        texte = "basculer_%s" % ("droite" if arg > 0 else "gauche")
    else:
        texte = "%s_%s" % (nom, "demi_tour" if abs(arg) == 180 else ("gauche" if arg > 0 else "droite"))
    return "%-24s (pince %+.0f°)" % (texte, prise)


def executer(robot, etapes, afficher=print, apres_etape=None):
    """Fait jouer les étapes au robot (vrai robot ou simulation), une par une, avec les liaisons rapides
    (voir LIAISONS), puis remonte la pince en position d'attente.
    apres_etape(i, etape) : appelée après chaque étape (la simulation y vérifie le cube)."""
    bas = None
    for i, etape in enumerate(etapes, 1):
        afficher("  %2d/%d  %s" % (i, len(etapes), decrire(etape)))
        nom, arg, prise = etape
        bas = MOUVEMENTS_ROBOT[nom](robot, arg, prise, bas)
        if apres_etape is not None:
            apres_etape(i, etape)
    remonter(robot, bas, rotation_pince_apres(etapes[-1]) if etapes else 0.0)


def ecrire(coups):
    return " ".join(f + {1: "", -1: "'", 2: "2"}[k] for f, k in coups) or "(déjà résolu)"


def resoudre(robot, cubestring, afficher=print):
    """Calcule la solution du cube décrit par `cubestring` et la fait jouer au robot. Renvoie les coups."""
    coups, etapes = meilleure_solution(cubestring)
    afficher("Solution (%d coups) : %s — %d prises du robot, ~%.0f s"
             % (len(coups), ecrire(coups), nombre_de_prises(etapes), duree_plan(etapes)))
    executer(robot, etapes, afficher)
    return coups
