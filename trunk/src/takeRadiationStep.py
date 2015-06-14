## @package src.takeRadiationStep
#  Contains function to take a single radiation time step.

from transientSource import computeRadiationSource,\
                            computeRadiationExtraneousSource
from radiationSolveSS import radiationSolveSS
from globalConstants import SPD_OF_LGT as c


## The parameter \f$\beta\f$ for each time-stepper
#
beta = {"CN":0.5, "BDF2":2./3., "BE":1.}


## Takes single radiation time step
#
#  @param[in] mesh          mesh object
#  @param[in] time_stepper  string identifier for the chosen time-stepper,
#                           e.g., 'CN'
#
def takeRadiationStep(mesh, time_stepper, problem_type, dt,
   cx_new, psi_left, psi_right,
   Qpsi_older, Qpsi_old, Qpsi_new, **kwargs):

   # assert that the appropriate sources were provided
   assert Qpsi_new != None, 'New source must be provided'
   if time_stepper != 'BE':
      assert Qpsi_old != None, 'Old source must be provided for CN or BDF2'
   if time_stepper == 'BDF2':
      assert Qpsi_older != None, 'Older source must be provided for BDF2'

   # evaluate transient source
   Q_tr = computeRadiationSource(
      mesh           = mesh,
      time_stepper   = time_stepper,
      problem_type   = problem_type,
      dt             = dt,
      psi_left       = psi_left,
      psi_right      = psi_right,
      Qpsi_older     = Qpsi_older,
      Qpsi_old       = Qpsi_old,
      Qpsi_new       = Qpsi_new,
      **kwargs)

   # compute diagonal modifier
   alpha = 1./(c*dt)

   # solve transient system
   rad_new = radiationSolveSS(
      mesh           = mesh,
      cross_x        = cx_new,
      Q              = Q_tr,
      bc_psi_left    = psi_left,
      bc_psi_right   = psi_right,
      diag_add_term  = alpha,
      implicit_scale = beta[time_stepper] )

   return rad_new

