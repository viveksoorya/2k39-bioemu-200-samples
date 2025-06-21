# -----------------------------------------------------------------------------
# Create a tube surface passing through specified atoms.
#
def tube_through_atoms(path_atoms, radius = 0, band_length = 0,
                       segment_subdivisions = 10, circle_subdivisions = 15,
                       follow_bonds = True, color = None,
                       surface_model = None, model_id = None):

    def shape(ptlist, pcolors, r=radius, nc=circle_subdivisions):
        return Tube(ptlist, pcolors, r, nc)

    mesh = (radius == 0)

    return extrusion(path_atoms, shape, band_length, segment_subdivisions,
                     follow_bonds, color, mesh, surface_model, model_id)

# -----------------------------------------------------------------------------
#
class Tube:

    def __init__(self, ptlist, pcolors, radius, circle_subdivisions,
                 end_caps = True):

        self.ptlist = ptlist    # Center line points and tangents.
        self.pcolors = pcolors  # Point colors.
        self.radius = radius
        self.circle_subdivisions = circle_subdivisions
        self.end_caps = end_caps

    def geometry(self):

        nz = len(self.ptlist)
        nc = self.circle_subdivisions
        height = 0
        tflist = extrusion_transforms(self.ptlist)
        from Shape.shapecmd import cylinder_geometry
        varray, tarray = cylinder_geometry(self.radius, height, nz, nc,
                                           caps = self.end_caps)
        # Transform circles.
        from _contour import affine_transform_vertices
        for i in range(nz):
            affine_transform_vertices(varray[nc*i:nc*(i+1),:], tflist[i])
        if self.end_caps:
            # Transform cap center points
            affine_transform_vertices(varray[nz*nc:nz*nc+nc+1,:], tflist[0])
            affine_transform_vertices(varray[nz*nc+nc+1:,:], tflist[-1])
        return varray, tarray

    def colors(self):

        nc = self.circle_subdivisions
        nz = len(self.pcolors)
        from numpy import empty, float32
        vcount = nz*nc+2*nc+2 if self.end_caps else nc*nc
        carray = empty((vcount,4), float32)
        for i in range(nz):
            carray[nc*i:nc*(i+1),:] = self.pcolors[i]
        if self.end_caps:
            carray[nz*nc:nz*nc+nc+1,:] = self.pcolors[0]
            carray[nz*nc+nc+1:,:] = self.pcolors[-1]
        return carray

# -----------------------------------------------------------------------------
# Create a ribbon surface passing through specified atoms.
#
def ribbon_through_atoms(path_atoms, width = 0, yaxis = None, twist = 0,
                         band_length = 0,
                         segment_subdivisions = 10, width_subdivisions = 15,
                         follow_bonds = True, color = None,
                         surface_model = None, model_id = None):

    def shape(ptlist, pcolors, w=width, nw=width_subdivisions, y=yaxis, t=twist):
        return Ribbon(ptlist, pcolors, w, nw, y, t)

    mesh = False

    return extrusion(path_atoms, shape, band_length, segment_subdivisions,
                     follow_bonds, color, mesh, surface_model, model_id)

# -----------------------------------------------------------------------------
#
class Ribbon:

    def __init__(self, ptlist, pcolors, width, width_subdivisions,
                 yaxis = None, twist = 0):

        self.ptlist = ptlist    # Center line points and tangents.
        self.pcolors = pcolors  # Point colors.
        self.width = width
        self.width_subdivisions = width_subdivisions
        self.yaxis = yaxis
        self.twist = twist

    def geometry(self):

        nz = len(self.ptlist)
        nw = self.width_subdivisions + 1
        height = 0
        tflist = extrusion_transforms(self.ptlist, self.yaxis)
        from Shape.shapecmd import rectangle_geometry
        varray, tarray = rectangle_geometry(self.width, height, nw, nz)

        from _contour import affine_transform_vertices
        if self.twist != 0:
            import Matrix
            twist_tf = Matrix.rotation_transform((0,0,1), self.twist)
            affine_transform_vertices(varray, twist_tf)

        # Transform transverse lines.
        va = varray.reshape((nz,nw,3))
        for i in range(nz):
            affine_transform_vertices(va[i,:,:], tflist[i])
        return varray, tarray

    def colors(self):

        nz = len(self.pcolors)
        nw = self.width_subdivisions + 1
        from numpy import empty, float32
        carray = empty((nz*nw,4), float32)
        for i in range(nz):
            carray[nw*i:nw*(i+1),:] = self.pcolors[i]
        return carray

