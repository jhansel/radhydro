## @package src.hydroSource
#  Contains classes to compute sources for hydrodynamics updates.

from crossXInterface import CrossXInterface
from transientSource import TransientSourceTerm, evalPlanckianOld
from copy            import deepcopy
import globalConstants as GC
import numpy as np
import utilityFunctions as UT
from utilityFunctions import getNu, computeEdgeVelocities, computeEdgeTemperatures,\
   computeEdgeDensities, computeHydroInternalEnergies, evalEdgeSource, \
   evalAverageSource

#--------------------------------------------------------------------------------
## Updates cell-average velocities \f$u_i\f$.
#
#  @param[in]     mesh        mesh object
#  @param[in]     hydro_star  star hydro cell-average states,
#     \f$\mathbf{H}^*_i\f$
#  @param[in,out] hydro_new   new hydro cell-average states,
#     \f$\mathbf{H}^{k+1}_i\f$
#
def updateVelocity(mesh, time_stepper, dt, hydro_star=None, hydro_new=None, **kwargs):
 
    # compute source
    src_handler = VelocityUpdateSourceHandler(mesh, time_stepper)
    Q = src_handler.computeTerm(**kwargs)

    # loop over cells
    for i in range(mesh.n_elems):

        # update velocity
        rho_new = hydro_new[i].rho
        rho_star = hydro_star[i].rho
        u_new = (rho_star*hydro_star[i].u + dt*Q[i]) / rho_new
        hydro_new[i].updateVelocity(u_new)

#--------------------------------------------------------------------------------
## Updates cell-average densities from ext source \f$Q_{rho}\f$.
#
#  @param[in]     mesh        mesh object
#  @param[in]     hydro_star  star hydro cell-average states,
#     \f$\mathbf{H}^*_i\f$
#  @param[in,out] hydro_new   new hydro cell-average states,
#     \f$\mathbf{H}^{k+1}_i\f$
#
def updateDensity(mesh, time_stepper, dt, hydro_star, hydro_new, hydro_prev, **kwargs):
 
    # compute source
    src_handler = DensityUpdateSourceHandler(mesh, time_stepper)
    Q = src_handler.computeTerm(**kwargs)

    # loop over cells
    for i in range(mesh.n_elems):

        # update density
        rho_new = hydro_star[i].rho + dt*Q[i]
        hydro_new[i].updateDensity(rho_new)
        hydro_prev[i].updateDensity(rho_new) #must also update previous

