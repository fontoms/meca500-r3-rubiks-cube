# -*- coding: utf-8 -*-
"""
Installe le solveur de Rubik's cube (librairie RubikTwoPhase de Kociemba + ses tables).

    python installer_solveur.py                     # installe la librairie, génère les tables (long !)
    python installer_solveur.py --tables <dossier>  # copie des tables déjà calculées (ex. celles du
                                                    #   groupe solveur) au lieu de les générer

Les tables (~80 Mo) vont dans solveur_tables/twophase/, ignoré par git : à refaire sur chaque
ordinateur. Les générer prend une demi-heure ou plus ; les copier depuis un autre PC est immédiat.
"""
import argparse
import os
import shutil
import subprocess
import sys
import time

from meca500_rubiks import resolution

MELANGE_TEST = "DUUBULDBFRBFRRULLLBRDFFFBLURDBFDFDRFRULBLUFDURRBLBDUDL"


def installer_librairie():
    try:
        import twophase  # noqa: F401
        print("1/3  Librairie RubikTwoPhase : déjà installée")
    except ImportError:
        print("1/3  Installation de la librairie RubikTwoPhase (pip)…")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "RubikTwoPhase"])


def installer_tables(source):
    destination = os.path.join(resolution.DOSSIER_TABLES, "twophase")
    if resolution.tables_installees():
        print("2/3  Tables du solveur : déjà présentes dans %s" % destination)
        return
    os.makedirs(destination, exist_ok=True)
    if source:
        manquantes = [t for t in resolution.TABLES if not os.path.isfile(os.path.join(source, t))]
        if manquantes:
            sys.exit("Tables manquantes dans %s : %s" % (source, ", ".join(manquantes)))
        print("2/3  Copie des tables depuis %s…" % source)
        for t in resolution.TABLES:
            shutil.copy2(os.path.join(source, t), os.path.join(destination, t))
        return
    print("2/3  Génération des tables du solveur dans %s" % destination)
    print("     (une demi-heure ou plus, une seule fois ; ne ferme pas la fenêtre)")
    debut = time.time()
    dossier = os.getcwd()
    os.chdir(resolution.DOSSIER_TABLES)          # la librairie écrit ses tables dans ./twophase
    try:
        import twophase.solver  # noqa: F401   l'import crée les tables manquantes
    finally:
        os.chdir(dossier)
    print("     terminé en %.0f min" % ((time.time() - debut) / 60))


def tester():
    coups = resolution.calculer_solution(MELANGE_TEST, temps_max=5)
    print("3/3  Test : solution de %d coups trouvée (%s)" % (len(coups), resolution.ecrire(coups)))


def main(argv):
    parser = argparse.ArgumentParser(description="Installe le solveur twophase et ses tables.")
    parser.add_argument("--tables", help="dossier contenant des tables déjà calculées (fichiers co_classidx…)")
    args = parser.parse_args(argv)
    installer_librairie()
    installer_tables(args.tables)
    tester()
    print("Solveur prêt : python resoudre_cube.py <cubestring>")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
