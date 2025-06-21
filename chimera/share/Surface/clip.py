# ------------------------------------------------------------------------------
#
def spherical_clip(volume, center = None, radius = None, color = None,
                   mesh = False, replace = True):

    v = volume
    if replace:
        unclip(v)
        
    s1, i1 = volume_surface(v)
    if center is None or radius is None:
        vxyz = s1.geometry[0]
        if len(vxyz) == 0:
            return
        if center is None:
            center = vxyz.mean(axis=0)
        if radius is None:
            radius = 0.4 * max(vxyz.max(axis=0) - vxyz.min(axis=0))
    from math import pi
    divisions = 2*pi*radius / min(v.data.step)
    if color is None:
        color = s1.color
    # TODO: Need to specify sphere is part of volume, not just any surface
    #       with same id.
    s2, i2 = sphere_surface(center, radius, color, mesh, divisions, v.id)

    f1, f2 = clip_surfaces(s1, i1, s2, i2)

    plist = getattr(v, 'spherical_clip_surface_pieces', ())
    v.spherical_clip_surface_pieces = plist + (s2,f1,f2)

# ------------------------------------------------------------------------------
#
def unclip(volume):

    if hasattr(volume, 'spherical_clip_surface_pieces'):
        for p in volume.spherical_clip_surface_pieces:
            if not p.__destroyed__:
                p.model.removePiece(p)
        delattr(volume, 'spherical_clip_surface_pieces')
        s, i = volume_surface(volume)
        s.triangleAndEdgeMask = None
    
# ------------------------------------------------------------------------------
# Clip one surface with another.
# Show only parts of surface 1 that are inside surface 2 and parts of surface 2
# that are inside surface 1.
#
def clip_surfaces(surf1, inside1, surf2, inside2):

    import Matrix as M
    tf1 = M.xform_matrix(surf1.model.openState.xform)
    tf2 = M.xform_matrix(surf2.model.openState.xform)
    tf12 = M.multiply_matrices(M.invert_matrix(tf2), tf1)
    tf21 = M.multiply_matrices(M.invert_matrix(tf1), tf2)
    f1 = clip_surface(surf1, tf12, inside2)
    f2 = clip_surface(surf2, tf21, inside1)
    return f1, f2

# ------------------------------------------------------------------------------
#
def clip_surface(surf, tf, inside):

    v, t = surf.geometry
    inside_t, fringe_v, fringe_t, fringe_n = \
        clip_geometry(v, t, surf.normals, tf, inside)

    from numpy import multiply
    multiply(inside_t, 0xf, inside_t)
    surf.triangleAndEdgeMask = inside_t

    f = surf.model.addPiece(fringe_v, fringe_t, surf.color)
    f.normals = fringe_n
    f.displayStyle = surf.displayStyle

    return f

# ------------------------------------------------------------------------------
#
def clip_geometry(vertices, triangles, normals, tf, inside):

    i = inside(vertices, tf)
    from numpy import int32
    it = inside_triangles(i, triangles).astype(int32)
    fv, ft, fn = fringe_geometry(vertices, triangles, normals, i)
    return it, fv, ft, fn
    
# ------------------------------------------------------------------------------
#
def inside_triangles(iv, t):

    di = iv[t]
    from numpy import less, logical_and
    it = less(di[:,0], 0)
    logical_and(it, less(di[:,1], 0), it)
    logical_and(it, less(di[:,2], 0), it)
    return it

# ------------------------------------------------------------------------------
#
def inside_sphere(xyz, tf, center, radius):

    txyz = xyz.copy()
    import Matrix as M
    M.transform_points(txyz, tf)
    from numpy import empty, float32
    d = empty((len(xyz),), float32)
    import _distances as D
    D.distances_from_origin(txyz, center, d)
    d -= radius
    return d

# ------------------------------------------------------------------------------
#
def fringe_geometry(v, t, n, di):

    ct = cut_triangles(t, di)
    ei, ev, en, imap = cut_edges(v, ct, n, di)
    tlist = []
    for i0,i1,i2 in ct:
        ilist = []
        for e in ((i0,i1), (i1,i2), (i2,i0)):
            if di[e[0]] < 0:
                ilist.append(imap[e[0]])
            if e in ei:
                ilist.append(ei[e])
        if len(ilist) == 3:
            tlist.append(tuple(ilist))
        elif len(ilist) == 4:
            tlist.append(tuple(ilist[:3]))
            tlist.append((ilist[0],ilist[2],ilist[3]))
    from numpy import array, int32
    et = array(tlist, int32).reshape((len(tlist),3))
    return ev, et, en

# ------------------------------------------------------------------------------
#
def cut_triangles(t, di):

    dt = di[t]
    from numpy import less, add, int32, logical_or, equal
    it = less(dt[:,0], 0).astype(int32)
    add(it, less(dt[:,1], 0).astype(int32), it)
    add(it, less(dt[:,2], 0).astype(int32), it)
    cm = logical_or(equal(it, 1), equal(it, 2))
    ct = t[cm,:]
    return ct

# ------------------------------------------------------------------------------
# 
def cut_edges(v, ct, n, di):

    from math import sqrt
    ei = {}
    imap = {}
    vs = set()
    vlist = []
    nlist = []
    for i0,i1,i2 in ct:
        for j0,j1 in ((i0,i1), (i1,i2), (i2,i0)):
            d0, d1 = di[j0], di[j1]
            if (d0 < 0 and d1 >= 0) or (d0 >= 0 and d1 < 0):
                if not (j0,j1) in ei:
                    ei[(j0,j1)] = ei[(j1,j0)] = len(vlist)
                    f = d1 / (d1 - d0)
                    vc = f*v[j0]+(1-f)*v[j1]
                    nc = f*n[j0]+(1-f)*n[j1]
                    nc /= sqrt((nc*nc).sum())
                    vlist.append(vc)
                    nlist.append(nc)
            if d0 < 0:
                if not j0 in imap:
                    imap[j0] = len(vlist)
                    vlist.append(v[j0])
                    nlist.append(n[j0])

    from numpy import array, float32
    ev = array(vlist, float32).reshape((len(vlist),3))
    en = array(nlist, float32).reshape((len(nlist),3))
            
    return ei, ev, en, imap

# ------------------------------------------------------------------------------
#
def sphere_surface(center = (0,0,0), radius = 1, color = (.75,.75,.75,1),
                   mesh = False, divisions = 50, model_id = None):

    cstring = '%f,%f,%f' % tuple(center)
    from Shape.shapecmd import sphere_shape
    s = sphere_shape(radius, cstring, color = color, mesh = mesh,
                     divisions = divisions, modelId = model_id)
    def inside(xyz, tf, center = center, radius = radius):
        return inside_sphere(xyz, tf, center, radius)
    return s, inside

# ------------------------------------------------------------------------------
#
def volume_surface(v):

    s = v.surface_piece_list[0]
    def inside(xyz, tf, v = v):
        import Matrix as M
        tfw = M.multiply_matrices(M.xform_matrix(v.openState.xform), tf)
        xfw = M.chimera_xform(tfw)
        di = v.interpolated_values(xyz, xfw) - v.surface_levels[0]
        di = -di
        return di
    return s, inside