#--------------------------------------------------------------------------------
## Updates internal energy slopes \f$\delta e_i\f$.
#
#  @param[in,out] hydro_new  new hydro unknowns \f$\mathbf{H}^{k+1}\f$,
#    which contains new velocities \f$u_i^{k+1}\f$
#
def updateInternalEnergy(time_stepper, dt, QE, cx_prev, rad_new, hydro_new,
    hydro_prev, hydro_star, slopes_old, e_rad_prev=None, E_slopes_old=None):
 
    # constants
    a = GC.RAD_CONSTANT
    c = GC.SPD_OF_LGT

    # get coefficient corresponding to time-stepper
    scales = {"CN":0.5, "BE":1., "BDF2":2./3.}
    scale = scales[time_stepper]

    # initialize new internal energy slopes
    e_rad_new = np.empty((len(hydro_new),2))

    # loop over cells
    for i in xrange(len(hydro_new)):

        # get hydro states
        state_new  = hydro_new[i]
        state_prev = hydro_prev[i]
        state_star = hydro_star[i]

        # compute edge densities
        rho = computeEdgeDensities(i, state_new, slopes_old)

        # compute edge velocities
        u_new  = computeEdgeVelocities(i, state_new,  slopes_old)

        # compute edge temperatures
        T_prev = computeEdgeTemperatures(state_prev.spec_heat, e_rad_prev[i])

        # compute edge internal energies
        e_prev = e_rad_prev[i]

        #Compute the total energy at left and right
        E_star = [hydro_star[i].E() - 0.5*E_slopes_old[i],
                  hydro_star[i].E() + 0.5*E_slopes_old[i]]

        # Compute the total energy before and after
        E_l = E_star[0]
        E_r = E_star[1]

        # loop over edges to compute new internal energies
        e_new = np.zeros(2)
        for x in range(2):

            # get new quantities
            Er = rad_new.E[i][x]

            # get previous quantities
            aT4 = a*T_prev[x]**4
            sig_a = cx_prev[i][x].sig_a
            spec_heat = state_prev.spec_heat

            # compute effective scattering ratio
            nu = getNu(T_prev[x], sig_a, rho[x], spec_heat, dt, scale)

            # evaluate additional source terms
            QE_elem = QE[i][x]

            # compute new internal energy
            e_new[x] = (1.0-nu)*scale*dt/rho[x] * (sig_a*c*(Er - aT4) + QE_elem/scale)\
               + (1.0-nu)*E_star[x]/rho[x] + nu*e_prev[x]\
               - 0.5*(1.0-nu)*(u_new[x]**2)

        #Compute a new total energy at each edge, that is what we are really
        #conserving and this will ensure regular hydro is unchanged
        E_new = [rho[x]*(0.5*u_new[x]**2 + e_new[x]) for x in range(2)]
        E_new_avg = 0.5*(E_new[0] + E_new[1])
        e_new_avg = E_new_avg/state_new.rho - 0.5*(state_new.u)**2

        # put new internal energy in the new hydro state
        hydro_new[i].updateStateInternalEnergy(e_new_avg)

        # compute new internal energy slope
        for x in range(2):
            e_rad_new[i][x] = e_new[x]


    # return new internal energy slopes
    return e_rad_new


#-----------------------------------------------------------------------------------
## Computes estimated energy gain \f$Q\f$ due to the coupling to radiation energy field
#  based on estimated co-moving frame flux. This is used in the energy update
#  equation in the computation of \f$Q_E\f$:
#  \f[
#      Q = \sigma_t \frac{u}{c} \left(\mathcal{F} - \frac{4}{3}\mathcal{E} u\right)
#  \f]
#
def evalEnergyExchange(i, rad, hydro, cx, slopes):

    # compute edge velocities
    u = computeEdgeVelocities(i, hydro[i], slopes)

    # compute momentum exchange term
    momentum_exchange_term = evalMomentumExchange(i, rad, hydro, cx, slopes)

    return [momentum_exchange_term[x]*u[x] for x in xrange(2)]


#------------------------------------------------------------------------------------
## Compute estimated momentum exchange \f$Q\f$ due to the coupling to radiation,
#  used the in the velocity update equation:
#  \f[
#      Q = \frac{\sigma_t}{c} \left(\mathcal{F} - \frac{4}{3}\mathcal{E} u\right)
#  \f]
#
def evalMomentumExchange(i, rad, hydro, cx, slopes):

    # compute edge velocities
    u = computeEdgeVelocities(i, hydro[i], slopes)

    return [cx[i][x].sig_t/GC.SPD_OF_LGT*(rad.F[i][x]
       - 4.0/3.0*rad.E[i][x]*u[x]) for x in xrange(2)]


#------------------------------------------------------------------------------------
## Computes \f$\sigma_a\phi\f$
#
def evalEnergyAbsorption(i, rad, cx):

    return [rad.phi[i][x]*cx[i][x].sig_a for x in xrange(2)]


