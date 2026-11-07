# -*- coding: utf-8 -*-
"""
Simulation RoboDK : Meca500 R3 + pince MEGP 25E avec doigts longs (impression 3D)

Séquence :
  1. la pince descend sur le cube posé dans le socle et le saisit en entier,
  2. elle le sort du socle,
  3. elle le bascule de 90° (vers le haut ou vers le bas, voir SENS_BASCULE),
  4. elle le repose dans le socle, s'ouvre et se dégage.

Le script construit toute la scène en 3D (socle, cube coloré, pince + doigts)
puis enregistre le projet sur le Bureau.

Orientation : les doigts serrent les faces avant/arrière du cube (axe X du socle),
les mors du socle tiennent les faces gauche/droite (axe Y). Le cube bascule autour
de l'axe des doigts, ce qui garde la pince à portée du Meca500 dans les deux sens.

Tous les réglages sont dans la section PARAMÈTRES. Les dimensions de la pince et
des doigts sont APPROXIMATIVES : remplace-les par celles de tes pièces.
"""

import os
from robodk.robolink import *     # API RoboDK
from robodk.robomath import *     # transl, rotx, rotz, Mat...

# ======================= PARAMÈTRES (à adapter) =======================

# --- Socle (repère placé au centre du dessus du socle) ---
SOCLE_X, SOCLE_Y = 170.0, 0.0     # position dans le repère de base du robot (mm)
HAUTEUR_SOCLE = 40.0
LARGEUR_SOCLE = 90.0
EPAISSEUR_MORS = 8.0
HAUTEUR_MORS = 14.0               # mors sur les faces ±Y du cube

# --- Cube ---
COTE_CUBE = 57.0

# --- Pince MEGP 25E (forme simplifiée) ---
EPAISSEUR_PLAQUE = 6.0
CORPS_X, CORPS_Y, CORPS_Z = 24.0, 34.0, 40.0
COURSE_MACHOIRE = 3.0             # course par mâchoire (Mecademic)

# --- Doigts longs imprimés en 3D ---
LARGEUR_DOIGT = 20.0
EPAISSEUR_DOIGT = 5.0
EPAISSEUR_PONT = 5.0
GARDE_HAUT = 5.0                  # espace entre le dessus du cube et le boîtier
GARDE_BAS = 4.0                   # les doigts s'arrêtent à 4 mm du bas du cube
ECART_OUVERT = COTE_CUBE + 2 * COURSE_MACHOIRE - 2.0   # écart pince ouverte

FICHIER_CAO_PINCE = ""            # fichier CAO officiel (STEP/STL), optionnel

# --- Mouvement ---
SENS_BASCULE = +1                 # +1 ou -1 : bascule vers un côté ou vers l'autre
ANGLE_BASCULE = 90.0
LEVEE = 30.0                      # hauteur de sortie du socle
DEGAGEMENT = 40.0                 # approche au-dessus du cube / dégagement final
VITESSE_LIN = 50.0
VITESSE_ART = 60.0

# --- Projet ---
ENREGISTRER_PROJET = True
NOM_PROJET = "Rubiks_Meca500.rdk"   # sur le Bureau
JOURNAL = "Rubiks_Meca500_journal.txt"

# ======================================================================

h = COTE_CUBE / 2
Z_CENTRE = h                                         # centre du cube posé (repère socle)
Z_BAS_CORPS = EPAISSEUR_PLAQUE + CORPS_Z             # dessous du boîtier (repère bride)
TCP_Z = Z_BAS_CORPS + h + GARDE_HAUT                 # TCP au centre du cube saisi
Z_BOUT_DOIGTS = TCP_Z + h - GARDE_BAS                # bout des doigts (repère bride)
SERRAGE = (ECART_OUVERT - COTE_CUBE) / 2

NOM_REPERE = "Socle_repere"
NOM_OUTIL = "MEGP 25E"
NOMS_SCENE = ["Socle", "Cube", "Cube_bas", "Cube_haut"]
NOMS_PINCE = ["Pince_plaque", "Pince_corps", "Pince_CAO", "Doigt_1", "Doigt_2"]

