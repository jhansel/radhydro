## @package src.transient
#  Contains functions to run transients.

from copy import deepcopy
import numpy as np
from math import sqrt

from nonlinearSolve import nonlinearSolve
from utilityFunctions import computeL2RelDiff
from transientSource import computeRadiationExtraneousSource
from hydroSource import computeMomentumExtraneousSource,\
   computeEnergyExtraneousSource
from takeRadiationStep import takeRadiationStep
from hydroSlopes import HydroSlopes
from musclHancock import hydroPredictor, hydroCorrector

## Runs transient for a radiation-only problem.
#
#  @param[in] psim_src  extraneous source function for \f$\Psi^-\f$
#  @param[in] psip_src  extraneous source function for \f$\Psi^+\f$
#
def runLinearTransient(mesh, time_stepper,
   psi_left, psi_right, cross_sects, rad_IC, psim_src, psip_src,
   dt_option='constant', dt_constant=None, t_start=0.0, t_end=1.0, verbose=False):

   # check input arguments
   if dt_option == 'constant':
      assert dt_constant is not None, "If time step size option is chosen to \
         be 'constant', then a time step size must be provided."

   # initialize time and solutions
   t = t_start
   rad_old = rad_IC
   Qpsi_old = computeRadiationExtraneousSource(psim_src, psip_src, mesh, t_start)
   rad_older  = None
   Qpsi_older = None
   
   # transient loop
   time_index = 0
   transient_incomplete = True # boolean flag signalling end of transient
   while transient_incomplete:

       # increment time index
       time_index += 1

       # if first step, then can't use BDF2
       if time_index == 1 and time_stepper == 'BDF2':
          time_stepper_this_step = 'BE'
       else:
          time_stepper_this_step = time_stepper

       # get time step size
       if dt_option == 'constant':
          dt = dt_constant
       else:
          raise NotImplementedError('Invalid time step size option')
  
       # adjust time step size if it would overshoot the end of the transient
       if t + dt >= t_end:
          dt = t_end - t
          t = t_end
          transient_incomplete = False # signal end of transient
       else:
          t += dt

       # print each time step
       if verbose:
          print("Time step %d: t = %f -> %f:" % (time_index,t-dt,t))

       # compute new extraneous source
       Qpsi_new = computeRadiationExtraneousSource(psim_src, psip_src, mesh, t)
  
       # take radiation step
       #
       # NOTE: In this case, cross sections are assumed to be constant
       #       with respect to time because cross sections are generally
       #       functions of material properties, and there is no coupling
       #       to material physics in a radiation-only problem.
       #
       rad_new = takeRadiationStep(
          mesh          = mesh,
          time_stepper  = time_stepper_this_step,
          problem_type  = 'rad_only',
          dt            = dt,
          psi_left      = psi_left,
          psi_right     = psi_right,
          cx_older      = cross_sects,
          cx_old        = cross_sects,
          cx_new        = cross_sects,
          rad_older     = rad_older,
          rad_old       = rad_old,
          Qpsi_older    = Qpsi_older,
          Qpsi_old      = Qpsi_old,
          Qpsi_new      = Qpsi_new)

       # save older solutions
       Qpsi_older = deepcopy(Qpsi_old)
       rad_older  = deepcopy(rad_old)

       # save old solutions
       Qpsi_old   = deepcopy(Qpsi_new)
       rad_old    = deepcopy(rad_new)

   # return final solution
   return rad_new


