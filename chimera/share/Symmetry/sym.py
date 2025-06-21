# -----------------------------------------------------------------------------
# Rotation about z axis.
#
def cyclic_symmetry_matrices(n, center = (0,0,0)):

    tflist = []
    from math import sin, cos, pi
    for k in range(n):
        a = 2*pi * float(k) / n
        c = cos(a)
        s = sin(a)
        tf = ((c, -s, 0, 0),
              (s, c, 0, 0),
              (0,0,1,0))
        tflist.append(tf)
    tflist = recenter_symmetries(tflist, center)
    return tflist

# -----------------------------------------------------------------------------
# Rotation about z axis, reflection about x axis.
#
def dihedral_symmetry_matrices(n, center = (0,0,0)):

    clist = cyclic_symmetry_matrices(n)
    reflect = ((1,0,0,0),(0,-1,0,0),(0,0,-1,0))
    from Matrix import matrix_products, identity_matrix
    tflist = matrix_products([identity_matrix(), reflect], clist)
    tflist = recenter_symmetries(tflist, center)
    return tflist

# -----------------------------------------------------------------------------
#
tetrahedral_orientations = ('222', 'z3')
def tetrahedral_symmetry_matrices(orientation = '222', center = (0,0,0)):

    aa = (((0,0,1),0), ((1,0,0),180), ((0,1,0),180), ((0,0,1),180),
          ((1,1,1),120), ((1,1,1),240), ((-1,-1,1),120), ((-1,-1,1),240),
          ((-1,1,-1),120), ((-1,1,-1),240), ((1,-1,-1),120), ((1,-1,-1),240))
    import Matrix as M
    syms = [M.rotation_transform(axis, angle) for axis, angle in aa]

    if orientation == 'z3':
        # EMAN convention, 3-fold on z, 3-fold in yz plane along neg y.
        from math import acos, sqrt, pi
        tf = M.multiply_matrices(
            M.rotation_transform((0,0,1), -45.0),
            M.rotation_transform((1,0,0), -acos(1/sqrt(3))*180/pi))
        syms = M.coordinate_transform_list(syms, tf)

    syms = recenter_symmetries(syms, center)
    return syms

# -----------------------------------------------------------------------------
# 4-folds along x, y, z axes.
#
def octahedral_symmetry_matrices(center = (0,0,0)):

    c4 = (((0,0,1),0), ((0,0,1),90), ((0,0,1),180), ((0,0,1),270))
    cube = (((1,0,0),0), ((1,0,0),90), ((1,0,0),180), ((1,0,0),270),
            ((0,1,0),90), ((0,1,0),270))
    import Matrix as M
    c4syms = [M.rotation_transform(axis, angle) for axis, angle in c4]
    cubesyms = [M.rotation_transform(axis, angle) for axis, angle in cube]
    syms = M.matrix_products(cubesyms, c4syms)
    syms = recenter_symmetries(syms, center)
    return syms

# -----------------------------------------------------------------------------
# Rise and angle per-subunit.  Angle in degrees.
#
def helical_symmetry_matrices(rise, angle, axis = (0,0,1), center = (0,0,0),
                              n = 1):
    
    zlist = [(i if i <= n/2 else n/2 - i) for i in range(n)]
    syms = [helical_symmetry_matrix(rise, angle, axis, center, z)
            for z in zlist]
    return syms

# -----------------------------------------------------------------------------
# Angle in degrees.
#
def helical_symmetry_matrix(rise, angle, axis = (0,0,1), center = (0,0,0),
                            n = 1):

    import Matrix as M
    if n == 0:
        return M.identity_matrix()
    rtf = M.rotation_transform(axis, n*angle, center)
    shift = M.translation_matrix([x*n*rise for x in axis])
    tf = M.multiply_matrices(shift, rtf)
    return tf

# -----------------------------------------------------------------------------
#
def translation_symmetry_matrices(n, delta):

    tflist = []
    dx, dy, dz = delta
    for k in range(n):
        tf = ((1, 0, 0, k*dx),
              (0, 1, 0, k*dy),
              (0, 0, 1, k*dz))
        tflist.append(tf)
    return tflist

# -----------------------------------------------------------------------------
#
def recenter_symmetries(tflist, center):

    if center == (0,0,0):
      return tflist
    import Matrix as M
    ctf = M.translation_matrix([-x for x in center])
    return M.coordinate_transform_list(tflist, ctf)