COUL = {
    "noir": [0.05, 0.05, 0.05, 1], "blanc": [0.95, 0.95, 0.95, 1], "jaune": [1.0, 0.85, 0.0, 1],
    "rouge": [0.85, 0.1, 0.1, 1], "orange": [1.0, 0.45, 0.0, 1], "vert": [0.0, 0.6, 0.2, 1],
    "bleu": [0.0, 0.3, 0.8, 1], "gris": [0.6, 0.6, 0.62, 1], "gris_fonce": [0.3, 0.3, 0.33, 1],
    "pla": [0.95, 0.55, 0.15, 1], "alu": [0.8, 0.8, 0.82, 1], "socle": [0.45, 0.35, 0.25, 1],
}

RDK = Robolink()
lignes_journal = []


def log(*args):
    texte = " ".join(str(a) for a in args)
    print(texte)
    lignes_journal.append(texte)


def pos(m):
    return [round(v, 1) for v in m.Pos()]


# ----------------------------- Géométrie -----------------------------

def boite(x0, y0, z0, x1, y1, z1):
    p = [[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0],
         [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]]
    faces = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4),
             (2, 3, 7), (2, 7, 6), (1, 2, 6), (1, 6, 5), (3, 0, 4), (3, 4, 7)]
    pts = []
    for a, b, c in faces:
        pts += [p[a], p[b], p[c]]
    return pts


def objet(nom, morceaux):
    """Crée un objet à la racine de la station (pose identité)."""
    donnees = []
    for pts, coul in morceaux:
        donnees += [tr(Mat(pts)), COUL[coul]]
    obj = RDK.AddShape(donnees)
    obj.setName(nom)
    return obj


def attacher(obj, parent, pose_locale):
    obj.setParent(parent)
    obj.setPose(pose_locale)


def supprimer(noms):
    for nom in noms:
        it = RDK.Item(nom, ITEM_TYPE_OBJECT)
        while it.Valid() and it.Name() == nom:
            it.Delete()
            it = RDK.Item(nom, ITEM_TYPE_OBJECT)


def morceaux_cube():
    """Cube 3x3 : corps noir + autocollants (centré en X/Y, posé sur z=0)."""
    s = COTE_CUBE / 3
    m, e = 1.0, 0.6
    morceaux = [(boite(-h, -h, 0, h, h, COTE_CUBE), "noir")]
    for i in (-1, 0, 1):
        for j in (-1, 0, 1):
            a, b = i * s - s / 2 + m, i * s + s / 2 - m      # coordonnée horizontale
            za, zb = (j + 1) * s + m, (j + 2) * s - m          # rangée (hauteur)
            ya, yb = j * s - s / 2 + m, j * s + s / 2 - m
            morceaux += [
                (boite(h, a, za, h + e, b, zb), "rouge"),
                (boite(-h - e, a, za, -h, b, zb), "orange"),
                (boite(a, h, za, b, h + e, zb), "vert"),
                (boite(a, -h - e, za, b, -h, zb), "bleu"),
                (boite(a, ya, COTE_CUBE, b, yb, COTE_CUBE + e), "blanc"),
                (boite(a, ya, -e, b, yb, 0), "jaune"),
            ]
    return morceaux


# ----------------------------- Scène -----------------------------

def chercher_fichier_robot():
    maison = os.path.expanduser("~")
    dossiers = [os.path.join(maison, "Desktop"), os.path.join(maison, "Documents", "RoboDK")]
    try:
        dossiers.append(RDK.getParam(PATH_LIBRARY))
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


def obtenir_robot():
    robot = RDK.Item('', ITEM_TYPE_ROBOT)
    if robot.Valid():
        return robot
    chemin = chercher_fichier_robot()
    if chemin:
        robot = RDK.AddFile(chemin)
        if robot.Valid():
            return robot
    raise Exception("Meca500 R3 introuvable. Télécharge-le depuis la bibliothèque RoboDK puis relance.")