## Class to evaluate the \f$Q_E^k\f$ term in linearization.
#
#  It is similar to other terms but with the implicit Planckian removed and
#  angularly integrated quantities.
#
# It utilizes the TransientSource term class to build terms mostly just for
# simplicity of having access to the time stepping algorithms. The ultimate
# return of this function is just a list of tuples of QE for each elem
#
class QEHandler(TransientSourceTerm):

    #-------------------------------------------------------------------------------
    ## Constructor
    #
    def __init__(self, *args):

        # call base class constructor
        TransientSourceTerm.__init__(self, *args)

    #----------------------------------------------------------------------------
    ## Function to evaluate source at all cells in the mesh. Call the base clas
    #  version first, then angularly integrate and form the tuple array we need  
    #
    def computeTerm(self, **kwargs):

        # loop over all cells and build source 
        Q = [[0.0,0.0] for i in range(self.mesh.n_elems)]
        for i in range(self.mesh.n_elems):
            
            # add the source from element i
            Q_elem = list(self.func(i, **kwargs))
            for x in range(2):

                Q[i][x] = Q_elem[x]

        return Q

    #--------------------------------------------------------------------------------
    ## Computes implicit terms in \f$Q_E^k\f$.
    #
    #  There is only an energy exchange term, no Planckian term.
    #
    def evalImplicit(self, i, rad_prev, hydro_prev, cx_prev, slopes_old,
       Qerg_new, **kwargs):

        Q_local = np.array(evalEnergyExchange(i, rad=rad_prev, hydro=hydro_prev,
                           cx=cx_prev, slopes=slopes_old))\
           + np.array(Qerg_new[i])

        return Q_local

    #--------------------------------------------------------------------------------
    ## Evaluate old term. This includes Planckian, as well as energy exchange term
    # 
    def evalOld(self, i, rad_old, hydro_old, cx_old, slopes_old, e_rad_old=None,
       Qerg_old=None, **kwargs):

        Q_local = np.array(evalEnergyAbsorption(i, rad=rad_old, cx=cx_old))\
           - np.array(evalPlanckianOld(i, hydro_old=hydro_old, cx_old=cx_old,
                      e_rad_old=e_rad_old))\
           + np.array(evalEnergyExchange(i, rad=rad_old, hydro=hydro_old, cx=cx_old,
                      slopes=slopes_old))\
           + np.array(Qerg_old[i])
        return Q_local

    #--------------------------------------------------------------------------------
    ## Evaluate older term. Just call the evalOld function as in other source terms
    #
    def evalOlder(self, i, rad_older, hydro_older, cx_older, slopes_older,
       e_rad_older=None, Qerg_older=None, **kwargs):

        return self.evalOld(i, rad_old=rad_older, hydro_old=hydro_older,
           cx_old=cx_older, slopes_old=slopes_older, e_rad_old=e_rad_older,
           Qerg_old=Qerg_older)


## Handles the density update source term
#
class DensityUpdateSourceHandler(TransientSourceTerm):

    #-------------------------------------------------------------------------------
    ## Constructor
    #
    def __init__(self, *args):

        # call base class constructor
        TransientSourceTerm.__init__(self, *args)

    #----------------------------------------------------------------------------
    def computeTerm(self, **kwargs):

        # loop over all cells and build source 
        Q = [0.0 for i in range(self.mesh.n_elems)]
        for i in range(self.mesh.n_elems):
            
            # add the source from element i
            Q_elem = self.func(i, **kwargs)
            Q[i] += Q_elem

        return Q

    #--------------------------------------------------------------------------------
    def evalImplicit(self, i, Qrho_new, **kwargs):

        return Qrho_new[i]

    #--------------------------------------------------------------------------------
    def evalOld(self, i, Qrho_old=None, **kwargs):

        return Qrho_old[i]

    #--------------------------------------------------------------------------------
    def evalOlder(self, i, Qrho_older=None, **kwargs):

        return Qrho_older[i]
    

