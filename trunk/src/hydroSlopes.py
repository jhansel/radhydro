## @package hydroSlopes
#  Contains class for computing and storing hydro slopes.

import numpy as np
from math import isinf

## Class for computing and storing hydro slopes
#
class HydroSlopes:

    ## Constructor
    #
    #  @param[in] states  hydro state for each cell
    #  @param[in] bc      hydro BC object
    #
    def __init__(self, states, bc, limiter):

       # save slope limiter
       self.limiter = limiter

       # extract vectors of conservative variables
       rho = [s.rho                     for s in states]
       mom = [s.rho*s.u                 for s in states]
       erg = [s.rho*(0.5*s.u*s.u + s.e) for s in states]

       # get boundary values
       rho_L, rho_R, mom_L, mom_R, erg_L, erg_R = bc.getBoundaryValues()

       # compute slopes
       self.rho_slopes = self.slopeReconstruction(rho, rho_L, rho_R)
       self.mom_slopes = self.slopeReconstruction(mom, mom_L, mom_R)
       self.erg_slopes = self.slopeReconstruction(erg, erg_L, erg_R)

       # compute an internal energy slope such that the edge internal energies conserve the TOTAL energy
       # I DONT THINK THIS IS RIGHT OR EVEN POSSILBE?
 #      rho_l, rho_r, mom_l, mom_r, erg_l, erg_r = self.createLinearRepresentation(states)

 #      self.e_slopes = np.zeros(len(states))
 #      for i in range(len(states)):
 #       
 #         el = erg_l[i]/rho_l[i] - 0.5*mom_l[i]**2./rho_l[i]**2.
 #         er = erg_r[i]/rho_r[i] - 0.5*mom_r[i]**2./rho_r[i]**2.

 #         ul = mom_l[i]/rho_l[i]
 #         ur = mom_r[i]/rho_r[i]
 #         print "New E?", (0.5*( rho_r[i]*(er + 0.5*ur*ur) + rho_l[i]*(el+0.5*ul*ul)))
 #       
 #         print "What the fuCK!?", 0.5*(el+er), states[i].e
 #         self.e_slopes[i] = (er - el)

 #      print "CHECKING: ",
 #      for i in range(len(states)):
 #        
 #         print "Average E", states[i].getConservativeVariables()[2]
 #         el = states[i].e - 0.5*self.e_slopes[i]
 #         er = states[i].e + 0.5*self.e_slopes[i]
 #         ul = mom_l[i]/rho_l[i]
 #         ur = mom_r[i]/rho_r[i]
 #         El = rho_l[i]*(el + 0.5*ul**2)
 #         Er = rho_r[i]*(er + 0.5*ur**2)
 #         print "New E", 0.5*(El+Er)

    ## Creates linear representation for solution using slopes
    #
    def createLinearRepresentation(self, states):

       n = len(states)
       rho_l = np.zeros(n)
       rho_r = np.zeros(n)
       mom_l = np.zeros(n)
       mom_r = np.zeros(n)
       erg_l = np.zeros(n)
       erg_r = np.zeros(n)
       for i in xrange(n):
          rho, mom, erg = states[i].getConservativeVariables()
          rho_l[i] = rho - 0.5*self.rho_slopes[i]
          rho_r[i] = rho + 0.5*self.rho_slopes[i]
          mom_l[i] = mom - 0.5*self.mom_slopes[i]
          mom_r[i] = mom + 0.5*self.mom_slopes[i]
          erg_l[i] = erg - 0.5*self.erg_slopes[i]
          erg_r[i] = erg + 0.5*self.erg_slopes[i]

       return rho_l, rho_r, mom_l, mom_r, erg_l, erg_r


    ## Reconstructs slopes for a single conservative variable
    #
    #  @param[in] u     cell average values for each cell
    #  @param[in] bc_L  value for left boundary ghost cell
    #  @param[in] bc_R  value for right boundary ghost cell
    #
    #  @return limited slopes for each cell
    #
    def slopeReconstruction(self, u, bc_L, bc_R):
    
        # omega of 0 gives centered approximation
        omega = 0.
    
        # compute slopes
        u_slopes = np.zeros(len(u))
        for i in range(len(u)):

            # get neighboring cell values
            if i == 0: # left boundary
               u_L = bc_L
               u_R = u[i+1]
            elif i == len(u)-1: # right boundary
               u_L = u[i-1]
               u_R = bc_R
            else:
               u_L = u[i-1]
               u_R = u[i+1]
            
            # compute differences over left and right edges of cell
            del_L = u[i] - u_L
            del_R = u_R  - u[i]

            # compute tentative slope
            del_i = 0.5*(1.+omega)*del_L + 0.5*(1.-omega)*del_R

            # compute limited slope
            if self.limiter == "minmod":

                del_i = minMod(del_R,del_L)

            elif self.limiter == "vanleer":

                beta = 1.

                #Catch if divide by zero
                if abs(del_R) < 1.0e-15: #0.000000001*(u[i]+0.00001):
                    if abs(del_L) < 1.0e-15: #0.000000001*(u[i]+0.00001):
                        r = 1.0
                    else:
                        r = -1.
                else:
                    r = del_L/del_R
                        
                if r < 0.0 or isinf(r):
                    del_i = 0.0
                else:

                    zeta_R = 2.*beta/(1.-omega+(1.+omega)*r)
                    zeta =  min(2.*r/(1.+r), zeta_R)
                    del_i = zeta*del_i

            elif self.limiter == "none":
                del_i = del_i

            elif self.limiter == "step":
                del_i = 0.0

            else:
                raise ValueError("Invalid slope limiter\n")

            #hardcoded change
  #          print "DEBUG changing how slope is computed in hydroSlopes"
  #          if i == 0:

  #              del_i = u[i+1]-u[i]
  #          elif i==len(u)-1:
  #              del_i = u[i]-u[i-1]


            # save slope
            u_slopes[i] = del_i

        return u_slopes

# ----------------------------------------------------------------------------------
def minMod(a,b):

    if a > 0 and b > 0:
        return min(a,b)
    elif a<0 and b<0:
        return max(a,b)
    else:
        return 0.