## Runs transient for a nonlinear radiation-material problem.
#
#  @param[in] add_ext_src  flag to signal that extraneous sources are to be added
#  @param[in] psim_src  extraneous source function for \f$\Psi^-\f$
#  @param[in] psip_src  extraneous source function for \f$\Psi^+\f$
#  @param[in] mom_src   extraneous source function for the conservation
#                       of momentum equation
#  @param[in] E_src     extraneous source function for the conservation
#                       of total energy equation
#
def runNonlinearTransient(mesh, problem_type,
   psi_left, psi_right, cross_sects, rad_IC, hydro_IC,
   psim_src=None, psip_src=None, mom_src=None, E_src=None,
   time_stepper='BE', dt_option='constant', dt_constant=None, CFL=0.5, t_start=0.0,
   t_end=1.0, use_2_cycles=False, verbose=False):

   # check input arguments
   if dt_option == 'constant':
      assert dt_constant != None, "If time step size option is chosen to \
         be 'constant', then a time step size must be provided."

   # initialize old quantities
   t_old = t_start
   cx_old = deepcopy(cross_sects)
   rad_old = rad_IC
   hydro_old = hydro_IC
   e_slopes_old = np.zeros(mesh.n_elems)
   Qpsi_old, Qmom_old, Qerg_old = computeExtraneousSources(
      psim_src, psip_src, mom_src, E_src, mesh, t_start)

   # set older quantities to nothing; these shouldn't exist yet
   cx_older       = None
   rad_older      = None
   hydro_older    = None
   slopes_older   = None
   e_slopes_older = None
   Qpsi_older     = None
   Qmom_older     = None
   Qerg_older     = None
   
   # transient loop
   time_index = 0
   transient_incomplete = True # boolean flag signalling end of transient
   while transient_incomplete:

       # increment time index
       time_index += 1

       # if first step, then can't use BDF2
       if time_index == 1 and time_stepper == 'BDF2':
          time_stepper_this_step = 'BE'
       else:
          time_stepper_this_step = time_stepper

       # get time step size
       if dt_option == 'constant':
          # constant time step size
          dt = dt_constant
       elif dt_option == 'CFL':
          # compute time step size according to CFL condition
          sound_speed = [sqrt(i.p * i.gamma / i.rho) + abs(i.u) for i in hydro_old]
          dt_vals = [CFL*(mesh.elements[i].dx)/sound_speed[i]
             for i in range(len(hydro_old))]
          dt = min(dt_vals)

          # if using 2 cycles, then twice the time step size may be taken
          if use_2_cycles:
             dt *= 2.0
       else:
          raise NotImplementedError('Invalid time step size option')
  
       # adjust time step size if it would overshoot the end of the transient
       if t_old + dt >= t_end:
          dt = t_end - t_old
          t_new = t_end
          transient_incomplete = False # signal end of transient
       else:
          t_new = t_old + dt

       # print each time step
       if verbose:
          print("\nTime step %d: t = %f -> %f:" % (time_index,t_old,t_new))
  
       # take time step
       if problem_type == 'rad_mat':

          # take time step without MUSCL-Hancock
          hydro_new, rad_new, cx_new, slopes_old, e_slopes_new,\
          Qpsi_new, Qmom_new, Qerg_new =\
             takeTimeStepRadiationMaterial(
             mesh         = mesh,
             time_stepper = time_stepper_this_step,
             dt           = dt,
             psi_left     = psi_left,
             psi_right    = psi_right,
             cx_old       = cx_old,
             cx_older     = cx_older,
             hydro_old    = hydro_old,
             hydro_older  = hydro_older,
             rad_old      = rad_old,
             rad_older    = rad_older,
             slopes_older = slopes_older,
             e_slopes_old = e_slopes_old,
             e_slopes_older = e_slopes_older,
             psim_src     = psim_src,
             psip_src     = psip_src,
             mom_src      = mom_src,
             E_src        = E_src,
             t_old        = t_old,
             Qpsi_old     = Qpsi_old,
             Qmom_old     = Qmom_old,
             Qerg_old     = Qerg_old,
             Qpsi_older   = Qpsi_older,
             Qmom_older   = Qmom_older,
             Qerg_older   = Qerg_older)

       else:

          # if user chose to use the 2-cycle scheme
          if use_2_cycles:

             print("  Cycle 1:")

             # take time step with MUSCL-Hancock
             hydro_half, rad_half, cx_half, slopes_old, e_slopes_half,\
             Qpsi_half, Qmom_half, Qerg_half =\
                takeTimeStepMUSCLHancock(
                mesh           = mesh,
                dt             = 0.5*dt, 
                psi_left       = psi_left,
                psi_right      = psi_right,
                cx_old         = cx_old,
                cx_older       = cx_older,
                hydro_old      = hydro_old,
                hydro_older    = hydro_older,
                rad_old        = rad_old,
                rad_older      = rad_older,
                slopes_older   = slopes_older,
                e_slopes_old   = e_slopes_old,
                e_slopes_older = e_slopes_older,
                time_stepper_predictor='CN',
                time_stepper_corrector='CN',
                psim_src     = psim_src,
                psip_src     = psip_src,
                mom_src      = mom_src,
                E_src        = E_src,
                t_old        = t_old,
                Qpsi_old     = Qpsi_old,
                Qmom_old     = Qmom_old,
                Qerg_old     = Qerg_old,
                Qpsi_older   = Qpsi_older,
                Qmom_older   = Qmom_older,
                Qerg_older   = Qerg_older)

             print("  Cycle 2:")

             # take time step with MUSCL-Hancock
             hydro_new, rad_new, cx_new, slopes_half, e_slopes_new,\
             Qpsi_new, Qmom_new, Qerg_new =\
                takeTimeStepMUSCLHancock(
                mesh           = mesh,
                dt             = 0.5*dt, 
                psi_left       = psi_left,
                psi_right      = psi_right,
                cx_old         = cx_half,
                cx_older       = cx_old,
                hydro_old      = hydro_half,
                hydro_older    = hydro_old,
                rad_old        = rad_half,
                rad_older      = rad_old,
                slopes_older   = slopes_old,
                e_slopes_old   = e_slopes_half,
                e_slopes_older = e_slopes_old,
                time_stepper_predictor='CN',
                time_stepper_corrector='BDF2',
                psim_src     = psim_src,
                psip_src     = psip_src,
                mom_src      = mom_src,
                E_src        = E_src,
                t_old        = t_old + 0.5*dt,
                Qpsi_old     = Qpsi_half,
                Qmom_old     = Qmom_half,
                Qerg_old     = Qerg_half,
                Qpsi_older   = Qpsi_old,
                Qmom_older   = Qmom_old,
                Qerg_older   = Qerg_old)

          else:

             # for first step, can't use BDF2; use CN instead
             if time_index == 1:
                time_stepper_corrector = 'CN'
             else:
                time_stepper_corrector = 'BDF2'
            
             # take time step with MUSCL-Hancock
             hydro_new, rad_new, cx_new, slopes_old, e_slopes_new,\
             Qpsi_new, Qmom_new, Qerg_new =\
                takeTimeStepMUSCLHancock(
                mesh           = mesh,
                dt             = dt, 
                psi_left       = psi_left,
                psi_right      = psi_right,
                cx_old         = cx_old,
                cx_older       = cx_older,
                hydro_old      = hydro_old,
                hydro_older    = hydro_older,
                rad_old        = rad_old,
                rad_older      = rad_older,
                slopes_older   = slopes_older,
                e_slopes_old   = e_slopes_old,
                e_slopes_older = e_slopes_older,
                time_stepper_predictor='CN',
                time_stepper_corrector=time_stepper_corrector,
                psim_src     = psim_src,
                psip_src     = psip_src,
                mom_src      = mom_src,
                E_src        = E_src,
                t_old        = t_old,
                Qpsi_old     = Qpsi_old,
                Qmom_old     = Qmom_old,
                Qerg_old     = Qerg_old,
                Qpsi_older   = Qpsi_older,
                Qmom_older   = Qmom_older,
                Qerg_older   = Qerg_older)

       # save older solutions
       cx_older  = deepcopy(cx_old)
       rad_older = deepcopy(rad_old)
       hydro_older = deepcopy(hydro_old)
       slopes_older = deepcopy(slopes_old)
       e_slopes_older = deepcopy(e_slopes_old)
       Qpsi_older = deepcopy(Qpsi_old)
       Qmom_older = deepcopy(Qmom_old)
       Qerg_older = deepcopy(Qerg_old)

       # save old solutions
       t_old = t_new
       cx_old  = deepcopy(cx_new)
       rad_old = deepcopy(rad_new)
       hydro_old = deepcopy(hydro_new)
       e_slopes_old = deepcopy(e_slopes_new)
       Qpsi_old = deepcopy(Qpsi_new)
       Qmom_old = deepcopy(Qmom_new)
       Qerg_old = deepcopy(Qerg_new)

   # return final solutions
   return rad_new, hydro_new