## Handles velocity update source term.
#
class VelocityUpdateSourceHandler(TransientSourceTerm):

    #-------------------------------------------------------------------------------
    ## Constructor
    #
    def __init__(self, *args):

        # call base class constructor
        TransientSourceTerm.__init__(self, *args)

    #----------------------------------------------------------------------------
    def computeTerm(self, **kwargs):

        # loop over all cells and build source 
        Q = [0.0 for i in range(self.mesh.n_elems)]
        for i in range(self.mesh.n_elems):
            
            # add the source from element i
            Q_elem = self.func(i, **kwargs)
            Q[i] += Q_elem

        return Q

    #--------------------------------------------------------------------------------
    def evalImplicit(self, i, rad_prev, hydro_prev, cx_prev, slopes_old, Qmom_new, **kwargs):

        Q_local = evalMomentumExchangeAverage(i, rad=rad_prev, hydro=hydro_prev,
           cx=cx_prev, slopes=slopes_old) + Qmom_new[i]
        return Q_local

    #--------------------------------------------------------------------------------
    def evalOld(self, i, rad_old, hydro_old, cx_old, slopes_old, Qmom_old, **kwargs):

        Q_local = evalMomentumExchangeAverage(i, rad=rad_old, hydro=hydro_old,
           cx=cx_old, slopes=slopes_old) + Qmom_old[i]
        return Q_local

    #--------------------------------------------------------------------------------
    def evalOlder(self, i, rad_older, hydro_older, cx_older, slopes_older, Qmom_older, **kwargs):

        Q_local = evalMomentumExchangeAverage(i, rad=rad_older, hydro=hydro_older,
           cx=cx_older, slopes=slopes_older) + Qmom_older[i]
        return Q_local


#------------------------------------------------------------------------------------
## Compute the momentum exchange term in the momentum equation,
#  \f$
#      Q = \frac{\sigma_t}{c} \left(F - \frac{4}{3}E u\right)
#  \f$.
#
def evalMomentumExchangeAverage(i, rad, hydro, cx, slopes):

#    # compute average cross section
#    sig_t = 0.5*cx[i][0].sig_t + 0.5*cx[i][1].sig_t
#
#    # compute average radiation quantities
#    E = 0.5*rad.E[i][0] + 0.5*rad.E[i][1]
#    F = 0.5*rad.F[i][0] + 0.5*rad.F[i][1]
#
#    # compute momentum exchange term
#    Q = sig_t/GC.SPD_OF_LGT*(F - 4.0/3.0*E*hydro[i].u)

    # speed of light
    c = GC.SPD_OF_LGT

    # compute edge velocities
    uL, uR = computeEdgeVelocities(i, hydro[i], slopes)

    # compute momentum exchange term at edges and then average
    QL = cx[i][0].sig_t/c*(rad.F[i][0] - 4.0/3.0*rad.E[i][0]*uL)
    QR = cx[i][1].sig_t/c*(rad.F[i][1] - 4.0/3.0*rad.E[i][1]*uR)
    Q = 0.5*(QL + QR)

    return Q


## Computes an extraneous source vector for the momentum equation,
#  \f$Q^{ext,\rho u}\f$, evaluated at each cell center.
#
#  @param[in] mom_src  function handle for the momentum extraneous source
#  @param[in] mesh     mesh
#  @param[in] t        time at which to evaluate the function
#
#  @return list of the momentum extraneous source function evaluated
#          at each cell center, \f$Q^{ext,\rho u}_i\f$
#
def computeMomentumExtraneousSource(mom_src, mesh, t):

   # Compute average of momentum source
   src = np.zeros(mesh.n_elems)
   for i in xrange(mesh.n_elems):

      el = mesh.getElement(i)
      x_l = el.xl
      x_r = el.xr

      src[i] = evalAverageSource(mom_src, x_l, x_r, t) 

   return src

## Computes an extraneous source vector for the energy equation,
#  \f$Q^{ext,E}\f$, evaluated at each cell edge.
#
#  @param[in] erg_src  function handle for the energy extraneous source
#  @param[in] mesh     mesh
#  @param[in] t        time at which to evaluate the function
#
#  @return list of tuples of the energy extraneous source function evaluated
#          at each edge on each cell, \f$(Q^{ext,E}_{i,L},Q^{ext,E}_{i,R})\f$
#
def computeEnergyExtraneousSource(erg_src, mesh, t):

   # evaluate energy source function at each edge of each cell
   src = []
   for i in xrange(mesh.n_elems):

      el = mesh.getElement(i)
      x_l = el.xl
      x_r = el.xr

      #Compute two basis moments of function
      src.append(  evalEdgeSource(erg_src, x_l, x_r, t) )

   return src





