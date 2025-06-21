#
# Calculate a solvent excluded molecular surface using a grid contouring method.
# This is test code, preparing for a production implementation in Chimera 2.
#
def ses_surface(atoms, probe_radius = 1.4, grid_spacing = 0.5, name = None):

    from _multiscale import get_atom_coordinates, bounding_box
    xyz = get_atom_coordinates(atoms, transformed = False)

    from numpy import array, float32
    r = array(tuple(a.radius for a in atoms), float32)

    # Compute bounding box for atoms
    xyz_min, xyz_max = bounding_box(xyz)
    pad = 2*probe_radius + r.max()
    origin = [x-pad for x in xyz_min]

    # Create 3d grid for computing distance map
    from math import ceil
    s = grid_spacing
    shape = [int(ceil((xyz_max[a] - xyz_min[a] + 2*pad) / s))
             for a in (2,1,0)]
    print 'grid size', shape, 'atoms', len(atoms)
    from numpy import empty, float32, sqrt
    matrix = empty(shape, float32)
    max_index_range = 2
    matrix[:,:,:] = max_index_range

    # Transform centers and radii to grid index coordinates
    xyz_to_ijk_tf = ((1.0/s, 0, 0, -origin[0]/s),
                     (0, 1.0/s, 0, -origin[1]/s),
                     (0, 0, 1.0/s, -origin[2]/s))
    ijk = xyz.copy()
    import Matrix as M
    M.transform_points(ijk, xyz_to_ijk_tf)
    ri = r.copy()
    ri += probe_radius
    ri /= s

    # Compute distance map from surface of spheres, positive outside.
    from _gaussian import sphere_surface_distance
    sphere_surface_distance(ijk, ri, max_index_range, matrix)

    # Get the SAS surface as a contour surface of the distance map
    from _contour import surface
    level = 0
    va, ta, na = surface(matrix, level, cap_faces = False,
                         calculate_normals = True)

    # Transform surface from grid index coordinates to atom coordinates
    ijk_to_xyz_tf = M.invert_matrix(xyz_to_ijk_tf)

    # Create surface model to show SAS surface
#    show_surface('SAS surface', va, ijk_to_xyz_tf, ta, na)

    # Compute SES surface distance map using SAS surface vertex
    # points as probe sphere centers.
    matrix[:,:,:] = max_index_range
    rp = empty((len(va),), float32)
    rp[:] = float(probe_radius)/s
    sphere_surface_distance(va, rp, max_index_range, matrix)
    ses_va, ses_ta, ses_na = surface(matrix, level, cap_faces = False,
                                     calculate_normals = True)

    # Create surface model to show surface
    m0 = atoms[0].molecule
    nm = ('%s SES surface' % m0.name) if name is None else name
    surf = show_surface(nm, ses_va, ijk_to_xyz_tf, ses_ta, ses_na,
                        color = (.7,.8,.5,1))
    surf.openState.xform = m0.openState.xform

    # Delete connected components more than 1.5 probe radius from atom spheres.
    import Surface
    Surface.split_surfaces(surf.surfacePieces, in_place = True)
    outside = []
    for p in surf.surfacePieces:
        pva, pta = p.geometry
        v0 = pva[0,:]
        d = xyz - v0
        d2 = (d*d).sum(axis = 1)
        adist = (sqrt(d2) - r).min()
#        print v0, adist
        if adist >= 1.5*probe_radius:
            outside.append(p)
    for p in outside:
        surf.removePiece(p)

    return surf

def show_surface(name, va, ijk_to_xyz_tf, ta, na, color = (.7,.7,.7,1)):

    va_xyz = va.copy()
    import Matrix as M
    M.transform_points(va_xyz, ijk_to_xyz_tf)
    from _surface import SurfaceModel
    surf = SurfaceModel()
    surf.name = name
    p = surf.addPiece(va_xyz, ta, color)
    p.normals = na
    from chimera import openModels
    openModels.add([surf])
    return surf

def surface_selected():

    from chimera import selection, replyobj
    atoms = selection.currentAtoms()
    if atoms:
        ses_surface(atoms)
#        ses_surface(atoms, grid_spacing = 0.2)
    else:
        replyobj.status('Select atoms to surface')

