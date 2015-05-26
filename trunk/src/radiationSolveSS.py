## @package src.radiationSolveSS
#  Provides functions to solve the steady-state S-2 equations. Also provides
#  means of employing solver to be used in temporal discretizations.

import math
import numpy as np
from numpy import array
from mesh import Mesh
from utilityFunctions import getIndex

## Steady-state solve function for the S-2 equations.
#
#  @param[in] mesh     a mesh object
#  @param[in] cross_x  list of cross sections for each element, stored as tuple
#                      for each cell.
#  @param[in] Q        total source (note there is no division by 4 pi in the solver,
#                      so an isotropic source should divide by 2. before passing to
#                      this function). This may include Q1 sources, but those are
#                      built in to the source vector. This vector contains the Q for 
#                      each DOF, i.e., for element i, Q_L+, Q_R+, Q_L-, Q_R-, using
#                      the same ordering as the equations for psi, accessed through
#                      getIndex()
#  @param[in] diag_add_term       term to add to reaction term for use in
#                                 time-dependent solvers, e.g., alpha*sigma_t*psi_L
#                                 -> (alpha*sigma_t + 1/c*delta_t)psi_L. Must be
#                                 done after scale
#  @param[in] bound_curr_lt       left  boundary current data, \f$j^+\f$
#  @param[in] bound_curr_rt       right boundary current data, \f$j^-\f$
#  @param[in] bound_flux_plus     left  boundary psi
#  @param[in] bound_flux_minus    right boundary psi
#
#  @return 
#          -# \f$\psi^+\f$, angular flux in plus directions
#          -# \f$\psi^-\f$, angular flux in minus directions
#          -# \f$\mathcal{E}\f$: radiation energy
#          -# \f$\mathcal{F}\f$: radiation flux
#
def radiationSolveSS(mesh, cross_x, Q, diag_add_term=0.0,
    bound_curr_lt=0.0, bound_curr_rt=0.0,
    bc_psi_plus = None, bc_psi_minus = None):

    # set directions
    mu = {"-" : -1/math.sqrt(3), "+" : 1/math.sqrt(3)}

    # compute boundary fluxes based on incoming currents if there is no specified
    # fluxes.  If fluxes are specified, they will overwrite current value. Default 
    # is zero current
    if bc_psi_plus != None and bound_curr_lt != 0.0:
        raise ValueError("You cannot specify a current and boundary flux, on left")
    if bc_psi_minus != None and bound_curr_rt != 0.0:
        raise ValueError("You cannot specify a current and boundary flux, on right")

    if bc_psi_plus == None:
        bc_psi_plus  =  bound_curr_lt / (0.5)

    if bc_psi_minus == None:
        bc_psi_minus = bound_curr_rt / (0.5)


    # initialize numpy arrays for system matrix and rhs
    n = 4*mesh.n_elems
    matrix = np.zeros((n, n))
    rhs    = np.zeros(n)

    # loop over interior cells
    for i in xrange(mesh.n_elems):
       # compute indices
       iprevRplus  = getIndex(i-1,"R","+") # dof i-1,R,+
       iLminus     = getIndex(i,  "L","-") # dof i,  L,-
       iLplus      = getIndex(i,  "L","+") # dof i,  L,+
       iRminus     = getIndex(i,  "R","-") # dof i,  R,-
       iRplus      = getIndex(i,  "R","+") # dof i,  R,+
       inextLminus = getIndex(i+1,"L","-") # dof i+1,L,-

       # get cell size
       h = mesh.getElement(i).dx

       # get cross sections
       cx_sL = cross_x[i][0].sig_s # Left  scattering
       cx_sR = cross_x[i][1].sig_s # Right scattering
       cx_tL = cross_x[i][0].sig_t # Left  total
       cx_tR = cross_x[i][1].sig_t # Right total

       # get sources
       QLminus = Q[iLminus] # minus direction, Left
       QLplus  = Q[iLplus] # plus  direction, Left
       QRminus = Q[iRminus] # minus direction, Right
       QRplus  = Q[iRplus] # plus  direction, Right

       # Left control volume, minus direction
       row = np.zeros(n)
       row[iLminus]    = -0.5*mu["-"] + 0.5*(cx_tL+diag_add_term)*h - 0.25*cx_sL*h
       row[iLplus]     = -0.25*cx_sL*h
       row[iRminus]    = 0.5*mu["-"]
       matrix[iLminus] = row
       rhs[iLminus]    = 0.5*h*QLplus
      
       # Left control volume, plus direction
       row = np.zeros(n)
       if i == 0:
          rhs[iLplus] = mu["+"]*bc_psi_plus
       else:
          row[iprevRplus] = -mu["+"]
       row[iLminus]    = -0.25*cx_sL*h
       row[iLplus]     = 0.5*mu["+"] + 0.5*(cx_tL+diag_add_term)*h - 0.25*cx_sL*h
       row[iRplus]     = 0.5*mu["+"]
       matrix[iLplus]  = row
       rhs[iLplus]    += 0.5*h*QLminus

       # Right control volume, minus direction
       row = np.zeros(n)
       row[iLminus]     = -0.5*mu["-"]
       row[iRminus]     = -0.5*mu["-"] + 0.5*(cx_tR+diag_add_term)*h - 0.25*cx_sR*h
       row[iRplus]      = -0.25*cx_sR*h
       if i == mesh.n_elems-1:
          rhs[iRminus] = -mu["-"]*bc_psi_minus
       else:
          row[inextLminus] = mu["-"]
       matrix[iRminus]  = row
       rhs[iRminus]    += 0.5*h*QRminus

       # Right control volume, plus direction
       row = np.zeros(n)
       row[iLplus]      = -0.5*mu["+"]
       row[iRminus]     = -0.25*cx_sR*h
       row[iRplus]      = 0.5*mu["+"] + 0.5*(cx_tR+diag_add_term)*h - 0.25*cx_sR*h
       matrix[iRplus]   = row
       rhs[iRplus]      = 0.5*h*QRplus

    # solve linear system
    solution = np.linalg.solve(matrix, rhs)

    # extract solution from global vector
    psi_minus = [(solution[4*i],  solution[4*i+2]) for i in xrange(mesh.n_elems)]
    psi_plus  = [(solution[4*i+1],solution[4*i+3]) for i in xrange(mesh.n_elems)]

    # return zeros for time being
    E = [(0, 0) for i in range(mesh.n_elems)]
    F = [(0, 0) for i in range(mesh.n_elems)]

    return psi_minus, psi_plus, E, F