# -----------------------------------------------------------------------------
#
def extrusion(path_atoms, shape, band_length = 0, segment_subdivisions = 10,
              follow_bonds = True, color = None, mesh = False,
              surface_model = None, model_id = None):

    if len(path_atoms) == 0:
        return None, []

    if follow_bonds:
        chains = atom_chains(path_atoms)
    else:
        chains = [(path_atoms,None)]
        if color is None:
            color = (.745,.745,.745,1)

    s = surface_model
    sxf = (s or path_atoms[0].molecule).openState.xform
    plist = []
    import Molecule as M
    for atoms, bonds in chains:
        xyz_path = M.atom_positions(atoms, sxf)
        point_colors = [M.atom_rgba(a) for a in atoms]
        if color:
            segment_colors = [color] * (len(atoms) - 1)
        else:
            segment_colors = [M.bond_rgba(b) for b in bonds]
        p = banded_extrusion(xyz_path, point_colors, segment_colors,
                        segment_subdivisions, band_length, shape, mesh = mesh,
                        surface_model = s, model_id = model_id)
        if p:
            plist.append(p)
            s = p.model
    if s:
        s.openState.xform = sxf
    return s, plist
    
# -----------------------------------------------------------------------------
# Return a list of atom chains.  An atom chain is a sequence
# of atoms connected by bonds where all non-end-point atoms have exactly 2
# bonds.  A chain is represented by a 2-tuple, the first element being the
# ordered list of atoms, and the second being the ordered list of bonds.
# In a chain which is a cycle all atoms have 2 bonds and the first and
# last atom in the chain are the same.  Non-cycles have end point atoms
# with more or less than 2 bonds.
#
def atom_chains(atoms):

  atom_bonds = {}       # Bonds connecting specified atoms.
  aset = set(atoms)
  for a in atoms:
      atom_bonds[a] = [b for b in a.bonds if b.otherAtom(a) in aset]

  used_bonds = {}
  chains = []
  for a in atoms:
    if len(atom_bonds[a]) != 2:
      for b in atom_bonds[a]:
        if not used_bonds.has_key(b):
          used_bonds[b] = 1
          c = trace_chain(a, b, atom_bonds)
          chains.append(c)
          end_bond = c[1][-1]
          used_bonds[end_bond] = 1

  #
  # Pick up cycles
  #
  reached_atoms = {}
  for catoms, bonds in chains:
    for a in catoms:
      reached_atoms[a] = 1

  for a in atoms:
    if not reached_atoms.has_key(a):
      bonds = atom_bonds[a]
      if len(bonds) == 2:
        b = bonds[0]
        c = trace_chain(a, b, atom_bonds)
        chains.append(c)
        for a in c[0]:
          reached_atoms[a] = 1
      
  return chains
          
# -----------------------------------------------------------------------------
#
def trace_chain(atom, bond, atom_bonds):

  atoms = [atom]
  bonds = [bond]

  a = atom
  b = bond
  while 1:
    a = b.otherAtom(a)
    atoms.append(a)
    if a == atom:
      break                     # loop
    blist = list(atom_bonds[a])
    blist.remove(b)
    if len(blist) != 1:
      break
    b = blist[0]
    bonds.append(b)
    
  return (atoms, bonds)