## Takes time step without any MUSCL-Hancock.
#
#  This should only be called if the problem type is 'rad_mat'.
#
def takeTimeStepRadiationMaterial(mesh, time_stepper, dt, psi_left, psi_right,
   cx_old, cx_older, hydro_old, hydro_older, rad_old, rad_older,
   slopes_older, e_slopes_old, e_slopes_older,
   psim_src, psip_src, mom_src, E_src, t_old, Qpsi_old, Qmom_old, Qerg_old,
   Qpsi_older, Qmom_older, Qerg_older):

       # compute new extraneous sources
       Qpsi_new, Qmom_new, Qerg_new = computeExtraneousSources(
          psim_src, psip_src, mom_src, E_src, mesh, t_old+dt)

       # compute slopes
       # NOTE: do we need to prevent limiters from being applied to slopes
       # in this case?
       slopes_old = HydroSlopes(hydro_old)

       # if there is no material motion, then the homogeneous hydro solution
       # should be equal to the old hydro solution
       hydro_star = deepcopy(hydro_old)

       # perform nonlinear solve
       hydro_new, rad_new, cx_new, e_slopes_new = nonlinearSolve(
          mesh         = mesh,
          time_stepper = time_stepper,
          problem_type = 'rad_mat',
          dt           = dt,
          psi_left     = psi_left,
          psi_right    = psi_right,
          cx_old       = cx_old,
          cx_older     = cx_older,
          hydro_old    = hydro_old,
          hydro_older  = hydro_older,
          hydro_star   = hydro_star,
          rad_old      = rad_old,
          rad_older    = rad_older,
          slopes_old   = slopes_old,
          slopes_older = slopes_older,
          e_slopes_old = e_slopes_old,
          e_slopes_older = e_slopes_older,
          Qpsi_new     = Qpsi_new,
          Qmom_new     = Qmom_new,
          Qerg_new     = Qerg_new,
          Qpsi_old     = Qpsi_old,
          Qmom_old     = Qmom_old,
          Qerg_old     = Qerg_old,
          Qpsi_older   = Qpsi_older,
          Qmom_older   = Qmom_older,
          Qerg_older   = Qerg_older)

       return hydro_new, rad_new, cx_new, slopes_old, e_slopes_new,\
          Qpsi_new, Qmom_new, Qerg_new


