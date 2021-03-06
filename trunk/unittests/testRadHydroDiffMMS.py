## @package unittests.testRadHydroMMS
#  Contains unittest class to test an MMS problem with the full
#  radiation-hydrodynamics scheme

# add source directory to module search path
import sys
sys.path.append('../src')

# symbolic math packages
from sympy import symbols, exp, sin, sympify, cos, diff
from math import pi
from sympy.utilities.lambdify import lambdify

import pickle

from scipy.optimize import fmin

# numpy
import numpy as np
import math
from math import sqrt

# unit test package
import unittest

# local packages
from createMMSSourceFunctions import createMMSSourceFunctionsRadHydro
from mesh import Mesh
from hydroState import HydroState, getIntErg
from radiation import Radiation
from plotUtilities import plotHydroSolutions, plotTemperatures, plotRadErg, plotS2Erg
from utilityFunctions import computeRadiationVector, computeAnalyticHydroSolution,\
   computeHydroL2Error, computeHydroConvergenceRates, printHydroConvergenceTable,\
   computeAnalyticRadSolution
from crossXInterface import ConstantCrossSection
from transient import runNonlinearTransient
from hydroBC import HydroBC
from radBC import RadBC
import globalConstants as GC
import radUtilities as RU

## Derived unittest class to test the MMS source creator functions
##
class TestRadHydroMMS(unittest.TestCase):
   def setUp(self):
      pass
   def tearDown(self):
      pass
   def test_RadHydroMMS(self):
      
      # declare symbolic variables
      x, t, alpha, c, a, mu  = symbols('x t alpha c a mu')
      
      # number of refinement cycles
      n_cycles = 5

      # number of elements in first cycle
      n_elems = 20

      # We will increase sigma and nondimensional C as we decrease the mesh
      # size to ensure we stay in the diffusion limit
      
      # numeric values
      gamma_value = 5./3.
      cv_value = 0.14472799784454
      
      # run for a fixed amount of time 
      t_end = 2.*pi
      sig_s = 0.0

      #Want material speeed to be a small fraction of speed of light
      #and radiation to be small relative to kinetic energy
      P = 0.001   # a_r T_inf^4/(rho_inf*u_inf^2)

      #Arbitrary ratio of pressure to density
      alpha_value = 0.5 

      #Arbitrary mach number well below the sound speed.  The choice of gamma and
      #the cv value, as well as C and P constrain all other material reference
      #parameters, but we are free to choose the material velocity below the sound
      #speed to ensure no shocks are formed
      M = 0.9
      cfl_value = 0.6  #but 2 time steps, so really like a CFL of 0.3

      dt = []
      dx = []
      err = []

      for cycle in range(n_cycles):
      
          #Keep ratio of  and sig_a*dx constant, staying in diffusion limit
          C = sig_a = 100000./20*n_elems   # c/a_inf
          sig_t = sig_s + sig_a

          a_inf = GC.SPD_OF_LGT/C

          #These lines of code assume specified C_v
          T_inf = a_inf**2/(gamma_value*(gamma_value-1.)*cv_value)
          rho_inf = GC.RAD_CONSTANT*T_inf**4/(P*a_inf**2)

          #Specify rho_inf and determine T_inf and Cv_value
          rho_inf = 1.0  #If we don't choose a reference density, then the specific heat values get ridiculous
          T_inf = pow(rho_inf*P*a_inf**2/GC.RAD_CONSTANT,0.25)  #to set T_inf based on rho_inf,
          cv_value = a_inf**2/(T_inf*gamma_value*(gamma_value-1.)) # to set c_v, if rho specified

          #Specify T_inf and solve for rho_inf and C_v value
    #      T_inf = 1
     #     rho_inf = GC.RAD_CONSTANT*T_inf**4/(P*a_inf**2)
     #     cv_value = a_inf**2/(T_inf*gamma_value*(gamma_value-1.)) # to set c_v, if rho specified

          #Same for all approachs
          p_inf = rho_inf*a_inf*a_inf

          print "The dimensionalization parameters are: "
          print "   a_inf : ", a_inf
          print "   T_inf : ", T_inf
          print " rho_inf : ", rho_inf
          print "   p_inf : ", p_inf
          print "     C_v : ", cv_value
          print "   gamma : ", gamma_value

          # create solution for thermodynamic state and flow field
          rho = rho_inf*(2. + sin(x-t))
          u   = a_inf*M*0.5*(2. + cos(x-t))
          p   = alpha_value*p_inf*(2. + cos(x-t))
          e = p/(rho*(gamma_value-1.))
          E = 0.5*rho*u*u + rho*e
          
          # create solution for radiation field based on solution for F 
          # that is the leading order diffusion limit solution
          T = e/cv_value
          Er = a*T**4
          Fr = -1./(3.*sig_t)*c*diff(Er,x) + sympify('4./3.')*Er*u

          #Form psi+ and psi- from Fr and Er
          psip = (Er*c*mu + Fr)/(2.*mu)
          psim = (Er*c*mu - Fr)/(2.*mu)

          # create functions for exact solutions
          substitutions = dict()
          substitutions['alpha'] = alpha_value
          substitutions['c']     = GC.SPD_OF_LGT
          substitutions['a']     = GC.RAD_CONSTANT
          substitutions['mu']    = RU.mu["+"]
          rho = rho.subs(substitutions)
          u   = u.subs(substitutions)
          mom = rho*u
          E   = E.subs(substitutions)
          psim = psim.subs(substitutions)
          psip = psip.subs(substitutions)
          T    = T.subs(substitutions)
          rho_f  = lambdify((symbols('x'),symbols('t')), rho,  "numpy")
          u_f    = lambdify((symbols('x'),symbols('t')), u,    "numpy")
          mom_f  = lambdify((symbols('x'),symbols('t')), mom,  "numpy")
          E_f    = lambdify((symbols('x'),symbols('t')), E,    "numpy")
          psim_f = lambdify((symbols('x'),symbols('t')), psim, "numpy")
          psip_f = lambdify((symbols('x'),symbols('t')), psip, "numpy")
          T_f    = lambdify((symbols('x'),symbols('t')), T,    "numpy")

          Er = Er.subs(substitutions)
          Er      = lambdify((symbols('x'),symbols('t')), Er, "numpy")

          #For reference create lambda as ratio of aT^4/rho--u^2 to check
          #P_f = lambda x,t: GC.RAD_CONSTANT*T_f(x,t)**4/(rho_f(x,t)*u_f(x,t)**2)
          #dx = 1./100.
          #x = -1.*dx
          #t=0.2
          #for i in range(100):
          #    x += dx
          #    print "ratio:", P_f(x,t)

          # create MMS source functions
          rho_src, mom_src, E_src, psim_src, psip_src = createMMSSourceFunctionsRadHydro(
             rho           = rho,
             u             = u,
             E             = E,
             psim          = psim,
             psip          = psip,
             sigma_s_value = sig_s,
             sigma_a_value = sig_a,
             gamma_value   = gamma_value,
             cv_value      = cv_value,
             alpha_value   = alpha_value,
             display_equations = True)

          # mesh
          width = 2.*pi
          mesh = Mesh(n_elems,width)

          # compute hydro IC for the sake of computing initial time step size

          hydro_IC = computeAnalyticHydroSolution(mesh,t=0.0,
             rho=rho_f, u=u_f, E=E_f, cv=cv_value, gamma=gamma_value)

          # compute the initial time step size according to CFL conditon (actually
          # half). We will then decrease this time step by the same factor as DX each
          # cycle
          if cycle == 0:

              sound_speed = [sqrt(i.p * i.gamma / i.rho) + abs(i.u) for i in hydro_IC]
              dt_vals = [cfl_value*(mesh.elements[i].dx)/sound_speed[i]
                 for i in xrange(len(hydro_IC))]
              dt_value = min(min(dt_vals),0.5) #don't take too big of time step
            
              print "initial dt_value", dt_value

              #Adjust the end time to be an exact increment of dt_values
              print "old t_end: ", t_end
              print "new t_end: ", t_end

          print "This cycle's dt value: ", dt_value

          # create uniform mesh
          mesh = Mesh(n_elems, width)

          dt.append(dt_value)
          dx.append(mesh.getElement(0).dx)

          # compute radiation IC
          psi_IC = computeRadiationVector(psim_f, psip_f, mesh, t=0.0)
          rad_IC = Radiation(psi_IC)

          # create rad BC object
          rad_BC = RadBC(mesh, 'periodic')

          # compute hydro IC
          hydro_IC = computeAnalyticHydroSolution(mesh,t=0.0,
             rho=rho_f, u=u_f, E=E_f, cv=cv_value, gamma=gamma_value)

          # Dimensionless parameters. These are all evaluated at peaks of trig
          # functions, very hard coded
          print "---------------------------------------------"
          print " Diffusion limit info:"
          print "---------------------------------------------"
          print "Size in mfp of cell", mesh.getElement(0).dx*sig_t
          print "Ratio of radiation energy to kinetic", Er(0.75,0)/(rho_f(0.25,0)*u_f(0.0,0)**2), GC.RAD_CONSTANT*T_inf**4/(rho_inf*a_inf**2)
          print "Ratio of speed of light to material sound speed", GC.SPD_OF_LGT/u_f(0.0,0), GC.SPD_OF_LGT/(a_inf)
          print "---------------------------------------------"

          # create hydro BC
          hydro_BC = HydroBC(bc_type='periodic', mesh=mesh)
      
          # create cross sections
          cross_sects = [(ConstantCrossSection(sig_s, sig_s+sig_a),
                          ConstantCrossSection(sig_s, sig_s+sig_a))
                          for i in xrange(mesh.n_elems)]

          # transient options
          t_start  = 0.0

          # if run standalone, then be verbose
          if __name__ == '__main__':
             verbosity = 2
          else:
             verbosity = 0

          #slope limiter
          limiter = 'double-minmod'
          
          # run the rad-hydro transient
          rad_new, hydro_new = runNonlinearTransient(
             mesh         = mesh,
             problem_type = 'rad_hydro',
             dt_option    = 'constant',
             dt_constant  = dt_value,
             slope_limiter = limiter,
             time_stepper = 'BDF2',
             use_2_cycles = True,
             t_start      = t_start,
             t_end        = t_end,
             rad_BC       = rad_BC,
             cross_sects  = cross_sects,
             rad_IC       = rad_IC,
             hydro_IC     = hydro_IC,
             hydro_BC     = hydro_BC,
             mom_src      = mom_src,
             E_src        = E_src,
             rho_src      = rho_src,
             psim_src     = psim_src,
             psip_src     = psip_src,
             verbosity    = verbosity,
             rho_f =rho_f,
             u_f = u_f,
             E_f = E_f,
             gamma_value = gamma_value,
             cv_value = cv_value,
             check_balance = True)

          # compute exact hydro solution
          hydro_exact = computeAnalyticHydroSolution(mesh, t=t_end,
             rho=rho_f, u=u_f, E=E_f, cv=cv_value, gamma=gamma_value)

          rad_exact = computeAnalyticRadSolution(mesh, t_end,psim=psim_f,psip=psip_f)
 
          #Compute error
          err.append(computeHydroL2Error(hydro_new, hydro_exact, rad_new, rad_exact ))

          n_elems  *= 2
          dt_value *= 0.5

          # compute convergence rates
          rates_dx = computeHydroConvergenceRates(dx,err)
          rates_dt = computeHydroConvergenceRates(dt,err)

          # print convergence table
          if n_cycles > 1:
             printHydroConvergenceTable(dx,err,rates=rates_dx,
                dx_desc='dx',err_desc='$L_2$')
             printHydroConvergenceTable(dt,err,rates=rates_dt,
                dx_desc='dt',err_desc='$L_2$')

      # plot
      if __name__ == '__main__':

         # compute exact hydro solution
         hydro_exact = computeAnalyticHydroSolution(mesh, t=t_end,
            rho=rho_f, u=u_f, E=E_f, cv=cv_value, gamma=gamma_value)


         # plot hydro solution
         plotHydroSolutions(mesh, hydro_new, x_exact=mesh.getCellCenters(),exact=hydro_exact)

         #plot exact and our E_r
         Er_exact_fn = 1./GC.SPD_OF_LGT*(psim + psip)
         Fr_exact_fn = (psip - psim)*RU.mu["+"]
         Er_exact = []
         Fr_exact = []
         psip_exact = []
         psim_exact = []
         x = mesh.getCellCenters()
         for xi in x:
             
             substitutions = {'x':xi, 't':t_end}
             Er_exact.append(Er_exact_fn.subs(substitutions))
             Fr_exact.append(Fr_exact_fn.subs(substitutions))
             psip_exact.append(psip_f(xi,t_end))
             psim_exact.append(psim_f(xi,t_end))

         plotRadErg(mesh, rad_new.E, Fr_edge=rad_new.F, exact_Er=Er_exact, exact_Fr =
               Fr_exact)

         plotS2Erg(mesh, rad_new.psim, rad_new.psip, exact_psim=psim_exact,
                 exact_psip=psip_exact)

         plotTemperatures(mesh, rad_new.E, hydro_states=hydro_new, print_values=True)

         #Make a pickle to save the error tables
         from sys import argv
         pickname = "results/testRadHydroDiffMMS.pickle"
         if len(argv) > 2:
            if argv[1] == "-o":
               pickname = argv[2].strip()

         #Create dictionary of all the data
         big_dic = {"dx": dx}
         big_dic["dt"] =  dt
         big_dic["Errors"] = err
         pickle.dump( big_dic, open( pickname, "w") )
         
               
               
         

# run main function from unittest module
if __name__ == '__main__':
   unittest.main()