def construire_socle_et_cube(robot):
    supprimer(NOMS_SCENE)
    repere = RDK.Item(NOM_REPERE, ITEM_TYPE_FRAME)
    if not repere.Valid():
        repere = RDK.AddFrame(NOM_REPERE, robot.Parent())
    repere.setPose(transl(SOCLE_X, SOCLE_Y, HAUTEUR_SOCLE))

    L = LARGEUR_SOCLE / 2
    socle = objet("Socle", [
        (boite(-L, -L, -HAUTEUR_SOCLE, L, L, -0.7), "socle"),
        (boite(-h, h + 0.7, -0.7, h, h + 0.7 + EPAISSEUR_MORS, HAUTEUR_MORS), "gris"),
        (boite(-h, -h - 0.7 - EPAISSEUR_MORS, -0.7, h, -h - 0.7, HAUTEUR_MORS), "gris"),
    ])
    attacher(socle, repere, eye(4))
    cube = objet("Cube", morceaux_cube())
    attacher(cube, repere, eye(4))
    return repere, cube


def construire_pince(robot):
    outil = RDK.Item(NOM_OUTIL, ITEM_TYPE_TOOL)
    autre = RDK.Item('', ITEM_TYPE_TOOL)
    a_nous = any(RDK.Item(n, ITEM_TYPE_OBJECT).Valid() for n in NOMS_PINCE)

    if not outil.Valid() and autre.Valid():
        return autre, []
    if outil.Valid() and not a_nous:
        return outil, []

    if not outil.Valid():
        outil = robot.AddTool(transl(0, 0, TCP_Z), NOM_OUTIL)
    outil.setPoseTool(transl(0, 0, TCP_Z))
    supprimer(NOMS_PINCE)

    # Toutes les géométries sont exprimées dans le repère de la BRIDE (Z sort de la bride)
    pieces = []
    if FICHIER_CAO_PINCE and os.path.isfile(FICHIER_CAO_PINCE):
        cao = RDK.AddFile(FICHIER_CAO_PINCE)
        cao.setName("Pince_CAO")
        pieces.append(cao)
    else:
        pieces.append(objet("Pince_plaque", [(boite(-16, -16, 0, 16, 16, EPAISSEUR_PLAQUE), "alu")]))
        pieces.append(objet("Pince_corps", [(boite(-CORPS_X / 2, -CORPS_Y / 2, EPAISSEUR_PLAQUE,
                                                   CORPS_X / 2, CORPS_Y / 2, Z_BAS_CORPS), "gris_fonce")]))

    yi = ECART_OUVERT / 2
    yo = yi + EPAISSEUR_DOIGT
    w = LARGEUR_DOIGT / 2
    doigts = []
    for nom, sg in (("Doigt_1", 1), ("Doigt_2", -1)):
        y_a, y_b = sorted([sg * 4, sg * yo])
        pts = boite(-w, y_a, Z_BAS_CORPS, w, y_b, Z_BAS_CORPS + EPAISSEUR_PONT)          # pont sur la mâchoire
        y_a, y_b = sorted([sg * yi, sg * yo])
        pts += boite(-w, y_a, Z_BAS_CORPS, w, y_b, Z_BOUT_DOIGTS)                         # grand doigt
        d = objet(nom, [(pts, "pla")])
        pieces.append(d)
        doigts.append((d, sg))

    # Diagnostic : où se trouve le repère de l'outil par rapport à la bride ?
    base = robot.Parent()
    robot.setPoseFrame(base)
    robot.setPoseTool(outil)
    tcp_abs = base.PoseAbs() * robot.Pose()
    bride_abs = tcp_abs * transl(0, 0, -TCP_Z)
    log("Bride abs:", pos(bride_abs), "| TCP abs:", pos(tcp_abs), "| Outil.PoseAbs:", pos(outil.PoseAbs()))

    for p in pieces:
        attacher(p, outil, eye(4))
    log("Pièce attachée (pose locale identité) abs:", pos(pieces[0].PoseAbs()))

    # Si le repère des enfants de l'outil n'est pas la bride, on corrige (sinon correction = identité)
    correction = pieces[0].PoseAbs().inv() * bride_abs
    for p in pieces:
        p.setPose(correction)
    log("Correction:", pos(correction), "-> pièce abs:", pos(pieces[0].PoseAbs()))
    return outil, doigts


