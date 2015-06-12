
import numpy as np
import matplotlib as plt
from pylab import *
from math import sqrt, isinf
from copy import deepcopy
from utilityFunctions import *
from hydroState import HydroState
from hydroSlopes import HydroSlopes

#--------------------------------------------------------------------------------------
## Main is my original hydro code, we shouldnt need this anymore but it is here
# temporarily in case we need it to compare
#def main():
#    
#    #Python requires indentation for nested functions etc.  It is best to use a text
#    #editor that allows for tabs to be expanded as spaces
#    width = 1.0
#    t_end = 0.05
#
#    t = 0.0
#    cfl = 0.5
#    n = 500
#    dx = width/n
#    gamma = 1.4 #gas constant
#
#    if n % 2 != 0: #simple error raise, % has lots of diff meanings in python
#        raise ValueError("Must be even number of cells")
#
#    #Choose riemann solver
#    riem_solver = HLLCSolver #HLLSolver, HLLCSolver
#
#    #Left and right BC and initial values
#    p_left = 1.0
#    u_left  = .750
#    rho_left = 1.
#
#    p_right = 0.1
#    u_right = 0.0
#    rho_right = 0.125
#
#    #pick initial time step
#    c_init = max(sqrt(gamma*p_left/rho_left)+u_left,sqrt(gamma*p_right/rho_right)+u_right)
#    dt_init = cfl*dx/c_init
#
#    #Can create lists of things in multiple ways
#    spat_coors = []
#    xi = 0.0
#    for i in range(n+1): #range(3) = [0,1,2], "for" iterates over "each" i "in" list
#        spat_coors.append(xi)
#        xi += dx
#    x = np.array(spat_coors) #Similar to a matlab vector
#    x_cent = [0.5*(x[i]+x[i+1]) for i in range(len(x)-1)] #for plotting cell centers
#
#    n_left = int(0.3*n)
#    n_right = int(0.7*n)
#
#    #Create cell centered variables
#    states = [HydroState(u=u_left,p=p_left,gamma=gamma,rho=rho_left) for i in range(n_left)]
#    states = states + [HydroState(u=u_right,p=p_right,gamma=gamma,rho=rho_right) for i in
#            range(n_right)]
#
#    #-----------------------------------------------------------------
#    # Solve Problem
#    #----------------------------------------------------------------
#    
#    #initialize dt
#    dt = dt_init
#
#    #loop over time steps
#    while (t < t_end):
#        t += dt
#
#        #shorten last step to be exact
#        if (t > t_end):
#            t -= dt
#            dt = t_end - t + 0.000000001
#            t += dt
#
#        print("t = %f -> %f" % (t-dt,t))
#
#        #Create vectors of conserved quantities
#        rho = [s.rho for s in states]
#        mom = [s.rho*s.u for s in states]
#        erg = [s.rho*(0.5*s.u*s.u + s.e) for s in states]
#
#        #Predict values by advecting each thing
#        rho_l, rho_r = slopeReconstruction(rho)
#        mom_l, mom_r = slopeReconstruction(mom)
#        erg_l, erg_r = slopeReconstruction(erg)
#
#        #Compute left and right states
#        states_l = [deepcopy(i) for i in states] #initialize 
#        states_r = [deepcopy(i) for i in states]
#
#        for i in range(len(rho_l)):
#            states_l[i].updateState(rho_l[i], mom_l[i], erg_l[i])
#            states_r[i].updateState(rho_r[i], mom_r[i], erg_r[i])
#
#        #Initialize predicited conserved quantities
#        rho_l_p = [0.0 for i in range(len(rho_l))]
#        rho_r_p = [0.0 for i in range(len(rho_l))]
#        mom_l_p = [0.0 for i in range(len(rho_l))]
#        mom_r_p = [0.0 for i in range(len(rho_l))]
#        erg_l_p = [0.0 for i in range(len(rho_l))]
#        erg_r_p = [0.0 for i in range(len(rho_l))]
#
#        #Advance in time each edge variable
#        for i in range(len(rho_l)):
#    
#            #rho
#            rho_l_p[i] = advCons(rho_l[i],dx,0.5*dt,rhoFlux(states_l[i]),rhoFlux(states_r[i])) 
#            rho_r_p[i] = advCons(rho_r[i],dx,0.5*dt,rhoFlux(states_l[i]),rhoFlux(states_r[i])) 
#
#            #mom
#            mom_l_p[i] = advCons(mom_l[i],dx,0.5*dt,momFlux(states_l[i]),momFlux(states_r[i])) 
#            mom_r_p[i] = advCons(mom_r[i],dx,0.5*dt,momFlux(states_l[i]),momFlux(states_r[i])) 
#
#            #erg
#            erg_l_p[i] = advCons(erg_l[i],dx,0.5*dt,ergFlux(states_l[i]),ergFlux(states_r[i])) 
#            erg_r_p[i] = advCons(erg_r[i],dx,0.5*dt,ergFlux(states_l[i]),ergFlux(states_r[i])) 
#
#        #Advance the primitive variables at the edges
#        for i in range(len(rho_l)):
#            states_l[i].updateState(rho_l_p[i], mom_l_p[i], erg_l_p[i])
#            states_r[i].updateState(rho_r_p[i], mom_r_p[i], erg_r_p[i])
#
#        #Solve for fluxes and values at faces
#        rho_F = [0.0 for i in range(n+1)]
#        mom_F = [0.0 for i in range(n+1)]
#        erg_F = [0.0 for i in range(n+1)]
#
#        #Solve Riemann problem at each face, for each quantity
#        #For boundaries it is easily defined
#        rho_F[0] = rhoFlux(states_l[0])
#        mom_F[0] = momFlux(states_l[0])
#        erg_F[0] = ergFlux(states_l[0])
#
#        rho_F[-1] = rhoFlux(states_r[-1])
#        mom_F[-1] = momFlux(states_r[-1])
#        erg_F[-1] = ergFlux(states_r[-1])
#
#        for i in range(0,n-1):
#
#            rho_F[i+1] = riem_solver(rho_r_p[i], rho_l_p[i+1], states_r[i],
#                    states_l[i+1], rhoFlux)
#            mom_F[i+1] = riem_solver(mom_r_p[i], mom_l_p[i+1], states_r[i],
#                    states_l[i+1], momFlux)
#            erg_F[i+1] = riem_solver(erg_r_p[i], erg_l_p[i+1], states_r[i],
#                    states_l[i+1], ergFlux)
#
#        #Advance conserved values based on edge fluxes
#        for i in range(len(rho)):
#
#            rho[i] = advCons(rho[i],dx,dt,rho_F[i],rho_F[i+1])
#            mom[i] = advCons(mom[i],dx,dt,mom_F[i],mom_F[i+1])
#            erg[i] = advCons(erg[i],dx,dt,erg_F[i],erg_F[i+1])
#
#        #Advance primitive variables
#        for i in range(len(states)):
#            states[i].updateState(rho[i],mom[i],erg[i])
#        
#        #Compute a new time step
#        c = [sqrt(i.p*i.gamma/i.rho)+abs(i.u) for i in states]
#        dt_vals = [cfl*(x[i+1]-x[i])/c[i] for i in range(len(c))]
#        dt = min(dt_vals)
#
#    # plot solution
#    plotHydroSolutions(x,states)


