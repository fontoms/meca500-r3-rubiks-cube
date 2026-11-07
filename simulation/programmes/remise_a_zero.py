# Programme RoboDK : exécute meca500_rubiks.remise_a_zero() dans la simulation.
import sys
sys.path.insert(0, '/Users/colin/Documents/Rubiks_Meca500/simulation')
import simulateur
simulateur.simuler('remise_a_zero')
