## @package src.newtonStateHanlder
#  This file contains a class to handle computing linearized source
#  terms and handles temperature updates during a non-linear TRT solve.
#  Also contains auxilary functions for evaluating TRT functions of interest
#
#  This class is eventually passed to the source builder as source. Although it is
#  has additional features, it is easier to have this class directly implement the
#  evalImplicit etc. functions than using forwarding functions and potentially having
#  the wrong states.
#
#  The documentation for the linearization and solution of non-linear system 
#  derives in detail the equations being generated here.
#
from musclHancock    import HydroState
from transientSource import TransientSourceTerm
from crossXInterface import CrossXInterface
from copy            import deepcopy
import globalConstants as GC
import numpy as np
import utilityFunctions as UT

#===================================================================================
## Main class to handle newton solve and temperature updates, etc.
#
class NewtonStateHandler(TransientSourceTerm):

    #--------------------------------------------------------------------------------
    ## Constructor
    #
    # @param [in] mesh            spatial mesh 
    # @param [in] delta_t         The time step size is required throughout class
    # @param [in] time_stepper    What type of time stepping method, e.g., 'BE'
    # @param [in] hydro_states_implicit  The initial guess for hydro states at end of
    #                             time step. These WILL be modified. Stored in usual
    #                             tuple format (L,R)
    #                               TODO have the constructor adjust star to use rad
    #                               slopes
    #
    def __init__(self,mesh,cx_new=None,hydro_states_implicit=None,time_stepper='BE'):

        TransientSourceTerm.__init__(self,mesh,time_stepper)

        #store scale coefficient from time discretization for computing nu
        scale = {"CN":0.5, "BE":1., "BDF2":2./3.}
        self.mesh = mesh
        self.time_stepper = time_stepper
        self.scale = scale[time_stepper]

        #Store the (initial) implicit hydro_states at t_{n+1}. These WILL be modified
        self.hydro_states = hydro_states_implicit

        #Store the cross sections, you will be updating these 
        self.cx_new = cx_new

    #---------------------------------------------------------------------------------
    def getFinalHydroStates():

        #destroy the hydro states so no one accidentally reuses these for now
        temp_states = self.hydro_states
        self.hydro_states = []

        return temp_states


    #--------------------------------------------------------------------------------
    ## Function to generate effective cross sections for linearization. 
    #  
    #  The effective re-emission source is included as a scattering cross section
    #  given by
    #  \f[
    #      \tilde{\sigma_s} = \sigma_s + \sigma_a(T^k)*\nu
    #  \f]
    #  It is noted that \nu is different for the different time stepping algorithms
    #
    # @param [in] cx_orig    Pass in the original cross sections, these are NOT
    #                        modified. Return effective cross section
    #
    def getEffectiveOpacities(self, dt):

        cx_effective = []
        cx_orig = self.cx_new #local reference

        # loop over cells:
        for i in range(len(cx_orig)):

            cx_i = []

            # calculate at left and right
            for x in range(2): 

                #Get the guessed temperature from states
                state = self.hydro_states[i][x]
                T     = state.getTemperature()
                rho   = state.rho

                #Make sure cross section is updated with temperature
                cx_orig[i][x].updateCrossX(rho,T) #if constant this call does nothing

                #Calculate the effective scattering cross sections
                sig_a_og = cx_orig[i][x].sig_a
                sig_s_og = cx_orig[i][x].sig_s
                nu    = getNu(T,sig_a_og,state.rho,state.spec_heat,dt,self.scale)
            
                #Create new FIXED cross section instance
                cx_i.append( CrossXInterface(sig_a_og, sig_s_og + nu*sig_a_og) )

            cx_effective.append(tuple(cx_i))

        return cx_effective

    #--------------------------------------------------------------------------------
    ## Function to evaluate Q_E^k in documentation. This is essentially everything
    #  else from the linearization that isnt included elsewhere
    #
    def getQE():

        if self.time_stepper == "BE":

            return 0.0
        else:

            raise NotImplementedError("Not really sure what to do here yet")

    #--------------------------------------------------------------------------------
    ## Compute a new internal energy in each of the states, based on a passed in
    #  solution for E^{k+1}
    #
    def updateIntEnergy(self, E, dt, hydro_states_star=None):

        #constants
        a = GC.RAD_CONSTANT
        c = GC.SPD_OF_LGT

        if self.time_stepper != 'BE':

            raise NotImplementedError("This only works for BE currently")

        #loop over cells
        for i in xrange(len(self.hydro_states)):

            #loop over left and right value
            for x in range(2):

                #get temperature for this cell, at indice k, we are going to k+1
                state = self.hydro_states[i][x]
                T_prev  = state.getTemperature()
                e_prev = state.e

                #old state from hydro
                state_star = hydro_states_star[i][x]
                e_star = state_star.e

                print E[i][x]*c

                sig_a = self.cx_new[i][x].sig_a
                nu    = getNu(T_prev,sig_a,state.rho,state.spec_heat,dt,self.scale)

                #Calculate planckian from T_prev (t_k)
                planck_prev = sig_a*a*c*T_prev**4.
                
                #Calculate a new internal energy and store it (NEED SCALE FACTORS)
                e_new = (1.-nu) * dt/state.rho * (sig_a*c*E[i][x] - planck_prev) \
                        + (1.-nu)*e_star + nu*e_prev
                self.hydro_states[i][x].e = e_new

                print "New temps: ", i, self.hydro_states[i][x].getTemperature()

        c = GC.SPD_OF_LGT
    

    #================================================================================
    #   The following functions are for the TransientSourceTerm class
    #--------------------------------------------------------------------------------
    ## Evaluate implicit term
    #
    # param [in] hydro_states_star  If there is no material motion, this is simply
    #                               the hydro states at t_n. But if there is material
    #                               motion these come from the MUSCL hancock. It is
    #                               assumed they have been adjusted to use the
    #                               correct slope before this function is called
    #
    def evalImplicit(self, i, hydro_states_star=None, dt=None,**kwargs):
        
        #calculate at left and right, isotropic emission source
        cx_new = self.cx_new #local reference
        planckian = [0.0,0.0]
        for x in range(2):

            #get temperature for this cell, at indice k
            state = self.hydro_states[i][x]
            T     = state.getTemperature()

            #old state from hydro
            state_star = hydro_states_star[i][x]

            #Update cross section just in case
            cx_new[i][x].updateCrossX(state.rho,T)

            sig_a = cx_new[i][x].sig_a
            nu    = getNu(T,sig_a,state.rho,state.spec_heat,dt,self.scale)

            #Calculate planckian
            emission = (1. - nu )*sig_a*GC.RAD_CONSTANT*GC.SPD_OF_LGT*T**4.
            
            #add in additional term from internal energy
            planckian[x] = emission - (nu*state.rho/(self.scale*dt) 
                    * (state.e  - state_star.e ) )

        #Store the (isotropic) sources in correct index
        Q = np.zeros(4)
        Q[UT.getLocalIndex("L","-")] = 0.5*planckian[0]
        Q[UT.getLocalIndex("L","+")] = 0.5*planckian[0]
        Q[UT.getLocalIndex("R","-")] = 0.5*planckian[1]
        Q[UT.getLocalIndex("R","+")] = 0.5*planckian[1]
        
        return Q

    #--------------------------------------------------------------------------------
    ## Evaluate implicit term
    #
    def evalOld(self, **kwargs):

        raise NotImplementedError("not done")

    #--------------------------------------------------------------------------------
    ## Evaluate BDF2 older term
    #
    def evalOlder(self, **kwargs):

        raise NotImplementedError("not done")

#=====================================================================================
# Miscellaneous functions that do not need to be a member function
#=====================================================================================
#
#--------------------------------------------------------------------------------
## Evaluate nu in linearization at a arbitrary temperature 'T'
#
def getNu(T, sig_a, rho, spec_heat, dt, scale):

    c_dt = GC.SPD_OF_LGT*dt
    beta = 4.*GC.RAD_CONSTANT * T * T * T / spec_heat #DU_R/De

    #Evaluate numerator
    num  = scale*sig_a*c_dt*beta/rho

    return num/(1. + num)