#-------------------------------------------------------------------------------------
#
## Predictor solver for hydro.
#
# Boundary Conditions: Essentially boundaries are treated as reflective. The fluxes
# on the boundary are just estimated based on the flux based on the edge state at
# that node. There is no need to pass in the boundary conditions then.
#
# @param[in] mesh           Basic spatial mesh object
# @param[in] states_old_a   Averages at old state. 
# @param[in] dt             time step size for this hydro solve. To predict values at 
#                           0.5 dt, pass in 1.0 dt
# 
# @return
#       -#  predicted states at averages
#       -#  predicted states slopes
#
def hydroPredictor(mesh, states_old_a, slopes, dt):

    dx = mesh.getElement(0).dx #currently a fixed width

    if mesh.n_elems % 2 != 0: #simple error raise, % has lots of diff meanings in python
        raise ValueError("Must be even number of cells")

    #Can create lists of things in multiple ways
    spat_coors = []
    for i in mesh.elements:
        spat_coors += [i.xl]
    spat_coors += [mesh.elements[-1].xr]
    x = np.array(spat_coors)
    x_cent = mesh.getCellCenters()

    #Initialize cell centered variables as passed in
    states = states_old_a

    #-----------------------------------------------------------------
    # Solve Problem
    #----------------------------------------------------------------

    #Create vectors of conserved quantities
    rho = [s.rho                     for s in states]
    mom = [s.rho*s.u                 for s in states]
    erg = [s.rho*(0.5*s.u*s.u + s.e) for s in states]

    # extract slopes
    rho_slopes, mom_slopes, erg_slopes = slopes.extractSlopes()

    # compute linear representations
    rho_l, rho_r = createLinearRepresentation(rho,rho_slopes)
    mom_l, mom_r = createLinearRepresentation(mom,mom_slopes)
    erg_l, erg_r = createLinearRepresentation(erg,erg_slopes)

    #Compute left and right states
    states_l = [deepcopy(i) for i in states] #initialize 
    states_r = [deepcopy(i) for i in states]
    for i in range(len(rho_l)):
        states_l[i].updateState(rho_l[i], mom_l[i], erg_l[i])
        states_r[i].updateState(rho_r[i], mom_r[i], erg_r[i])

    #Initialize predicited conserved quantities
    rho_p = [0.0 for i in range(len(rho))]
    mom_p = [0.0 for i in range(len(rho))]
    erg_p = [0.0 for i in range(len(rho))]

    #Advance in time each edge variable
    for i in range(len(rho)):

        #rho
        rho_p[i] = advCons(rho[i],dx,0.5*dt,rhoFlux(states_l[i]),rhoFlux(states_r[i])) 

        #mom
        mom_p[i] = advCons(mom[i],dx,0.5*dt,momFlux(states_l[i]),momFlux(states_r[i])) 

        #erg
        erg_p[i] = advCons(erg[i],dx,0.5*dt,ergFlux(states_l[i]),ergFlux(states_r[i])) 
        
    #Advance the primitive variables
    for i in range(len(rho)):
        states[i].updateState(rho_p[i], mom_p[i], erg_p[i])

    #Return states at left and right values
    return states

    
