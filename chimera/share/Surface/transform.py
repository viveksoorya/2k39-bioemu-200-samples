# -----------------------------------------------------------------------------
#
def transform_surface_pieces(surfaces, scale, rotate, axis, center, move):
    
    tf = surface_transform(scale, rotate, axis, center, move)
    import Matrix as M
    rtf = M.rotation_transform(axis, rotate) if rotate != 0 else None
    for p in surfaces:
        mtf = M.xform_matrix(p.model.openState.xform)
        ptf = M.coordinate_transform(tf, mtf)
        va, ta = p.geometry
        na = p.normals
        M.transform_points(va, ptf)
        p.geometry = (va, ta)
        if rtf:
            M.transform_vectors(na, M.coordinate_transform(rtf, mtf))
        p.normals = na

# -----------------------------------------------------------------------------
#
def surface_transform(scale, rotate, axis, center, move):
    
    import Matrix as M
    tf = M.identity_matrix()
    if not center is None:
        cf = M.translation_matrix([-x for x in center])
        tf = M.multiply_matrices(cf, tf)
    if not scale is None:
        stf = ((scale,0,0,0),(0,scale,0,0),(0,0,scale,0))
        tf = M.multiply_matrices(stf, tf)
    if rotate != 0:
        rtf = M.rotation_transform(axis, rotate)
        tf = M.multiply_matrices(rtf, tf)
    if not center is None:
        ucf = M.translation_matrix(center)
        tf = M.multiply_matrices(ucf, tf)
    if not move is None:
        mtf = M.translation_matrix(move)
        tf = M.multiply_matrices(mtf, tf)
    return tf

# -----------------------------------------------------------------------------
#
def surface_radius(p,c):

    va, ta = p.geometry
    if len(ta) == 0:
        return 0
    p = va - c
    r2 = (p*p).sum(axis = 1)
    r2max = r2[ta.ravel()].max()
    import math
    return math.sqrt(r2max)
