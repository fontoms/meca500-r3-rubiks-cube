# -*- coding: utf-8 -*-
"""
Modèle logiciel du Rubik's cube : 26 cubies, coups en notation standard, format kociemba.

Pur Python (aucune dépendance à RoboDK) : testable directement (tests/test_modele_cube.py).
Repère : celui du socle, centre du cube ; positions des cubies sur la grille -1 / 0 / 1.
"""

# Orientation de départ (repère du socle) : U en haut, F face au robot (-X), R vers -Y.
# Couleurs : U blanc, D jaune, F vert, B bleu, R rouge, L orange.
DIR_FACE = {"U": (0, 0, 1), "D": (0, 0, -1), "F": (-1, 0, 0),
            "B": (1, 0, 0), "R": (0, -1, 0), "L": (0, 1, 0)}
FACE_DIR = {v: k for k, v in DIR_FACE.items()}


# ----------------------------- Petites matrices entières 3x3 -----------------------------

def rot_quart(axe, q):
    """Matrice entière 3x3 : rotation de q×90° autour de l'axe 0=X, 1=Y, 2=Z."""
    c, s = [1, 0, -1, 0][q % 4], [0, 1, 0, -1][q % 4]
    if axe == 0:
        return [[1, 0, 0], [0, c, -s], [0, s, c]]
    if axe == 1:
        return [[c, 0, s], [0, 1, 0], [-s, 0, c]]
    return [[c, -s, 0], [s, c, 0], [0, 0, 1]]


def rot_autour(n, q):
    """Rotation de q×90° autour de la direction n (±X, ±Y, ±Z)."""
    axe = [i for i in range(3) if n[i]][0]
    return rot_quart(axe, q * n[axe])


def mul(A, v):
    return tuple(sum(A[i][k] * v[k] for k in range(3)) for i in range(3))


def mulm(A, B):
    return [[sum(A[i][k] * B[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def transp(A):
    return [[A[j][i] for j in range(3)] for i in range(3)]


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


# ----------------------------- Le cube -----------------------------

def nom_cubie(p0):
    return "Cubie_%+d%+d%+d" % p0


class ModeleCube:
    """26 cubies : position (grille -1/0/1, repère socle, centre du cube) + orientation 3x3.

    self.c[position_de_depart] = [position_actuelle, orientation_actuelle]
    """

    def __init__(self):
        self.c = {}
        for x in (-1, 0, 1):
            for y in (-1, 0, 1):
                for z in (-1, 0, 1):
                    if (x, y, z) != (0, 0, 0):
                        self.c[(x, y, z)] = [(x, y, z), rot_quart(0, 0)]

    def copie(self):
        m = ModeleCube()
        m.c = {k: [p, [r[:] for r in R]] for k, (p, R) in self.c.items()}
        return m

    def tourner(self, Q, filtre=lambda p: True):
        for k, (p, R) in self.c.items():
            if filtre(p):
                self.c[k] = [mul(Q, p), mulm(Q, R)]

    def centre(self, face):
        return self.c[DIR_FACE[face]][0]

    def coup(self, face, k):
        """Coup de notation standard : face tournée de k quarts de tour dans le sens horaire."""
        n = self.centre(face)
        self.tourner(rot_autour(n, -k), lambda p: sum(p[i] * n[i] for i in range(3)) == 1)

    def orientation(self):
        cols = [self.c[e][0] for e in ((1, 0, 0), (0, 1, 0), (0, 0, 1))]
        return [[cols[j][i] for j in range(3)] for i in range(3)]

    def normalise(self):
        """Copie remise dans l'orientation de départ (centres à leur place)."""
        m = self.copie()
        m.tourner(transp(self.orientation()))
        return m

    def autocollants(self):
        res = {}
        for p0, (p, R) in self.c.items():
            for i in range(3):
                if p0[i]:
                    e = tuple(p0[i] if j == i else 0 for j in range(3))
                    res[(p, mul(R, e))] = FACE_DIR[e]
        return res

    def facelets(self):
        """Chaîne de 54 lettres au format kociemba (ordre U R F D L B)."""
        st = self.normalise().autocollants()
        haut = {"U": DIR_FACE["B"], "R": DIR_FACE["U"], "F": DIR_FACE["U"],
                "D": DIR_FACE["F"], "L": DIR_FACE["U"], "B": DIR_FACE["U"]}
        out = ""
        for f in "URFDLB":
            n, u = DIR_FACE[f], haut[f]
            r = cross(tuple(-v for v in n), u)
            for i in range(3):
                for j in range(3):
                    p = tuple(n[a] + u[a] * (1 - i) + r[a] * (j - 1) for a in range(3))
                    out += st[(p, n)]
        return out

    def resolu(self):
        f = self.facelets()
        return all(len(set(f[9 * i:9 * i + 9])) == 1 for i in range(6))

    def egal(self, autre):
        a, b = self.normalise(), autre.normalise()
        return all(a.c[k][0] == b.c[k][0] and a.c[k][1] == b.c[k][1] for k in a.c)


# ----------------------------- Notation des coups -----------------------------

def lire_coups(texte):
    """"R U' F2" → [("R", 1), ("U", -1), ("F", 2)]."""
    coups = []
    for tok in texte.replace(",", " ").split():
        face, suf = tok[0].upper(), tok[1:]
        if face not in DIR_FACE:
            raise ValueError("Coup inconnu : " + tok)
        k = 2 if "2" in suf else (-1 if "'" in suf else 1)
        coups.append((face, k))
    return coups


def ecrire_coups(coups):
    return " ".join(f + {1: "", -1: "'", 2: "2"}[k] for f, k in coups)


def inverse(coups):
    return [(f, 2 if k == 2 else -k) for f, k in reversed(coups)]


def chemin_vers_bas(d):
    """Plus courte suite de bascules (B, ±1) / rotations (Z, q) qui amène la direction d en bas."""
    ops = [("B", 1), ("B", -1), ("Z", 1), ("Z", -1)]
    niveau = [(d, [])]
    for _ in range(4):
        for v, chemin in niveau:
            if v == (0, 0, -1):
                return chemin
        niveau = [(mul(rot_quart(0 if op == "B" else 2, a), v), chemin + [(op, a)])
                  for v, chemin in niveau for op, a in ops]
    raise ValueError("Pas de chemin pour %s" % (d,))
