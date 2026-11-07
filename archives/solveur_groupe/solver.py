import twophase.solver as sv

# cubestring "UUUUUUUUU..."

def solve(cubestring: str):
    solution = sv.solve(cubestring, 20, 15)
    return solution