# -*- coding: utf-8 -*-
"""Journal texte de scene.py (journal/Rubiks_Meca500_journal.txt)."""
import os

import parametres as P

lignes_journal = []


def log(*args):
    texte = " ".join(str(a) for a in args)
    print(texte)
    lignes_journal.append(texte)


def ecrire_journal():
    if not P.JOURNAL:
        return
    try:
        os.makedirs(P.DOSSIER_JOURNAL, exist_ok=True)
        with open(os.path.join(P.DOSSIER_JOURNAL, P.JOURNAL), "w") as f:
            f.write("\n".join(lignes_journal) + "\n")
    except OSError as e:
        print("Journal non écrit : %s" % e)
