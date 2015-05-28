## @package src.mesh
#  Contains mesh-related classes.

#================================================================================
## Mesh class.
#
#  Represents 1-D, Cartesian, fixed grid mesh. Contains a list of Element objects.
#================================================================================
class Mesh:

    #----------------------------------------------------------------------------
    ## Constructor. Takes number of elements, domain width, and x position of
    #  left edge of domain.
    #
    #  @param[in] n_elems     number of elements
    #  @param[in] width       width of domain
    #  @param[in] x_left      x position of left edge of domain. Default is zero.
    #----------------------------------------------------------------------------
    def __init__(self, n_elements, width, x_start=0.):

        # mesh currently assumes uniform element widths
        self.n_elems = n_elements
        dx = width/float(n_elements)
        
        # build elements
        self.elements = [Element(i,(i+0.5)*dx,dx) for i in xrange(n_elements)]

        # compute max dx in mesh
        self.max_dx = dx
               
    #----------------------------------------------------------------------------
    ## Print definition.
    #----------------------------------------------------------------------------
    def __str__(self):

        print_str = "\n-----------------------------------------------------" \
                    "\n                     Elements" \
                    "\n-----------------------------------------------------\n"

        ## Concatenate element strings together and return as one long string
        for el in self.elements:       #for each "Element" in self.elements
            print_str += el.__str__()  #el is an object, not an index in this loop

        return print_str


    #----------------------------------------------------------------------------
    ## Accessor function.
    #----------------------------------------------------------------------------
    def getElement(self, el_id):

        return self.elements[el_id]


#================================================================================
## Element class.
#
#  1-D element, which is defined solely by its ID and its left and right edges.
#================================================================================
class Element:

    #----------------------------------------------------------------------------
    ## Constructor. Takes ID, center, and width of element.
    #----------------------------------------------------------------------------
    def __init__(self, el_id, x_center, width ):

        self.el_id = el_id              #id for this element
        self.dx = width                 ## @var dx spatial width, doxygen?
        self.x_cent = x_center          #center of cell
        self.xl = x_center - width/2.   #
        self.xr = x_center + width/2.


    #----------------------------------------------------------------------------
    ## Print definition.
    #----------------------------------------------------------------------------
    def __str__(self):

        return "ID: %i x_l : %.4f x_r : %.4f\n" % (self.el_id, self.xl, self.xr)

