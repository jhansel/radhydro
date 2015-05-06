## @package src.hydroExecutioner
#  Runs a hydrodynamics problem.

import numpy as np
from numpy import       array
from mesh import        Mesh
from math import        sqrt
from musclHanc import   hydroPredictor, main, HydroState, \
                        plotHydroSolutions, hydroCorrector

## Main executioner for Hydro solve. Currently in a testing state.
def solveHydroProblem():

    #-------------------------------------------------------------------------------
    # Construct initial hydro states, probably create an initializer class
    #-------------------------------------------------------------------------------
    width = 1.0
    t_end = 0.05

    t = 0.0
    cfl = 0.5
    n = 500

    #Left and right BC and initial values
    gamma = 1.4 #gas constant
    p_left = 1.0
    u_left  = .750
    rho_left = 1.

    p_right = 0.1
    u_right = 0.0
    rho_right = 0.125

    #Create a mesh, currently hardcoded
    mesh = Mesh(n, width)
    dx = mesh.getElement(0).dx

    if n % 2 != 0: #simple error raise, % has lots of diff meanings in python
        raise ValueError("Must be even number of cells")

    i_left = int(0.3*n)
    i_right = int(0.7*n)

    #Create cell centered variables
    states_a = [HydroState(u=u_left,p=p_left,gamma=gamma,rho=rho_left) for i in range(i_left)]
    states_a = states_a + [HydroState(u=u_right,p=p_right,gamma=gamma,rho=rho_right) for i in
            range(i_right)]

    #-----------------------------------------------------------------
    # Solve Problem
    #----------------------------------------------------------------

    #loop over time steps
    while (t < t_end):

        #Compute a new time step size based on CFL
        c = [sqrt(i.p*i.gamma/i.rho)+abs(i.u) for i in states_a]
        dt_vals = [cfl*(mesh.elements[i].dx)/c[i] for i in range(len(c))]
        dt = min(dt_vals)
        print "new dt:", dt

        t += dt
        #shorten last step to be exact
        if (t > t_end):
            t -= dt
            dt = t_end - t + 0.000000001
            t += dt

        #Solve predictor step
        states_l, states_r = hydroPredictor(mesh, states_a, dt)

        #Solve corrector step
        states_a = hydroCorrector(mesh, states_a, states_l, states_r, dt)


    spat_coors = [i.x_cent for i in mesh.elements]
    plotHydroSolutions(spat_coors,states=states_a)
    for i in states_a:
        print i
    


if __name__ == "__main__":
    solveHydroProblem()
