# -*- coding: utf-8 -*-
"""
Aide au montage du socle sur le VRAI robot (voir GUIDE_MONTAGE.md).

    python placer_socle.py

Le robot amène la pince OUVERTE à l'endroit où le code attend le cube (SOCLE dans
meca500_rubiks/reglages.py), patins à hauteur du milieu du cube : à cette hauteur, tout l'outil
est au-dessus du socle (5 mm au-dessus de ses coins les plus hauts), il ne peut pas le toucher.

Tu regardes si les patins sont bien centrés sur les ouvertures avant / arrière de la poche.
Sinon, tu décales le robot au clavier :
    x 5     → 5 mm plus loin du robot          x -5   → 5 mm plus près
    y 5     → 5 mm vers la gauche (vu du robot) y -5   → 5 mm vers la droite
    ok      → affiche la ligne SOCLE à recopier dans reglages.py, puis remonte et s'arrête
    q       → remonte et s'arrête sans rien changer
Décalage limité à ±30 mm autour de SOCLE. SANS le cube, main sur l'arrêt d'urgence.
"""
import sys

import meca500_rubiks as rubiks

DECALAGE_MAX = 30.0


def main():
    x0, y0, z = rubiks.SOCLE
    dx = dy = 0.0
    robot = rubiks.connecter()                     # activation, réglages, position d'attente
    commande = ["q"]
    try:
        rubiks.ouvrir_pince(robot)
        rubiks.aller(robot, rubiks.H_CUBE)         # pince ouverte, patins au milieu de la poche
        robot.WaitIdle(60)
        print(__doc__.split("Tu regardes")[1].split("Décalage")[0])
        while True:
            commande = input("SOCLE = (%.1f, %.1f, %.1f) > " % (x0 + dx, y0 + dy, z)).strip().lower().split()
            if not commande:
                continue
            if commande[0] in ("q", "ok"):
                break
            if commande[0] not in ("x", "y") or len(commande) != 2:
                print("Commande : x <mm>, y <mm>, ok ou q")
                continue
            try:
                pas = float(commande[1].replace(",", "."))
            except ValueError:
                print("Nombre invalide : %s" % commande[1])
                continue
            nx, ny = (dx + pas, dy) if commande[0] == "x" else (dx, dy + pas)
            if max(abs(nx), abs(ny)) > DECALAGE_MAX:
                print("Refusé : plus de %.0f mm du SOCLE de reglages.py" % DECALAGE_MAX)
                continue
            dx, dy = nx, ny
            rubiks.aller(robot, rubiks.H_CUBE, lieu=(x0 + dx, y0 + dy, z))
            robot.WaitIdle(60)

        if commande[0] == "ok":
            print("\nRecopie cette ligne dans meca500_rubiks/reglages.py :")
            print("SOCLE = (%.1f, %.1f, %.1f)" % (x0 + dx, y0 + dy, z))
            print("puis reconstruis la station RoboDK et relance les tests (GUIDE_MONTAGE.md, étape 5).")
        rubiks.aller(robot, rubiks.H_ATTENTE, lieu=(x0 + dx, y0 + dy, z))
        rubiks.position_attente(robot)
    finally:
        rubiks.deconnecter(robot)
    return 0


if __name__ == "__main__":
    sys.exit(main())
