# -----------------------------------------------------------------------------
# Move surface groups radially.
#
def move_surface_groups_radially(surfaces, factor = 2, frames = 25):

    sfactor = (factor-1.0) / frames
    gsteps = compute_group_steps(surfaces, sfactor)
    radial_step = lambda: move_surface_groups(gsteps)
    import Play
    Play.call_for_n_frames(radial_step, frames)

# -----------------------------------------------------------------------------
#
def unmove_surface_groups_radially(surfaces, factor = 2, frames = 25):

    move_surface_groups_radially(surfaces, 1.0/factor, frames)
    
# -----------------------------------------------------------------------------
#
def compute_group_steps(surf_groups, sfactor):

    #
    # Have to compute centers in eye coordinates since surface groups may
    # be from models with different xforms.
    #
    gcenters = []
    for g in surf_groups:
        varray, tarray = g.geometry
        if len(varray) == 0:
            continue            # No center position
        from Matrix import xform_matrix, apply_matrix
        tf = xform_matrix(g.model.openState.xform)
        gcenter = apply_matrix(tf, center_of_points(varray))
        gcenters.append((g, gcenter, len(varray)))

    if len(gcenters) == 0:
        return []
    
    counts = map(lambda gcn: gcn[2], gcenters)
    centers = map(lambda gcn: gcn[1], gcenters)
    from numpy import dot as matrix_multiply, sum, subtract, array
    center = matrix_multiply(counts, centers) / sum(counts)
    
    gsteps = []
    for g, gc, gn in gcenters:
        disp = subtract(gc, center)
        from Matrix import xform_matrix, apply_matrix_without_translation
        tf = xform_matrix(g.model.openState.xform.inverse())
        disp = apply_matrix_without_translation(tf, disp)  # Object coordinates
        shift = (sfactor * array(disp)).astype(varray.dtype)
        gsteps.append((g, shift))

    return gsteps

# -----------------------------------------------------------------------------
#
def move_surface_groups(group_step_list):

    import Matrix as M
    for g, step in group_step_list:
        tf = g.placement
        if tf is None:
            tf = M.identity_matrix()
        g.placement = M.multiply_matrices(M.translation_matrix(step), tf)

# -----------------------------------------------------------------------------
#
def center_of_points(points):

    from numpy import sum
    center = sum(points, axis = 0) / len(points)
    return center

# -----------------------------------------------------------------------------
#
def length(v):

    import math
    return math.sqrt(v[0]*v[0] + v[1]*v[1] + v[2]*v[2])