# ----------------------------- Pince -----------------------------

etat_pince = {"fermee": False}


def bouger_doigts(doigts, fermer):
    if etat_pince["fermee"] == fermer:
        return
    for d, sg in doigts:
        dy = -sg * SERRAGE if fermer else sg * SERRAGE
        d.setPose(d.Pose() * transl(0, dy, 0))
    etat_pince["fermee"] = fermer


def ouvrir_pince(robot, doigts, cube, repere):
    # Robot réel (mecademicpy) : robot.GripperOpen()
    bouger_doigts(doigts, False)
    cube.setParentStatic(repere)
    robot.Pause(300)


def fermer_pince(robot, doigts, cube, outil):
    # Robot réel (mecademicpy) : robot.GripperClose()
    bouger_doigts(doigts, True)
    avant = pos(cube.PoseAbs())
    cube.setParentStatic(outil)
    log("Cube saisi : abs avant", avant, "après", pos(cube.PoseAbs()))
    robot.Pause(300)


# ----------------------------- Séquence -----------------------------

def pose_outil(z, bascule_deg=0.0):
    """TCP au centre du cube (hauteur z), doigts sur les faces ±X.
    bascule_deg : rotation du cube autour de l'axe des doigts (X du socle)."""
    return transl(0, 0, z) * rotx(bascule_deg * pi / 180) * rotz(pi / 2) * rotx(pi)


def main():
    robot = obtenir_robot()
    RDK.Render(False)
    repere, cube = construire_socle_et_cube(robot)
    outil, doigts = construire_pince(robot)
    RDK.Render(True)

    robot.setPoseFrame(repere)
    robot.setPoseTool(outil)
    robot.setSpeed(VITESSE_LIN, VITESSE_ART)

    a = SENS_BASCULE * ANGLE_BASCULE
    etape = ""
    try:
        etape = "approche"
        robot.MoveJ(pose_outil(Z_CENTRE + DEGAGEMENT + h))
        ouvrir_pince(robot, doigts, cube, repere)

        etape = "descente et prise"
        robot.MoveL(pose_outil(Z_CENTRE))
        fermer_pince(robot, doigts, cube, outil)

        etape = "sortie du socle"
        robot.MoveL(pose_outil(Z_CENTRE + LEVEE))

        etape = "bascule de %.0f°" % a
        robot.MoveJ(pose_outil(Z_CENTRE + LEVEE, a))

        etape = "retour dans le socle"
        robot.MoveL(pose_outil(Z_CENTRE, a))
        ouvrir_pince(robot, doigts, cube, repere)

        etape = "dégagement"
        robot.MoveL(pose_outil(Z_CENTRE + DEGAGEMENT + h, a))
        robot.MoveJ(pose_outil(Z_CENTRE + DEGAGEMENT + h))
    except Exception as e:
        log("ERREUR pendant l'étape :", etape, "->", str(e))
        ecrire_journal()
        RDK.ShowMessage("Mouvement impossible pendant l'étape « %s ».\n"
                        "Essaie SENS_BASCULE = %d ou déplace le socle (SOCLE_X/Y, HAUTEUR_SOCLE)."
                        % (etape, -SENS_BASCULE), False)
        raise

    message = "Bascule de %.0f° terminée." % a
    if ENREGISTRER_PROJET:
        try:
            chemin = os.path.join(RDK.getParam(PATH_DESKTOP), NOM_PROJET)
            RDK.Save(chemin)
            if os.path.isfile(chemin):
                message += "\nProjet enregistré : " + chemin
        except Exception as e:
            message += "\nEnregistrement impossible : %s" % str(e)
    log(message)
    ecrire_journal()
    RDK.ShowMessage(message, False)


def ecrire_journal():
    try:
        chemin = os.path.join(RDK.getParam(PATH_DESKTOP), JOURNAL)
        with open(chemin, "w") as f:
            f.write("\n".join(lignes_journal) + "\n")
    except Exception:
        pass


if __name__ == "__main__":
    main()