## Takes time step with MUSCL-Hancock.
#
#  This should only be called if the problem type is 'rad_hydro'.
#
def takeTimeStepMUSCLHancock(mesh, dt, psi_left, psi_right,
   cx_old, cx_older, hydro_old, hydro_older, rad_old, rad_older,
   slopes_older, e_slopes_old, e_slopes_older,
   psim_src, psip_src, mom_src, E_src, t_old,
   Qpsi_old, Qmom_old, Qerg_old, Qpsi_older, Qmom_older, Qerg_older,
   time_stepper_predictor='CN', time_stepper_corrector='BDF2'):

       # assert that BDF2 was not chosen for the predictor time-stepper
       assert time_stepper_predictor != 'BDF2', 'BDF2 cannot be used in\
          the predictor step.'

       # compute new extraneous sources
       Qpsi_half, Qmom_half, Qerg_half = computeExtraneousSources(
          psim_src, psip_src, mom_src, E_src, mesh, t_old+0.5*dt)

       # compute slopes
       slopes_old = HydroSlopes(hydro_old)

       # perform predictor step of MUSCL-Hancock
       hydro_star = hydroPredictor(mesh, hydro_old, slopes_old, dt)

       print "    Predictor step:"

       # perform nonlinear solve
       hydro_half, rad_half, cx_half, e_slopes_half = nonlinearSolve(
          mesh         = mesh,
          time_stepper = time_stepper_predictor,
          problem_type = 'rad_hydro',
          dt           = 0.5*dt,
          psi_left     = psi_left,
          psi_right    = psi_right,
          cx_old       = cx_old,
          hydro_old    = hydro_old,
          hydro_star   = hydro_star,
          rad_old      = rad_old,
          slopes_old   = slopes_old,
          e_slopes_old = e_slopes_old,
          Qpsi_new     = Qpsi_half,
          Qmom_new     = Qmom_half,
          Qerg_new     = Qerg_half,
          Qpsi_old     = Qpsi_old,
          Qmom_old     = Qmom_old,
          Qerg_old     = Qerg_old,
          Qpsi_older   = Qpsi_older, # this is a dummy argument
          Qmom_older   = Qmom_older, # this is a dummy argument
          Qerg_older   = Qerg_older) # this is a dummy argument

       print "    Corrector step:"

       # compute new extraneous sources
       Qpsi_new, Qmom_new, Qerg_new = computeExtraneousSources(
          psim_src, psip_src, mom_src, E_src, mesh, t_old+dt)

       # perform corrector step of MUSCL-Hancock
       hydro_star = hydroCorrector(mesh, hydro_half, dt)

       # perform nonlinear solve
       hydro_new, rad_new, cx_new, e_slopes_new = nonlinearSolve(
          mesh         = mesh,
          time_stepper = time_stepper_corrector,
          problem_type = 'rad_hydro',
          dt           = dt,
          psi_left     = psi_left,
          psi_right    = psi_right,
          cx_old       = cx_old,
          cx_older     = cx_older,
          hydro_old    = hydro_old,
          hydro_older  = hydro_older,
          hydro_star   = hydro_star,
          rad_old      = rad_old,
          rad_older    = rad_older,
          slopes_old   = slopes_old,
          slopes_older = slopes_older,
          e_slopes_old = e_slopes_old,
          e_slopes_older = e_slopes_older,
          Qpsi_new     = Qpsi_new,
          Qmom_new     = Qmom_new,
          Qerg_new     = Qerg_new,
          Qpsi_old     = Qpsi_old,
          Qmom_old     = Qmom_old,
          Qerg_old     = Qerg_old,
          Qpsi_older   = Qpsi_older,
          Qmom_older   = Qmom_older,
          Qerg_older   = Qerg_older)

       return hydro_new, rad_new, cx_new, slopes_old, e_slopes_new,\
          Qpsi_new, Qmom_new, Qerg_new


## Computes all extraneous sources
#
def computeExtraneousSources(psim_src, psip_src, mom_src, E_src, mesh, t):

   # compute radiation extraneous source
   if psim_src != None and psip_src != None:
      Qpsi = computeRadiationExtraneousSource(psim_src, psip_src, mesh, t)
   else:
      Qpsi = np.zeros(mesh.n_elems*4)

   # compute momentum extraneous source
   if mom_src != None:
      Qmom = computeMomentumExtraneousSource(mom_src, mesh, t)
   else:
      Qmom = np.zeros(mesh.n_elems)

   # compute energy extraneous source
   if E_src != None:
      Qerg = computeEnergyExtraneousSource(E_src, mesh, t)
   else:
      Qerg = [(0.0,0.0) for i in xrange(mesh.n_elems)]

   return Qpsi, Qmom, Qerg


