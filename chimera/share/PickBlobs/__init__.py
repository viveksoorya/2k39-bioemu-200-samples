# -----------------------------------------------------------------------------
#
def picked_surface_component(surface_models, xyz_in, xyz_out):

    d, p, t = closest_surface_intercept(surface_models, xyz_in, xyz_out)
    if p == None:
        return None, None, None

    varray, tarray = p.maskedGeometry(p.Solid)
    vlist, tlist = connected_component(tarray, t)
    return p, vlist, tlist

# -----------------------------------------------------------------------------
#
def connected_component(tarray, t):

    import _surface
    tlist = _surface.connected_triangles(tarray, t)
    vlist = _surface.triangle_vertices(tarray, tlist)
    return vlist, tlist

# -----------------------------------------------------------------------------
#
def closest_surface_intercept(surface_models, xyz_in, xyz_out):

    pilist = []
    for m in surface_models:
        if m.display:
            f, p, tri = surface_intercept(m, xyz_in, xyz_out)
            if not f is None:
                pilist.append((f,p,tri))
    if len(pilist) == 0:
        return None, None, None
    f, p, tri = min(pilist, key = lambda fpt: fpt[0])
    return f, p, tri

# -----------------------------------------------------------------------------
#
def surface_intercept(surf, xyz_in, xyz_out):

    from VolumeViewer import slice as s
    planes = s.per_model_clip_planes(surf)
    xyz1, xyz2, f1, f2 = s.clip_segment_with_planes(xyz_in, xyz_out, planes)
    if xyz1 is None:
        return None, None, None        # No intercept due to clipping
    from Matrix import apply_inverse_matrix
    sxyz1, sxyz2 = apply_inverse_matrix(surf.openState.xform, xyz1, xyz2)
    for p in surf.surfacePieces:
        if p.display and not hasattr(p, 'outline_box'):
            tri, fs = closest_piece_intercept(p, sxyz1, sxyz2)
            if not tri is None:
                f = f1 + fs*(f2-f1)
                return (f, p, tri)
    return None, None, None

# -----------------------------------------------------------------------------
#
def closest_piece_intercept(surface_piece, xyz_in, xyz_out):

    p = surface_piece
    varray, tarray = p.maskedGeometry(p.Solid)
    t, f = closest_geometry_intercept(varray, tarray, xyz_in, xyz_out)
    return t, f

# -----------------------------------------------------------------------------
#
def closest_geometry_intercept(varray, tarray, xyz_in, xyz_out):

    import _surface
    fmin, tmin = _surface.closest_geometry_intercept(varray, tarray,
                                                     xyz_in, xyz_out)
    return tmin, fmin

# -----------------------------------------------------------------------------
#
def color_blob(surface_piece, vlist, rgba):

    p = surface_piece
    vc = p.vertexColors
    if vc == None:
        varray, tarray = p.maskedGeometry(p.Solid)
        n = len(varray)
        from numpy import zeros, single as floatc
        vc = zeros((n, 4), floatc)
        color = p.color
        for k,c in enumerate(color):
            vc[:,k] = c

    vc[vlist,:] = rgba

    p.vertexColors = vc

# -----------------------------------------------------------------------------
#
def blob_geometry(surface_piece, vlist, tlist):

    p = surface_piece
    varray, tarray = p.maskedGeometry(p.Solid)
    
    vbarray = varray.take(vlist, axis=0)
    tbarray = tarray.take(tlist, axis=0)

    # Remap vertex indices in triangle array to use new vertex list.
    from numpy import zeros, intc, arange
    vmap = zeros(varray.shape[0], intc)
    vmap[vlist] = arange(len(vlist), dtype = intc)
    tbarray[:,:] = vmap[tbarray]
        
    return vbarray, tbarray

# -----------------------------------------------------------------------------
#
def surface_models():

  import chimera
  import _surface
  mlist = chimera.openModels.list(modelTypes = [_surface.SurfaceModel])
  import SurfaceCap
  mlist = filter(lambda m: not SurfaceCap.is_surface_cap(m), mlist)

  return mlist

# -------------------------------------------------------------------------
#
def principle_axes_box(varray, tarray):

  import _surface
  weights = _surface.vertex_areas(varray, tarray)
  from Measure import inertia
  axes, d2e, center = inertia.moments_of_inertia([(varray, weights)])
  from Matrix import point_bounds
  bounds = [point_bounds(varray, axes[a]) for a in range(3)]
  return axes, bounds
      
# -------------------------------------------------------------------------
#
def outline_box_surface(axes, bounds, align_to, box_surface = None,
                        rgba = (0,1,0,1), linewidth = 0):

  # Compute corners
  vlist = []
  for ci in ((0,0,0),(0,0,1),(0,1,0),(0,1,1),
                 (1,0,0),(1,0,1),(1,1,0),(1,1,1)):
      v = [sum([bounds[a][ci[a]]*axes[a][c] for a in (0,1,2)]) for c in (0,1,2)]
      vlist.append(v)
  tlist = ((0,4,5), (5,1,0), (0,2,6), (6,4,0),
           (0,1,3), (3,2,0), (7,3,1), (1,5,7),
           (7,6,2), (2,3,7), (7,5,4), (4,6,7))
  b = 8 + 2 + 1    # Bit mask, 8 = show triangle, edges are bits 4,2,1
  hide_diagonals = (b,b,b,b,b,b,b,b,b,b,b,b)


  if box_surface is None or box_surface.__destroyed__:
      import _surface
      box_surface = _surface.SurfaceModel()
      box_surface.name = 'Principal axes box'
      from chimera import openModels
      openModels.add([box_surface], sameAs = align_to)
  elif align_to and box_surface.openState != align_to.openState:
      # Transform vertices to box model coordinates.
      from Matrix import multiply_matrices, xform_matrix, apply_matrix
      tf = multiply_matrices(
          xform_matrix(box_surface.openState.xform.inverse()),
          xform_matrix(align_to.openState.xform))
      vlist = apply_matrix(tf, vlist)

  box_surface.display = True
  p = box_surface.newPiece()
  p.displayStyle = p.Mesh
  p.lineThickness = linewidth
  p.useLighting = False
  p.outline_box = True # Do not cap clipped outline box.
  # Set geometry after setting outline_box attribute to avoid undesired
  # coloring and capping of outline boxes.
  p.geometry = vlist, tlist
  p.triangleAndEdgeMask = hide_diagonals
  p.color = rgba

  return box_surface

# -------------------------------------------------------------------------
#
def boundary_lengths(varray, tarray):

    import _surface
    loops = _surface.boundary_loops(tarray)
    return [loop_length(loop, varray) for loop in loops]

# -------------------------------------------------------------------------
#
def loop_length(vindices, varray):

    p = varray.take(vindices, axis=0)
    p0 = p[0,:].copy()
    p[:-1,:] -= p[1:,:]
    p[-1,:] -= p0
    p *= p
    from numpy import sqrt
    d = sqrt(p.sum(axis=1)).sum()
    return d
