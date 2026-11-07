from movements import (
    bascule_droite,
    bascule_gauche,
    bascule_avant,
    bascule_arriere,
    tourner_haut_droite,
    tourner_haut_gauche,
)

def move_r():
    bascule_droite()
    tourner_haut_droite()
    bascule_gauche()
    bascule_avant()

def move_l():
    bascule_gauche()
    tourner_haut_droite()
    bascule_droite()
    bascule_arriere()

def move_u():
    bascule_droite()
    bascule_droite()
    tourner_haut_droite()
    bascule_droite()
    bascule_arriere()
    bascule_droite()

def move_d():
    tourner_haut_droite()
    bascule_avant()
    bascule_droite()
    bascule_arriere()

def move_f():
    bascule_arriere()
    tourner_haut_droite()
    bascule_avant()
    bascule_droite()

def move_b():
    bascule_avant()
    tourner_haut_droite()
    bascule_arriere()
    bascule_gauche()

sol_to_move_map = {
    "R": move_r,
    "L": move_l,
    "U": move_u,
    "D": move_d,
    "F": move_f,
    "B": move_b,
}

def solution_to_moves(solution: str):
    splits = solution.split(" ")

    # Retire le nombre de move à la fin de la solution
    splits.pop()

    for moves in splits:
        move = moves[0] # The move R L U D F B
        n = int(moves[1]) # The number of times to repeat the move

        for _ in range(n):
            sol_to_move_map[move]()

