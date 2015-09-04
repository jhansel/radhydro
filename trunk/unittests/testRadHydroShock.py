## @package unittests.testRadHydroShock
#  Contains unittest class to test a radiation-hydrodyamics shock problem.

# add source directory to module search path
import sys
sys.path.append('../src')

# unit test package
import unittest

# local packages
from mesh import Mesh
from hydroState import HydroState
from radiation import Radiation
from plotUtilities import plotHydroSolutions, plotTemperatures, plotS2Erg
from utilityFunctions import computeRadiationVector, computeAnalyticHydroSolution
from crossXInterface import ConstantCrossSection
from transient import runNonlinearTransient
from hydroBC import HydroBC
from radBC   import RadBC
import globalConstants as GC

## Derived unittest class to test the radiation-hydrodynamics shock problem
#
class TestRadHydroShock(unittest.TestCase):
   def setUp(self):
      pass
   def tearDown(self):
      pass
   def test_RadHydroShock(self):

      # test case
      test_case = "marcho2" # mach1.2 mach2 mach50 marcho1.05
      
      # create uniform mesh
      n_elems = 50
      width = 0.04
      x_start = -0.02
      mesh_center = x_start + 0.5*width
      mesh = Mesh(n_elems, width, x_start=x_start)

      # gamma constant
      gam = 5.0/3.0
 
      # material 1 and 2 properties: Table 6.1
      sig_a1 = 390.71164263502122
      sig_s1 = 853.14410158161809 -sig_a1
      c_v1   = 0.12348
      sig_a2 = sig_a1
      sig_s2 = sig_s1
      c_v2   = c_v1

      if test_case == "mach1.2": # Mach 1.2 problem: Table 6.2

         # material 1 IC
         rho1   = 1.0
         E1     = 2.2226400000000000e-02
         u1     = 1.4055888445772469e-01
         e1     = E1/rho1 - 0.5*u1*u1
         Erad_left = 1.372E-06

         # material 2 IC
         rho2   = 1.2973213452231311
         E2     = 2.6753570531538713e-002
         u2     = 1.0834546504247138e-001
         e2     = E2/rho2 - 0.5*u2*u2
         Erad_right = 2.7955320762182542e-06

         # final time
         t_end = 1.2

         # temperature plot filename
         test_filename = "radshock_mach1.2.pdf"

         # temperature plot exact solution filename
         exact_solution_filename = "mach1.2_exact_solution.csv"

      elif test_case == "mach2": # Mach 2 problem: Table 6.3

         # material 1 IC
         rho1   = 1.0
         E1     = 3.9788000000000004e-002
         u1     = 2.3426480742954117e-001
         e1     = E1/rho1 - 0.5*u1*u1
         T1     = e1/c_v1
         Erad_left = 1.372E-06

         # material 2 IC
         rho2   = 2.2860748989303659e+000
         E2     = 7.0649692950433357e-002
         u2     = 1.0247468599526272e-001
         e2     = E2/rho2 - 0.5*u2*u2
         T2     = e2/c_v2
         Erad_right = 2.5560936967521927e-005

         print "rho", rho1, rho2
         print "vel", u1, u2
         print "Temperature", T1, T2
         print "momentum", rho1*u1, rho2*u2
         print "E",E1, E2
         print "E_r",Erad_left, Erad_right

         # final time
         t_end = 1.0

         # temperature plot output filename
         test_filename = "radshock_mach2.pdf"

         # temperature plot exact solution filename
         exact_solution_filename = "mach2_exact_solution.csv"

      elif test_case == "mach50": # Mach 50 problem: Table 6.4

         raise NotImplementedError("Mach 50 test requires negativity monitoring," \
            + "which is not yet implemented.")

         # material 1 IC
         rho1   = 1.0
         E1     = 1.7162348000000001e+001
         u1     = 5.8566201857385289e+000
         e1     = E1/rho1 - 0.5*u1*u1
         Erad_left = 1.372E-06

         # material 2 IC
         rho2   = 6.5189217901173153e+000
         E2     = 9.5144308747326214e+000
         u2     = 8.9840319830453630e-001
         e2     = E2/rho2 - 0.5*u2*u2
         Erad_right = 7.3372623010289956e+001

         # final time
         t_end = 1.5

         # temperature plot filename
         test_filename = "radshock_mach50.pdf"

         # temperature plot exact solution filename
         exact_solution_filename = "mach50_exact_solution.csv"

      elif test_case == "marcho2":

         # material 1 IC
         rho1   = 1.0
         u1     = 0.23426480742954117
         T1     = 1.219999999999999973e-01
         e1     = T1*c_v2
         E1     = 0.5*rho1*u1*u1 + e1*rho1
         Erad_left = 3.039477120074432e-06

         # material 2 IC
         rho2   = 2.286074898930029242
         u2     = 0.10247468599526272
         T2     = 2.534635394302977573e-01
         e2     = T2*c_v2
         E2     = 0.5*rho2*u2*u2 + e2*rho2
         Erad_right = 5.662673693907908e-05


         print "rho", rho1, rho2
         print "vel", u1, u2
         print "Temperature", T1, T2
         print "momentum", rho1*u1, rho2*u2
         print "E",E1, E2
         print "E_r",Erad_left, Erad_right

         # final time
         t_end = 0.10

         # temperature plot filename
         test_filename = "radshock_mach50.pdf"

         # temperature plot exact solution filename
         exact_solution_filename = "marcho2_exact_solution.csv"

      elif test_case == "marcho1.05":

         # material 1 IC
         rho1   = 1.0
         u1     = 0.1228902
         T1     = 0.1
         e1     = T1*c_v2
         E1     = 0.5*rho1*u1*u1 + e1*rho1
         Erad_left = 1.372E-06

         # material 2 IC
         rho2   = 1.0749588
         u2     = rho1*u1/rho2
         T2     = 0.1049454
         e2     = T2*c_v2
         E2     = 0.5*rho2*u2*u2 + e2*rho2
         Erad_right = 1.664211799256650E-06
         print "rho", rho1, rho2
         print "vel", u1, u2
         print "Temperature", T1, T2
         print "momentum", rho1*u1, rho2*u2
         print "E",E1, E2
         print "E_r",Erad_left, Erad_right




         # final time
         t_end = 1.0

         # temperature plot filename
         test_filename = "radshock_mach50.pdf"

         # temperature plot exact solution filename
         exact_solution_filename = "marcho1.05_exact_solution.csv"
         exact_solution_filename = None


      else:
         raise NotImplementedError("Invalid test case")
         
      # compute radiation BC; assumes BC is independent of time
      c = GC.SPD_OF_LGT
      # NOTE: What is the justification for this? Does Jarrod assume Fr = 0?
      psi_left  = 0.5*c*Erad_left  
      psi_right = 0.5*c*Erad_right

      #Create BC object
      rad_BC = RadBC(mesh, "dirichlet", psi_left=psi_left, psi_right=psi_right)
      
      # construct cross sections and hydro IC
      cross_sects = list()
      hydro_IC = list()
      psi_IC = list()

      for i in range(mesh.n_elems):  
      
         if mesh.getElement(i).x_cent < mesh_center: # material 1
            cross_sects.append( (ConstantCrossSection(sig_s1, sig_s1+sig_a1),
                                 ConstantCrossSection(sig_s1, sig_s1+sig_a1)) )
            hydro_IC.append(
               HydroState(u=u1,rho=rho1,e=e1,spec_heat=c_v1,gamma=gam))

            psi_IC += [psi_left for dof in range(4)]

         else: # material 2
            cross_sects.append((ConstantCrossSection(sig_s2, sig_a2+sig_s2),
                                ConstantCrossSection(sig_s2, sig_a2+sig_s2)))
            hydro_IC.append(
               HydroState(u=u2,rho=rho2,e=e2,spec_heat=c_v2,gamma=gam))

            psi_IC += [psi_right for dof in range(4)]

      #Smooth out the middle solution
      n_smoothed = 0
      state_l = hydro_IC[0]
      state_r = hydro_IC[-1]
        
      rho_l =  state_l.rho
      rho_r =  state_r.rho
      drho  = rho_r - rho_l
      u_l   =  state_l.u
      u_r   =  state_r.u
      du    = u_r - u_l
      e_l   =  state_l.e
      e_r   =  state_r.e
      de    = e_r-e_l

      #Scale
      idx = 0
      if n_smoothed > 0:
          for i in range(mesh.n_elems/2-n_smoothed/2-1,mesh.n_elems/2+n_smoothed/2):

              rho = rho_l + drho*idx/n_smoothed
              u   = rho_l*u_l/rho
              e   = e_l + de*idx/n_smoothed

              idx+=1

              E   = 0.5*rho*u*u + rho*e
              hydro_IC[i].updateState(rho, rho*u, E)

      plotHydroSolutions(mesh, hydro_IC)

      rad_IC = Radiation(psi_IC)

      # create hydro BC
      hydro_BC = HydroBC(bc_type='fixed', mesh=mesh, state_L = state_l,
            state_R = state_r)
      hydro_BC = HydroBC(bc_type='reflective', mesh=mesh)

      # transient options
      t_start  = 0.0

      # if run standalone, then be verbose
      if __name__ == '__main__':
         verbosity = 2
      else:
         verbosity = 0
      
      # run the rad-hydro transient
      rad_new, hydro_new = runNonlinearTransient(
         mesh         = mesh,
         problem_type = 'rad_hydro',
         dt_option    = 'CFL',
         CFL          = 0.6,
         use_2_cycles = True,
         t_start      = t_start,
         t_end        = t_end,
         rad_BC       = rad_BC,
         cross_sects  = cross_sects,
         rad_IC       = rad_IC,
         hydro_IC     = hydro_IC,
         hydro_BC     = hydro_BC,
         verbosity    = verbosity,
         slope_limiter = 'vanleer',
         check_balance=True)

      # plot
      if __name__ == '__main__':

         # compute exact hydro solution
         hydro_exact = None

         # plot hydro solution
         plotHydroSolutions(mesh, hydro_new, exact=hydro_exact)

         # plot material and radiation temperatures
         plotTemperatures(mesh, rad_new.E, hydro_states=hydro_new, print_values=False,
            save=False, filename=test_filename,
            exact_solution_filename=exact_solution_filename)

         plotS2Erg(mesh, rad_new.psim, rad_new.psip)

# run main function from unittest module
if __name__ == '__main__':
   unittest.main()

