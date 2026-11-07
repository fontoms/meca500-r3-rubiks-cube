# -*- coding: utf-8 -*-
"""
Pilote le VRAI Meca500 (mecademicpy). Pour la simulation, utilise RoboDK.

    python piloter_robot.py                     → menu des mouvements
    python piloter_robot.py basculer_droite     → un seul mouvement, puis déconnexion
    python piloter_robot.py --liste             → liste des mouvements

Premier essai : SANS le cube, vitesses basses (reglages.py), main sur l'arrêt d'urgence.
"""
import sys

import meca500_rubiks as rubiks

NOMS = {m.__name__: m for m in rubiks.MOUVEMENTS}


def main(argv):
    if argv and argv[0] == "--liste":
        for nom, m in NOMS.items():
            print("%-22s %s" % (nom, m.__doc__.splitlines()[0]))
        return 0
    if argv and argv[0] not in NOMS:
        print("Mouvement inconnu : %s\nMouvements : %s" % (argv[0], ", ".join(NOMS)))
        return 1

    robot = rubiks.connecter()
    try:
        if argv:
            print("->", argv[0])
            NOMS[argv[0]](robot)
        else:
            rubiks.menu(robot)
    finally:
        rubiks.deconnecter(robot)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