#-------------------------------------------------------------------------------------
#
## Corrector solver for hydro.
#
# The corrector solve takes in a predicted state at dt/2, and computes new values at
# dt.  The input is averages and slopes, the output is new averages, with the slopes
# un-adjusted.
#
# The slopes are defined based on the following relation in a cell:
# 
# \f$U(x) = U_a + \frac{2U_x}{h_x}(x - x_i) \f$
#
# Thus, \f$U_R = U_a + U_x\f$ and \f$U_L = U_a - U_x\f$, and 
# \f$U_x = \frac{U_R - U_L}{2}\f$
#
# @param[in] mesh           Basic spatial mesh object
# @param[in] states_old_a   Averages at old state. 
# @param[in] states_l       Predicted values at left nodes, at dt/2
# @param[in] states_r       Predicted values at right nodes, at dt/2
# @param[in] delta_t        time step size for this hydro solve. To predict values at 
#                           0.5 dt, pass in 1.0 dt
# 
#
# @return
#       -#  predicted states averages
#
def hydroCorrector(mesh, states_old_a, dt):

    #Choose riemann solver
    riem_solver = HLLCSolver #HLLSolver, HLLCSolver

    #Solve for fluxes and values at faces
    n = mesh.n_elems
    rho_F = np.zeros(n+1)
    mom_F = np.zeros(n+1)
    erg_F = np.zeros(n+1)

    #Create vectors of predicted variables
    rho_p = [s.rho                     for s in states_old_a]
    mom_p = [s.rho*s.u                 for s in states_old_a]
    erg_p = [s.rho*(0.5*s.u*s.u + s.e) for s in states_old_a]

    #Solve Rieman problem at each face, for each quantity
    #For boundaries it is easily defined
    rho_F[0] = rhoFlux(states_old_a[0])
    mom_F[0] = momFlux(states_old_a[0])
    erg_F[0] = ergFlux(states_old_a[0])

    rho_F[-1] = rhoFlux(states_old_a[-1])
    mom_F[-1] = momFlux(states_old_a[-1])
    erg_F[-1] = ergFlux(states_old_a[-1])

    for i in range(0,n-1):

        rho_F[i+1] = riem_solver(rho_p[i], rho_p[i+1], states_old_a[i],
                states_old_a[i+1], rhoFlux)
        mom_F[i+1] = riem_solver(mom_p[i], mom_p[i+1], states_old_a[i],
                states_old_a[i+1], momFlux)
        erg_F[i+1] = riem_solver(erg_p[i], erg_p[i+1], states_old_a[i],
                states_old_a[i+1], ergFlux)

    #Intialize cell average quantity arrays at t_old
    rho = [s.rho for s in states_old_a]
    mom = [s.rho*s.u for s in states_old_a]
    erg = [s.rho*(0.5*s.u**2. + s.e) for s in states_old_a]

    #Advance conserved values at centers based on edge fluxes
    for i in range(len(rho)):

        dx = mesh.getElement(i).dx

        #Example of edge fluxes:
        #   i is 0 for 1st element, so edge 0 and edge 1 is i and i+1
        rho[i] = advCons(rho[i],dx,dt,rho_F[i],rho_F[i+1])
        mom[i] = advCons(mom[i],dx,dt,mom_F[i],mom_F[i+1])
        erg[i] = advCons(erg[i],dx,dt,erg_F[i],erg_F[i+1])

    #Advance primitive variables
    states_a = [deepcopy(i) for i in states_old_a] 
    for i in range(len(states_a)):
        states_a[i].updateState(rho[i],mom[i],erg[i])

    return states_a