# -----------------------------------------------------------------------------
# Create an extruded surface along a path with banded coloring.
#
def banded_extrusion(xyz_path, point_colors, segment_colors,
                     segment_subdivisions, band_length, shape, mesh = False,
                     surface_model = None, model_id = None):

    if len(xyz_path) <= 1:
        return None             # No path

    import spline
    ptlist = spline.natural_cubic_spline(xyz_path, segment_subdivisions,
                                         return_tangents = True)

    plist = [pt[0] for pt in ptlist]
    pcolors = band_colors(plist, point_colors, segment_colors,
                          segment_subdivisions, band_length)

    s = shape(ptlist, pcolors)

    p = make_surface_piece(s, mesh, surface_model, model_id)
    return p

# -----------------------------------------------------------------------------
#
def make_surface_piece(shape, mesh = False,
                       surface_model = None, model_id = None):

    if surface_model is None:
        import _surface
        surface_model = _surface.SurfaceModel()
        from chimera import openModels as om
        if model_id is None:
            model_id = (om.Default, om.Default)
        om.add([surface_model], baseId = model_id[0], subid = model_id[1])

    varray, tarray = shape.geometry()
    carray = shape.colors()
    
    p = surface_model.addPiece(varray, tarray, (1,1,1,1))
    p.vertexColors = carray
    if mesh:
        p.displayStyle = p.Mesh
        p.useLighting = False
    return p

# -----------------------------------------------------------------------------
# Compute transforms mapping (0,0,0) origin to points along path with z axis
# along path tangent.
#
def extrusion_transforms(ptlist, yaxis = None):

    import Matrix as M
    tflist = []
    if yaxis is None:
        # Make xy planes for coordinate frames at each path point not rotate
        # from one point to next.
        tf = M.identity_matrix()
        n0 = (0,0,1)
        for p1,n1 in ptlist:
            tf = M.multiply_matrices(M.vector_rotation_transform(n0,n1), tf)
            tflist.append(M.multiply_matrices(M.translation_matrix(p1),tf))
            n0 = n1
    else:
        # Make y-axis of coordinate frames at each point align with yaxis.
        for p,t in ptlist:
            za = t
            xa = M.normalize_vector(M.cross_product(yaxis, za))
            ya = M.cross_product(za, xa)
            tf = ((xa[0], ya[0], za[0], p[0]),
                  (xa[1], ya[1], za[1], p[1]),
                  (xa[2], ya[2], za[2], p[2]))
            tflist.append(tf)
    return tflist

# -----------------------------------------------------------------------------
# Calculate point colors for an interpolated set of points.
# Point colors are extended to interpolated points and segments within
# band_length/2 arc distance.
#
def band_colors(plist, point_colors, segment_colors,
                segment_subdivisions, band_length):

  n = len(point_colors)
  pcolors = []
  for k in range(n-1):
    j = k * (segment_subdivisions + 1)
    import spline
    arcs = spline.arc_lengths(plist[j:j+segment_subdivisions+2])
    bp0, mp, bp1 = band_points(arcs, band_length)
    scolors = ([point_colors[k]]*bp0 +
               [segment_colors[k]]*mp +
               [point_colors[k+1]]*bp1)
    pcolors.extend(scolors[:-1])
  if band_length > 0:
      last = point_colors[-1]
  else:
      last = segment_colors[-1]
  pcolors.append(last)
  return pcolors
  
# -----------------------------------------------------------------------------
# Count points within band_length/2 of each end of an arc.
#
def band_points(arcs, band_length):
      
  arc = arcs[-1]
  half_length = min(.5 * band_length, .5 * arc)
  bp0 = mp = bp1 = 0
  for p in range(len(arcs)):
    l0 = arcs[p]
    l1 = arc - arcs[p]
    if l0 < half_length:
      if l1 < half_length:
        if l0 <= l1:
          bp0 += 1
        else:
          bp1 += 1
      else:
        bp0 += 1
    elif l1 < half_length:
      bp1 += 1
    else:
      mp += 1

  return bp0, mp, bp1
