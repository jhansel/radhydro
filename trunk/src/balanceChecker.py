## @package src.balanceChecker
#  Contains a class to compute balance

import numpy as np
import radUtilities as RU
import globalConstants as GC
from math import sqrt

## Default dictionary to pass to balance checker
#
empty_srcs = {"rad":0.0,"mass":0.0,"erg":0.0,"mom":0.0}


#================================================================================
## Balance checker class
#
#================================================================================
class BalanceChecker:

    #----------------------------------------------------------------------------
    ## Constructor. 
    #
    #  @param[in] mesh          need spatial mesh for volumes
    #  @param[in] time_stepper  not implemented for all methods necessarily
    #  @param[in] dt            assumed constant essentially
    #----------------------------------------------------------------------------
    def __init__(self, mesh, problem_type, timestepper, dt):

        self.mesh = mesh
        self.time_stepper  = timestepper
        self.dt   = dt
        self.prob = problem_type

    #----------------------------------------------------------------------------
    ## Compute balance on a simple steady state problem
    #  Constructor
    #
    def computeSSRadBalance(self, psi_left, psi_right, rad, sigma_a, Q_iso):

        #assume uniform volume
        vol = self.mesh.getElement(0).dx

        #get Cell invegrated quantities
        sources = sum([Q_iso*2*vol for i in rad.phi])
        absor = sum([0.5*(i[0]+i[1])*vol*sigma_a for i in rad.phi])

        #Get currents
        mu = RU.mu["+"]
        j_in = (psi_left*mu + psi_right*mu)
        j_out= rad.psim[0][0]*mu + rad.psip[-1][1]*mu

        bal = j_in - j_out + sources - absor
        
        print "\n====================================================="
        print "Balance Check"
        print "====================================================="
        print "    Absorption Rate:   %.6e" % absor
        print "            Sources:   %.6e" % sources
        print "Current in:            %.6e" % (j_in)
        print "Current out:           %.6e" % (j_out)
        print "-----------------------------------------------------"
        print "    Absolute Balance:  %.6e" % bal
        print "    Relative Balance:  %.6e" % (bal/(sources))
        print "=====================================================\n"

        return 

    #----------------------------------------------------------------------------
    ## Compute balance for a TRT only problem with no velocity
    #
    def computeBalance(self, psi_left, psi_right, hydro_old,
            hydro_new, rad_old, rad_new, hydro_F_left=None, hydro_F_right=None, 
            Q_ext={"rad":0.0,"mass":0.0,"erg":0.0,"mom":0.0}, write=True):

        #assume uniform volume
        vol = self.mesh.getElement(0).dx
        dt  = self.dt

        #get Cell invegrated quantities
        Er_new = sum([0.5*(i[0]+i[1])*vol for i in rad_new.E])
        Er_old = sum([0.5*(i[0]+i[1])*vol for i in rad_old.E])
        em_new = sum([i.e*vol*i.rho for i in hydro_new])
        em_old = sum([i.e*vol*i.rho for i in hydro_old])

        #Get currents
        mu = RU.mu["+"]
        j_in = (psi_left*mu + psi_right*mu)
        j_out_new = rad_new.psim[0][0]*mu + rad_new.psip[-1][1]*mu

        #Compute mass balance
        mass_new = sum([i.rho*vol for i in hydro_new])
        mass_old = sum([i.rho*vol for i in hydro_old])

        #Compute kinetic energy
        KE_new = sum([vol*(0.5*i.rho*i.u**2) for i in hydro_new])
        KE_old = sum([vol*(0.5*i.rho*i.u**2) for i in hydro_old])

        #Compute total momentum
        mom_new = sum([vol*(i.rho*i.u) for i in hydro_new])
        mom_old = sum([vol*(i.rho*i.u) for i in hydro_old])

        if (self.time_stepper == 'BE' and self.prob == 'rad_mat'):

            erg_bal = em_new + Er_new - Er_old - em_old - (j_in - j_out_new)*dt 
            mass_bal = mass_new - mass_old
            mom_bal = mom_new - mom_old

        elif (self.prob == 'rad_hydro'):

            mass_bal = mass_new - mass_old + dt*(hydro_F_right["rho"] -
                hydro_F_left["rho"])
            mom_bal = mom_new - mom_old + dt*(hydro_F_right["mom"] -
                hydro_F_left["mom"])
            erg_bal = em_new + KE_new - em_old - KE_old + dt*(hydro_F_right["erg"] -
                    hydro_F_left["erg"])

                
        #simple balance
        if (write):

            print "\n====================================================="
            print "Balance Check"
            print "====================================================="
            print "New energy radiation:  %.6e" % Er_new
            print "Old energy radiation:  %.6e" % Er_old
            print "Current in:            %.6e" % (j_in*dt)
            print "Current out:           %.6e" % (j_out_new*dt)
            print "-----------------------------------------------------"
            print "New energy material:   %.6e" % em_new
            print "Old energy material:   %.6e" % em_old
            print "New kinetic energy:    %.6e" % (KE_new)
            print "Old kinetic energy:    %.6e" % (KE_old) 
            print "mass flux left:        %.6e" % (hydro_F_left["rho"]*dt) 
            print "momentum flux left:    %.6e" % (hydro_F_left["mom"]*dt) 
            print "energy flux left:      %.6e" % (hydro_F_left["erg"]*dt) 
            print "mass flux right:       %.6e" % (hydro_F_right["rho"]*dt)
            print "momentum flux right:   %.6e" % (hydro_F_right["mom"]*dt)
            print "energy flux right:     %.6e" % (hydro_F_right["erg"]*dt)
            print "-----------------------------------------------------"
            print "        Mass Balance (Relative):  %.6e (%.6e)" % (mass_bal, mass_bal/(mass_new))
            print "    Momentum Balance (Relative):  %.6e (%.6e)" % (mom_bal, mom_bal/(mom_new))
            print "      Energy Balance (Relative):  %.6e (%.6e)" % (erg_bal, erg_bal/(em_new+Er_new))
            print "=====================================================\n"


            