#------------------------------------------------------------------------------------
# Define some functions for evaluating fluxes for different state variables
#------------------------------------------------------------------------------------
def rhoFlux(s):
    return s.rho*s.u

def momFlux(s):
    return s.rho*s.u*s.u+s.p

def ergFlux(s):
    return (s.rho*(0.5*s.u*s.u+s.e) + s.p) * s.u


## Creates linear representation for solution using slopes
#
def createLinearRepresentation(u,slopes):

   u_l = [u[i] - 0.5*slopes[i] for i in xrange(len(u))]
   u_r = [u[i] + 0.5*slopes[i] for i in xrange(len(u))]
   return u_l, u_r

#------------------------------------------------------------------------------------
# Create function for advancing conserved quantities in time
#------------------------------------------------------------------------------------
def advCons(val, dx, dt, f_left, f_right):

    return val + dt/dx*(f_left - f_right)

# ----------------------------------------------------------------------------------
def minMod(a,b):

    if a > 0 and b > 0:
        return min(a,b)
    elif a<0 and b<0:
        return max(a,b)
    else:
        return 0.

#------------------------------------------------------------------------------------
def HLLSolver(U_l, U_r, L, R, flux): #quantity of interest U, state to the left, state to right

    #sound speed:
    a_l = L.getSoundSpeed()
    a_r = R.getSoundSpeed()

    #Compute bounding speeds
    S_l = min(L.u - a_l, R.u - a_r)
    S_r = max(L.u + a_l, R.u + a_r)

    #Compute fluxes at the boundaries
    F_l = flux(L)
    F_r = flux(R)

    #Compute the state at the face
    U_hll = (S_r*U_r - S_l*U_l + F_l - F_r) / (S_r-S_l)
    F_hll = (S_r*F_l - S_l*F_r + S_l*S_r*(U_r - U_l) ) / (S_r - S_l)

    #Return appropraite state
    if S_r < 0:
        return F_r
    elif S_l <= 0.0 and S_r >= 0.0:
        return F_hll
    elif S_l > 0.0 and S_r > 0.0:
        return F_l
    else:
        raise ValueError("HLL solver produced unrealistic fluxes\n")
    
