# -*- coding: utf-8 -*-
"""
Point d'entrée de la SIMULATION RoboDK (le code du robot est dans ../meca500_rubiks/).

Se lance depuis RoboDK : Tools > Run Script > 00_Rubiks_Meca500 (qui appelle scene.main()),
ou depuis PyCharm / un terminal avec RoboDK ouvert :  python simulation/scene.py

Le mode se choisit dans parametres.py (MODE) :
  "installer"  → construit la scène, ajoute un programme par mouvement de meca500_rubiks
                 dans l'arbre de la station, et enregistre Rubiks_Meca500.rdk.
  "tests"      → enchaîne les mouvements de la liste TESTS en vérifiant les collisions.
  "resolution" → résout un cube mélangé (MELANGE / SOLUTION), pour plus tard.

Organisation de la simulation :
  parametres.py        dimensions (pince, socle, cube) et réglages      ← à modifier
  modele_cube.py       modèle logiciel du Rubik's cube (sans RoboDK)
  construction.py      construction de la scène 3D dans RoboDK
  banc_essais.py       MODE "tests" (collisions) et "resolution"
  simulateur.py        joue meca500_rubiks dans RoboDK (programmes de la station)
  verifier.py          vérification cinématique de meca500_rubiks
  connexion_robodk.py  connexion à RoboDK
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import parametres as P                                       # noqa: E402
from robodk import robolink                                  # noqa: E402
from connexion_robodk import RDK                             # noqa: E402
from journalisation import ecrire_journal, lignes_journal, log  # noqa: E402

# RoboDK exécute le programme depuis une copie temporaire : on retrouve le projet grâce au dossier de la
# station ouverte (Rubiks_Meca500.rdk est à la racine du projet). Aucun chemin écrit en dur : les
# programmes marchent sur tous les ordinateurs (Mac, Windows) sans reconstruire la station.
GABARIT_PROGRAMME = '''# -*- coding: utf-8 -*-
# Programme RoboDK : exécute meca500_rubiks.{nom}() dans la simulation.
import os
import sys
from robodk import robolink
projet = robolink.Robolink().getParam("PATH_OPENSTATION")    # dossier de Rubiks_Meca500.rdk
sys.path.insert(0, os.path.join(projet, "simulation"))
import simulateur
simulateur.simuler({nom!r})
'''


def installer_mouvements():
    """Construit la scène et ajoute dans l'arbre de la station un programme par mouvement
    de meca500_rubiks (même nom que la fonction), plus « remise_a_zero » et « verifier_mouvements »."""
    import meca500_rubiks
    from banc_essais import preparer_scene

    preparer_scene([])
    RDK.setCollisionActive(robolink.COLLISION_OFF)
    os.makedirs(P.DOSSIER_PROGRAMMES, exist_ok=True)
    noms = ["remise_a_zero", "verifier_mouvements"] + [f.__name__ for f in meca500_rubiks.MOUVEMENTS]
    for it in RDK.ItemList(robolink.ITEM_TYPE_PROGRAM_PYTHON):     # anciens programmes
        it.Delete()
    for nom in noms:
        chemin = os.path.join(P.DOSSIER_PROGRAMMES, nom + ".py")
        with open(chemin, "w", encoding="utf-8") as f:
            f.write(GABARIT_PROGRAMME.format(nom=nom))
        prog = RDK.AddFile(chemin)
        if prog.Valid():
            prog.setName(nom)
    log("Programmes ajoutés dans l'arbre de la station : " + ", ".join(noms))


def main():
    import banc_essais

    resultat = None
    try:
        if P.MODE == "installer":
            resultat = installer_mouvements()
        elif P.MODE == "tests":
            resultat = banc_essais.mode_tests()
        else:
            resultat = banc_essais.mode_resolution()
    except Exception as e:
        log("ERREUR :", str(e))
        ecrire_journal()
        RDK.ShowMessage("Erreur : %s" % e, False)
        raise
    finally:
        if P.VERIFIER_COLLISIONS:
            RDK.setCollisionActive(robolink.COLLISION_OFF)

    message = lignes_journal[-1] if lignes_journal else "Terminé."
    if P.ENREGISTRER_PROJET:
        chemin = os.path.join(P.DOSSIER_PROJET, P.NOM_PROJET)
        try:
            RDK.Save(chemin)
            if os.path.isfile(chemin):
                log("Projet enregistré : " + chemin)
        except Exception as e:
            log("Enregistrement impossible : %s" % e)
    ecrire_journal()
    RDK.ShowMessage("Terminé — détails dans le journal :\n" + message, False)
    return resultat


if __name__ == "__main__":
    main()
