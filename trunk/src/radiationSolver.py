import math
import numpy as np
from numpy import array
from Mesh import Mesh

## Index function for 1-D LD S-2.
#
#  @param[in] i     cell index, from 1 to n-1, where n is number of cells
#  @param[in] side  string, either "L" or "R", corresponding to left or right dof
#  @param[in] dir   string, either "-" or "+", corresponding to - or + direction
#
#  @return    global dof index
def index(i, side, dir):
  side_shift = {"L" : 0, "R" : 2}
  dir_shift  = {"-" : 0, "+" : 1}
  return 4*i + side_shift[side] + dir_shift[dir]

## Steady-state solve function for the S-2 equations.
#
#  @param[in] mesh     a mesh object
#  @param[in] cross_x  list of cross sections for each element, stored as tuple
#                      for each cell.
#  @param[in] Q_minus  total isotropic source in minus direction:
#                      \f$Q = Q_0 + 3\mu^-Q_1\f$
#  @param[in] Q_plus   total isotropic source in plus direction:
#                      \f$Q = Q_0 + 3\mu^+Q_1\f$
#  @param[in] stream_scale_factor scale factor \f$\alpha\f$for reaction and
#                                 streaming terms; sigma_t psi + mu \dpsi/dx ->
#                                 alpha*(sigma_t psi + mu \dpsi/dx). This is
#                                 used with various time dependent solvers.
#  @param[in] diag_add_term       term to add to reaction term for use in
#                                 time-dependent solvers, e.g., alpha*sigma_t*psi_L
#                                 -> (alpha*sigma_t + 1/c*delta_t)psi_L. Must be
#                                 done after scale
#  @param[in] bound_curr_lt       left boundary current
#  @param[in] bound_curr_rt       right boundary current
#
#  @return 
#          -# \f$\psi^+\f$, angular flux in plus directions
#          -# \f$\psi^-\f$, angular flux in minus directions
#          -# \f$\mathcal{E}\f$: radiation energy
#          -# \f$\mathcal{F}\f$: radiation flux
#
def radiationSolver(mesh, cross_x, Q_minus, Q_plus, stream_scale_factor=1.0,
        diag_add_term=0.0, bound_curr_lt=0.0, bound_curr_rt=0.0):

    # set directions
    mu = {"-" : -1/math.sqrt(3), "+" : 1/math.sqrt(3)}

    # 1/(4*pi) constant for isotropic source Q
    c_Q = 1/(4*math.pi)

    # initialize numpy arrays for system matrix and rhs
    n = 4*mesh.n_elems
    matrix = np.zeros((n, n))
    rhs    = np.zeros(n)

    # loop over interior cells
    for i in xrange(1,mesh.n_elems-1):
       # compute indices
       iprevRplus  = index(i-1,"R","+") # dof i-1,R,+
       iLminus     = index(i,  "L","-") # dof i,  L,-
       iLplus      = index(i,  "L","+") # dof i,  L,+
       iRminus     = index(i,  "R","-") # dof i,  R,-
       iRplus      = index(i,  "R","+") # dof i,  R,+
       inextLminus = index(i+1,"L","-") # dof i+1,L,-

       # get cell size
       h = mesh.getElement(i).dx

       # get cross sections
       cx_sL = cross_x[i][0].sig_s # Left  scattering
       cx_sR = cross_x[i][1].sig_s # Right scattering
       cx_tL = cross_x[i][0].sig_t # Left  total
       cx_tR = cross_x[i][1].sig_t # Right total

       # get sources
       QLminus = Q_minus[i][0] # minus direction, Left
       QLplus  = Q_plus [i][0] # plus  direction, Left
       QRminus = Q_minus[i][1] # minus direction, Right
       QRplus  = Q_plus [i][1] # plus  direction, Right

       # Left control volume, minus direction
       row = np.zeros(n)
       row[iLminus] = -0.5*mu["-"] + 0.5*cx_tL*h - 0.25*cx_sL*h
       row[iLplus]  = -0.25*cx_sL*h
       row[iRminus] = 0.5*mu["-"]
       matrix[iLminus] = row
       rhs[iLminus] = 0.5*c_Q*h*QLplus
      


    # return zeros for time being
    psi_minus = [(0, 0) for i in range(mesh.n_elems)]
    psi_plus = [(0, 0) for i in range(mesh.n_elems)]
    E = [(0, 0) for i in range(mesh.n_elems)]
    F = [(0, 0) for i in range(mesh.n_elems)]

    return psi_minus, psi_plus, E, F