#------------------------------------------------------------------------------------
def HLLCSolver(U_l, U_r, L, R, flux): #quantity of interest U, state to the left, state to right

    #sound speed:
    a_l = L.getSoundSpeed()
    a_r = R.getSoundSpeed()

    #Compute bounding speeds
    S_l = min(L.u - a_l, R.u - a_r)
    S_r = max(L.u + a_l, R.u + a_r)
    S_star = ( (R.p - L.p + L.rho*L.u*(S_l - L.u) - R.rho*R.u*(S_r - R.u)) /
               (L.rho*(S_l - L.u) - R.rho*(S_r - R.u)) )

    #Check for zero velocity differences:
    if L == R:
        S_star = L.u

    #Compute fluxes at the boundaries
    F_l = flux(L)
    F_r = flux(R)

    #Compute star values
    coeff_l = L.rho*(S_l - L.u)/(S_l - S_star)
    coeff_r = R.rho*(S_r - R.u)/(S_r - S_star)

    if flux == rhoFlux:

        U_lstar = coeff_l
        U_rstar = coeff_r

    elif flux == momFlux:

        U_lstar = coeff_l*S_star
        U_rstar = coeff_r*S_star

    elif flux == ergFlux:

        U_lstar = coeff_l*( (0.5*L.u*L.u + L.e) + (S_star-L.u)*(S_star +
            L.p/(L.rho*(S_l - L.u)) ) )
        U_rstar = coeff_r*( (0.5*R.u*R.u + R.e) + (S_star-R.u)*(S_star +
            R.p/(R.rho*(S_r - R.u)) ) )

    else:

        raise ValueError("Ended up in a wierd place in HLLC")
    

    #Compute the state at the face
    F_lstar = F_l + S_l*(U_lstar - U_l)
    F_rstar = F_r + S_r*(U_rstar - U_r)

    #Return appropraite state
    if S_r < 0:
        return F_r

    elif S_l <= 0.0 and S_star > 0.0:
        return F_lstar

    elif S_star <= 0.0 and S_r > 0.0:
        return F_rstar

    elif S_l > 0.0:
        return F_l

    else:
        print S_l, S_star, S_r
        raise ValueError("HLLC solver produced unrealistic fluxes\n")

#-------------------------------------------------------------------------------------
def plotHydroSolutions(x,states=None): #Default func values is trivial

    plt.figure(figsize=(11,8.5))

    if states==None:
        raise ValueError("Need to pass in states")
    else:
        u = []
        p = []
        rho = []
        e = []
        for i in states:
            u.append(i.u)
            p.append(i.p)
            rho.append(i.rho)
            e.append(i.e)

    #get edge values
    x_cent = x
    if len(x) == len(states)+1:
        x_cent = [0.5*(x[i]+x[i+1]) for i in xrange(len(states))]
    
    if u != None:
        plotSingle(x_cent,u,"$u$")
    
    if rho != None:
        plotSingle(x_cent,rho,r"$\rho$") 

    if p != None:
        plotSingle(x_cent,p,r"$p$")

    if e != None:
        plotSingle(x_cent,e,r"$e$")

    plt.show(block=False) #show all plots generated to this point
    raw_input("Press anything to continue...")
    plotSingle.fig_num=0

#-------------------------------------------------------------------------------------
def plotSingle(x,y,ylabl):

    #static variable counter
    plotSingle.fig_num += 1
    plt.subplot(2,2,plotSingle.fig_num)
    plt.xlabel('$x$ (cm)')
    plt.ylabel(ylabl)
    plt.plot(x,y,"b+-",label="My Stuff")
    plt.savefig("var_"+str(plot2D.fig_num)+".pdf")
    
plotSingle.fig_num=0

#-------------------------------------------------------------------------------------
def plot2D(x,y,x_ex,y_ex,ylabl):

    #static variable counter
    plot2D.fig_num += 1

    plt.subplot(2,2,plot2D.fig_num)
    plt.xlabel('$x$ (cm)')
    plt.ylabel(ylabl)
    plt.plot(x,y,"b+-",label="Lagrangian")
    plt.plot(x_ex,y_ex,"r--",label="Exact")
    plt.savefig("var_"+str(plot2D.fig_num)+".pdf")
    
plot2D.fig_num=0

#-------------------------------------------------------------------------------------
if __name__ == "__main__":
    main()

