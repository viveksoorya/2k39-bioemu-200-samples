# -----------------------------------------------------------------------------
# Optimize the position of molecules in density maps.
#
# Uses gradient descent to rigidly move molecule to increase sum of density
# values at selected atom positions.
#

# -----------------------------------------------------------------------------
#
def move_selected_atoms_to_maximum(max_steps = 2000, ijk_step_size_min = 0.01,
                                   ijk_step_size_max = 0.5,
                                   optimize_translation = True,
                                   optimize_rotation = True,
                                   move_whole_molecules = True,
                                   request_stop_cb = None):

    from VolumeViewer import active_volume
    volume = active_volume()
    if volume == None or volume.model_transform() == None:
        if request_stop_cb:
            request_stop_cb('No volume data set.')
        return {}
    
    from chimera import selection
    atoms = selection.currentAtoms()
    if len(atoms) == 0:
        if request_stop_cb:
            request_stop_cb('No atoms selected.')
        return {}

    stats = move_atoms_to_maximum(atoms, volume, max_steps,
                                  ijk_step_size_min, ijk_step_size_max,
                                  optimize_translation, optimize_rotation,
                                  move_whole_molecules,
                                  request_stop_cb)
    return stats

# -----------------------------------------------------------------------------
#
def move_atoms_to_maximum(atoms, volume,
                          max_steps = 2000, ijk_step_size_min = 0.01,
                          ijk_step_size_max = 0.5,
                          optimize_translation = True,
                          optimize_rotation = True,
                          move_whole_molecules = True,
                          request_stop_cb = None):

    points = atom_coordinates(atoms)
    point_weights = None        # Each atom give equal weight in fit.

    metric = 'sum product'
    symmetries = []
    move_tf, stats = motion_to_maximum(points, point_weights, volume, max_steps,
                                       ijk_step_size_min, ijk_step_size_max,
                                       optimize_translation, optimize_rotation,
                                       metric, symmetries, request_stop_cb)
    stats['molecules'] = list(set([a.molecule for a in atoms]))

    import move
    move.move_models_and_atoms(move_tf, [], atoms, move_whole_molecules, volume)

    from Matrix import chimera_xform
    poc, clevel = points_outside_contour(points, chimera_xform(move_tf), volume)
    stats['atoms outside contour'] = poc
    stats['contour level'] = clevel

    return stats

# -----------------------------------------------------------------------------
#
def motion_to_maximum(points, point_weights, volume, max_steps,
                      ijk_step_size_min, ijk_step_size_max,
                      optimize_translation, optimize_rotation,
                      metric = 'sum product', symmetries = [],
                      request_stop_cb = None):

    from chimera import Xform
    data_array, xyz_to_ijk_transform = \
        volume.matrix_and_transform(Xform(), subregion = None, step = 1)
    move_tf, stats = \
             locate_maximum(points, point_weights,
                            data_array, xyz_to_ijk_transform,
                            max_steps, ijk_step_size_min, ijk_step_size_max,
                            optimize_translation, optimize_rotation,
                            metric, None, symmetries, request_stop_cb)
    return move_tf, stats

# -----------------------------------------------------------------------------
# Find transformation to move to local sum of densities maximum.
# Take gradient steps of fixed length and cut step length when several
# steps in a row produce little overall motion.
#
# Symmetries describe multiple placements of the data array in the
# point coordinate system. The data array copies are summed.  Instead of
# thinking of the returned optimizing transformation T as moving the points
# it is clearer to consider T-inverse moving the data array which then has
# symmetry operators applied to it, and the points remain stationary.
# Grid indices are mapped to point coordinates using
#   S * T^-1 * xyz_to_ijk_transform^-1
# where S is a symmetry.
#
def locate_maximum(points, point_weights, data_array, xyz_to_ijk_transform,
                   max_steps, ijk_step_size_min, ijk_step_size_max,
                   optimize_translation, optimize_rotation,
                   metric = 'sum product', rotation_center = None,
                   symmetries = [], request_stop_cb = None):

    segment_steps = 4
    cut_step_size_threshold = .25
    step_cut_factor = .5
    step_grow_factor = 1.2
    
    ijk_step_size = ijk_step_size_max

    if metric == 'correlation about mean':
        from numpy import sum, float64
        wm = sum(point_weights, dtype = float64) / len(point_weights)
        point_wts = point_weights.copy()
        point_wts -= wm
    else:
        point_wts = point_weights

    import Matrix as M
    move_tf = M.identity_matrix()

    if rotation_center is None:
        from numpy import sum, float64
        rotation_center = rc = sum(points, axis=0, dtype=float64) / len(points)

    syminv = [M.invert_matrix(s) for s in symmetries]

    step = 0
    while step < max_steps and ijk_step_size > ijk_step_size_min:
        xyz_to_ijk_tf = M.multiply_matrices(xyz_to_ijk_transform, move_tf)
        rc = (rotation_center if len(symmetries) == 0
              else M.apply_matrix(M.invert_matrix(move_tf), rotation_center))
        seg_tf = step_to_maximum(points, point_wts,
                                 data_array, xyz_to_ijk_tf,
                                 segment_steps, ijk_step_size,
                                 optimize_translation, optimize_rotation,
                                 rc, metric, syminv)
        step += segment_steps
        mm = maximum_ijk_motion(points, xyz_to_ijk_tf, seg_tf)
        mmcut = cut_step_size_threshold * segment_steps * ijk_step_size
        if mm < mmcut:
            ijk_step_size *= step_cut_factor
        else:
            ijk_step_size = min(ijk_step_size*step_grow_factor,
                                ijk_step_size_max)
        move_tf = M.multiply_matrices(move_tf, seg_tf)
        if request_stop_cb:
            shift, angle = M.shift_and_angle(move_tf, rc)
            if request_stop_cb('%d steps, shift %.3g, rotation %.3g degrees'
                               % (step, shift, angle)):
                break

    # Record statistics of optimization.
    shift, angle = M.shift_and_angle(move_tf, rc)
    axis, axis_point, angle, axis_shift = M.axis_center_angle_shift(move_tf)
    xyz_to_ijk_tf = M.multiply_matrices(xyz_to_ijk_transform, move_tf)
    stats = {'shift': shift, 'axis': axis, 'axis point': axis_point,
             'angle': angle, 'axis shift': axis_shift, 'steps': step,
             'points': len(points), 'transform': move_tf}

    amv, npts = average_map_value(points, xyz_to_ijk_tf, data_array, syminv)
    stats['average map value'] = amv
    stats['points in map'] = npts      # Excludes out-of-bounds points
    stats['symmetries'] = len(symmetries)
    if not point_weights is None:
        map_values = volume_values(points, xyz_to_ijk_tf, data_array, syminv)
        olap, cor, corm = overlap_and_correlation(point_weights, map_values)
        stats['overlap'] = olap
        stats['correlation'] = cor
        stats['correlation about mean'] = corm
                
    return move_tf, stats
    
# -----------------------------------------------------------------------------
#
def step_to_maximum(points, point_weights, data_array, xyz_to_ijk_transform,
                    steps, ijk_step_size,
                    optimize_translation, optimize_rotation,
                    rotation_center, metric, syminv = []):

    step_types = []
    if optimize_translation:
        step_types.append(translation_step)
    if optimize_rotation:
        step_types.append(rotation_step)
        
    from Matrix import identity_matrix, multiply_matrices
    move_tf = identity_matrix()

    if step_types:
        for step in range(steps):
            calculate_step = step_types[step % len(step_types)]
            xyz_to_ijk_tf = multiply_matrices(xyz_to_ijk_transform, move_tf)
            step_tf = calculate_step(points, point_weights,
                                     rotation_center, data_array,
                                     xyz_to_ijk_tf, ijk_step_size, metric,
                                     syminv)
            move_tf = multiply_matrices(move_tf, step_tf)

    return move_tf

# -----------------------------------------------------------------------------
#
def translation_step(points, point_weights, center, data_array,
                     xyz_to_ijk_transform, ijk_step_size, metric,
                     syminv = []):

    g = gradient_direction(points, point_weights, data_array,
                           xyz_to_ijk_transform, metric, syminv)
    from numpy import array, float, dot as matrix_multiply
    tf = array(xyz_to_ijk_transform)
    gijk = matrix_multiply(tf[:,:3], g)
    from Matrix import norm
    n = norm(gijk)
    if n > 0:
        delta = g * (ijk_step_size / n)
    else:
        delta = array((0,0,0), float)

    delta_tf = ((1,0,0,delta[0]),
                (0,1,0,delta[1]),
                (0,0,1,delta[2]))

    return delta_tf

# -----------------------------------------------------------------------------
#
def gradient_direction(points, point_weights, data_array,
                       xyz_to_ijk_transform, metric = 'sum product',
                       syminv = []):

    if metric == 'sum product':
        f = sum_product_gradient_direction
        kw = {}
    elif metric == 'correlation':
        f = correlation_gradient_direction
        kw = {'about_mean':False,
              'syminv': syminv}
    elif metric == 'correlation about mean':
        f = correlation_gradient_direction
        kw = {'about_mean':True,
              'syminv': syminv}
    a = f(points, point_weights, data_array, xyz_to_ijk_transform, **kw)
    return a

# -----------------------------------------------------------------------------
#
def sum_product_gradient_direction(points, point_weights, data_array,
                                   xyz_to_ijk_transform):

    gradients = volume_gradients(points, xyz_to_ijk_transform, data_array)
    if point_weights is None:
        from numpy import float64
        g = gradients.sum(axis=0, dtype = float64)
    else:
        import Matrix as M
        g = M.vector_sum(point_weights, gradients)
    return g

# -----------------------------------------------------------------------------
# Derivative of correlation with respect to translation of points.
#
# g = (|v-vm|^2*sum(wi*vi,j) - sum(wi*vi)*sum((vi-vm)*vi,j)) / |w||v-vm|^3
#
def correlation_gradient_direction(points, point_weights, data_array,
                                   xyz_to_ijk_transform, about_mean = False,
                                   syminv = []):

    # TODO: Exclude points outside data.  Currently treated as zero values.
    values = volume_values(points, xyz_to_ijk_transform, data_array, syminv)
    gradients = volume_gradients(points, xyz_to_ijk_transform, data_array,
                                 syminv)
    import _distances as D
    g = D.correlation_gradient(point_weights, values, gradients, about_mean)
    return g

# -----------------------------------------------------------------------------
#
def torque_axis(points, point_weights, center, data_array,
                xyz_to_ijk_transform, metric = 'sum product', syminv = []):

    if metric == 'sum product':
        f = sum_product_torque_axis
        kw = {}
    elif metric == 'correlation':
        f = correlation_torque_axis
        kw = {'about_mean':False,
              'syminv': syminv}
    elif metric == 'correlation about mean':
        f = correlation_torque_axis
        kw = {'about_mean':True,
              'syminv': syminv}
    a = f(points, point_weights, center, data_array, xyz_to_ijk_transform, **kw)
    return a
    
# -----------------------------------------------------------------------------
#
def sum_product_torque_axis(points, point_weights, center, data_array,
                            xyz_to_ijk_transform):

    gradients = volume_gradients(points, xyz_to_ijk_transform, data_array)
    import _distances as dist
    tor = dist.torque(points, point_weights, gradients, center)
    return tor

# -----------------------------------------------------------------------------
# Correlation variation with respect to rotation of points about center.
# 
#       dc/da = (t,u)           at a = 0.
#
# where c is correlation, a is rotation angle, u is axis unit vector, and t is
# the torque axis defined by this equation and returned by this routine.
#
# t = (|v-vm|^2*sum(wi*rixDvi) - sum(wi*vi)*sum((vi-vm)*rixDvi)) / |w||v-vm|^3
#
def correlation_torque_axis(points, point_weights, center, data_array,
                            xyz_to_ijk_transform, about_mean = False,
                            syminv = []):

    # TODO: Exclude points outside data.  Currently treated as zero values.
    values = volume_values(points, xyz_to_ijk_transform, data_array, syminv)
    import _distances as D
    if len(syminv) == 0:
        gradients = volume_gradients(points, xyz_to_ijk_transform, data_array)
        tor = D.correlation_torque(points, point_weights, values, gradients,
                                   center, about_mean)
    else:
        pxg = volume_torques(points, center, xyz_to_ijk_transform, data_array,
                             syminv)
        tor = D.correlation_torque2(point_weights, values, pxg, about_mean)

    return tor

# -----------------------------------------------------------------------------
#
def volume_values(points, xyz_to_ijk_transform, data_array, syminv = [],
                  return_outside = False):

    import VolumeData as VD
    if len(syminv) == 0:
        values, outside = VD.interpolate_volume_data(points,
                                                     xyz_to_ijk_transform,
                                                     data_array)
    else:
        import Matrix as M
        from numpy import zeros, float32, add
        values = zeros((len(points),), float32)
        for sinv in syminv:
            tf = M.multiply_matrices(xyz_to_ijk_transform, sinv)
            # TODO: Make interpolation reuse the same array.
            v, outside = VD.interpolate_volume_data(points, tf, data_array)
            add(values, v, values)
        outside = []

    if return_outside:
        return values, outside

    return values

# -----------------------------------------------------------------------------
#
def volume_gradients(points, xyz_to_ijk_transform, data_array, syminv = []):

    import VolumeData as VD
    if len(syminv) == 0:
        gradients, outside = VD.interpolate_volume_gradient(
            points, xyz_to_ijk_transform, data_array)
    else:
        import Matrix as M
        from numpy import zeros, float32, add
        gradients = zeros(points.shape, float32)
        p = points.copy()
        for sinv in syminv:
            # TODO: Make interpolation use original point array.
            p[:] = points
            M.transform_points(p, sinv)
            g, outside = VD.interpolate_volume_gradient(p, xyz_to_ijk_transform,
                                                        data_array)
            add(gradients, g, gradients)

    return gradients

# -----------------------------------------------------------------------------
#
def volume_torques(points, center, xyz_to_ijk_transform, data_array,
                   syminv = []):

    import _distances as D
    import VolumeData as VD
    if len(syminv) == 0:
        gradients, outside = VD.interpolate_volume_gradient(
            points, xyz_to_ijk_transform, data_array)
        torques = gradients
        D.torques(points, center, gradients, torques)
    else:
        import Matrix as M
        from numpy import zeros, float32, add
        torques = zeros(points.shape, float32)
        p = points.copy()
        for sinv in syminv:
            # TODO: Make interpolation use original point array.
            p[:] = points
            M.transform_points(p, sinv)
            g, outside = VD.interpolate_volume_gradient(p, xyz_to_ijk_transform,
                                                        data_array)
            D.torques(p, center, g, g)
            add(torques, g, torques)

    return torques
    
# -----------------------------------------------------------------------------
#
def rotation_step(points, point_weights, center, data_array,
                  xyz_to_ijk_transform, ijk_step_size, metric,
                  syminv = []):

    axis = torque_axis(points, point_weights, center, data_array,
                       xyz_to_ijk_transform, metric, syminv)

    from Matrix import norm, rotation_transform
    na = norm(axis)
    if len(points) == 1 or na == 0:
        axis = (0,0,1)
        angle = 0
    else:
        axis /= na
        angle = angle_step(axis, points, center, xyz_to_ijk_transform,
                           ijk_step_size)
    move_tf = rotation_transform(axis, angle, center)
    return move_tf
    

# -----------------------------------------------------------------------------
# Return angle such that rotating point about given axis and center causes the
# largest motion in ijk space to equal ijk_step_size.
#
def angle_step(axis, points, center, xyz_to_ijk_transform, ijk_step_size):

    import Matrix as m
    tf = m.multiply_matrices(m.zero_translation(xyz_to_ijk_transform),
                             m.cross_product_transform(axis),
                             m.translation_matrix([-x for x in center]))

    import _distances as dist
    av = dist.maximum_norm(points, tf)
    
    if av > 0:
        from math import pi
        angle = (ijk_step_size / av) * 180.0/pi
    else:
        angle = 0
    return angle
    
# -----------------------------------------------------------------------------
#
def maximum_ijk_motion(points, xyz_to_ijk_transform, move_tf):

    from Matrix import multiply_matrices, apply_matrix, maximum_norm
    ijk_moved_tf = multiply_matrices(xyz_to_ijk_transform, move_tf)

    from numpy import subtract
    diff_tf = subtract(ijk_moved_tf, xyz_to_ijk_transform)

    import _distances as dist
    d = dist.maximum_norm(points, diff_tf)
    
    return d


# -----------------------------------------------------------------------------
#
def atom_coordinates(atoms):

    from _multiscale import get_atom_coordinates
    points = get_atom_coordinates(atoms, transformed = True)
    return points

# -----------------------------------------------------------------------------
#
def average_map_value_at_atom_positions(atoms, volume = None):

    if volume is None:
        from VolumeViewer import active_volume
        volume = active_volume()

    points = atom_coordinates(atoms)

    if volume is None or len(points) == 0:
        return 0, len(points)

    from chimera import Xform
    data_array, xyz_to_ijk_transform = \
        volume.matrix_and_transform(Xform(), subregion = None, step = 1)

    amv, npts = average_map_value(points, xyz_to_ijk_transform, data_array)
    return amv, npts

# -----------------------------------------------------------------------------
#
def average_map_value(points, xyz_to_ijk_transform, data_array, syminv = []):

    values, outside = volume_values(points, xyz_to_ijk_transform,
                                    data_array, syminv, return_outside = True)
    from numpy import float64
    s = values.sum(dtype = float64)
    n = len(points) - len(outside)
    if n > 0:
        amv = s / n
    else:
        amv = 0
    return amv, n

# -----------------------------------------------------------------------------
# Returns of grid points of map above specified threshold.
# Returns global coordinates by default.
# If above_threshold is false filter out points with zero density.
#
from chimera import Xform
def map_points_and_weights(v, above_threshold, point_to_world_xform = Xform()):

    m, xyz_to_ijk_tf = v.matrix_and_transform(point_to_world_xform,
                                              subregion = None, step = None)
          
    if above_threshold:
        # Keep only points where density is above lowest displayed threshold
        threshold = min(v.surface_levels)
        import _volume
        points_int = _volume.high_indices(m, threshold)
        from numpy import single as floatc
        points = points_int.astype(floatc)
        weights = m[points_int[:,2],points_int[:,1],points_int[:,0]]
    else:
        from numpy import single as floatc, ravel, nonzero, take
        from VolumeData import grid_indices
        points = grid_indices(m.shape[::-1], floatc)        # i,j,k indices
        weights = ravel(m).astype(floatc)
        # TODO: use numpy.count_nonzero() after updating to numpy 1.6
        nz = nonzero(weights)[0]
        if len(nz) < len(weights):
            points = take(points, nz, axis=0)
            weights = take(weights, nz, axis=0)

    import Matrix as M
    M.transform_points(points, M.invert_matrix(xyz_to_ijk_tf))

    return points, weights
    
# -----------------------------------------------------------------------------
# xform is transform to apply to first map in global coordinates.
#
def map_overlap_and_correlation(map1, map2, above_threshold, xform = None):

    p, w1 = map_points_and_weights(map1, above_threshold)
    if xform is None:
        from chimera import Xform
        xform = Xform()
    w2 = map2.interpolated_values(p, xform, subregion = None, step = None)
    return overlap_and_correlation(w1, w2)

# -----------------------------------------------------------------------------
#
def overlap_and_correlation(v1, v2):

    v1 = float_array(v1)
    v2 = float_array(v2)
    if v2.dtype != v1.dtype:
        # One array is 32-bit float, one is 64-bit float.
        # inner_product_64() requires they have same type.
        from numpy import float64
        v1 = v1.astype(float64, copy = False)
        v2 = v2.astype(float64, copy = False)
    # Use 64-bit accumulation of sums to avoid round-off errors.
    from Matrix import inner_product_64
    olap = inner_product_64(v1, v2)
    n1 = inner_product_64(v1, v1)
    n2 = inner_product_64(v2, v2)
    n = len(v1)
    from numpy import sum, float64
    m1 = sum(v1, dtype = float64) / n
    m2 = sum(v2, dtype = float64) / n
    d2 = (n1 - n*m1*m1)*(n2 - n*m2*m2)
    if d2 < 0:
        d2 = 0          # This only happens due to rounding error.
    from math import sqrt
    d = sqrt(d2)
    corm = (olap - n*m1*m2) / d if d > 0 else 0.0
    d = sqrt(n1*n2)
    cor = olap / d if d > 0 else 0.0
    return olap, cor, corm
    
# -----------------------------------------------------------------------------
#
def float_array(a):

    from numpy import ndarray, float32, float64, single as floatc, array
    if type(a) is ndarray and a.dtype in (float32, float64):
        return a
    return array(a, floatc)

# -----------------------------------------------------------------------------
# Move selected atoms to local maxima of map shown by volume viewer.
# Each atom is moved independently.
#
def move_atoms_to_maxima():

    from chimera.selection import currentAtoms
    atoms = currentAtoms()
    if len(atoms) == 0:
        from chimera.replyobj import status
        status('No atoms selected.')
        return
        
    for a in atoms:
        move_atom_to_maximum(a)

# -----------------------------------------------------------------------------
#
def move_atom_to_maximum(a, max_steps = 2000,
                         ijk_step_size_min = 0.001, ijk_step_size_max = 0.5):

    from VolumeViewer import active_volume
    dr = active_volume()
    if dr == None or dr.model_transform() == None:
        from chimera.replyobj import status
        status('No data shown by volume viewer dialog')
        return

    points = atom_coordinates([a])
    point_weights = None
    move_tf, stats = motion_to_maximum(points, point_weights, dr, max_steps,
                                       ijk_step_size_min, ijk_step_size_max,
                                       optimize_translation = True,
                                       optimize_rotation = False)

    # Update atom position.
    from Matrix import chimera_xform
    xf = chimera_xform(move_tf)
    mxf = a.molecule.openState.xform
    p = mxf.inverse().apply(xf.apply(a.xformCoord()))
    a.setCoord(p)

# -----------------------------------------------------------------------------
#
def atoms_outside_contour(atoms, volume = None):

    if volume is None:
        from VolumeViewer import active_volume
        volume = active_volume()
    points = atom_coordinates(atoms)
    from chimera import Xform
    poc, clevel = points_outside_contour(points, Xform(), volume)
    return poc, clevel

# -----------------------------------------------------------------------------
#
def points_outside_contour(points, xf, volume):

    if volume is None:
        return None, None

    levels = volume.surface_levels
    if len(levels) == 0:
        return None, None

    contour_level = min(levels)
    values = volume.interpolated_values(points, xf, subregion = None, step = None)
    from numpy import sum
    poc = sum(values < contour_level)
    return poc, contour_level

# -----------------------------------------------------------------------------
#
def atom_fit_message(atoms, volume, stats):
    
    molecules = list(set([a.molecule for a in atoms]))
    mnames = ['%s (%s)' % (m.name, m.oslIdent()) for m in molecules]
    mnames = ', '.join(mnames)
    plural = 's' if len(molecules) > 1 else ''
    vname = volume.name
    natom = stats['points']
    aoc = stats.get('atoms outside contour', None)
    clevel = stats.get('contour level', None)
    ave = stats['average map value']
    steps = stats['steps']
    shift = stats['shift']
    angle = stats['angle']

    message = ('Fit molecule%s %s to map %s using %d atoms\n'
               % (plural, mnames, vname, natom) +
               '  average map value = %.4g, steps = %d\n' % (ave, steps) +
               '  shifted from previous position = %.3g\n' % (shift,) +
               '  rotated from previous position = %.3g degrees\n' % (angle,))
    if (not clevel is None) and (not aoc is None):
      message += ('  atoms outside contour = %d, contour level = %.5g\n'
                  % (aoc, clevel))

    return message

# -----------------------------------------------------------------------------
#
def map_fit_message(moved_map, fixed_map, stats):
    
    mmname = moved_map.name
    fmname = fixed_map.name
    np = stats['points']
    steps = stats['steps']
    shift = stats['shift']
    angle = stats['angle']
    cor = stats['correlation']
    corm = stats['correlation about mean']
    olap = stats['overlap']
    nsym = stats['symmetries']
    sym = ', %d symmetries' % nsym if nsym else ''

    message = (
        'Fit map %s in map %s using %d points%s\n' % (mmname, fmname, np, sym) +
        '  correlation = %.4g, correlation about mean = %.4g, overlap = %.4g\n' % (cor, corm, olap) +
        '  steps = %d, shift = %.3g, angle = %.3g degrees\n'
        % (steps, shift, angle))
    return message

# -----------------------------------------------------------------------------
#
def transformation_matrix_message(model, map, transform = None):
    
    m = model
    mname = '%s (%s)' % (m.name, m.oslIdent())
    mxf = m.openState.xform

    f = map
    fname = '%s (%s)' % (f.name, f.oslIdent())
    fxf = f.openState.xform
    
    if transform is None:
        mxf.premultiply(fxf.inverse())
        from Matrix import xform_matrix
        mtf = xform_matrix(mxf)
    else:
        mtf = transform
    message = ('Position of %s relative to %s coordinates:\n'
               % (mname, fname))
    from Matrix import transformation_description
    message += transformation_description(mtf)
    return message

# -----------------------------------------------------------------------------
#
def simulated_map(atoms, res, mwm):

    v = find_simulated_map(atoms, res, mwm)
    if v is None:
      # Need to be able to move map independent of molecule if changing
      #  atom coordinates.
      from chimera import OpenModels
      id = None if mwm else OpenModels.Default
      from MoleculeMap import molecule_map
      v = molecule_map(atoms, res, modelId = id)
      v.display = False
      v.fitsim_params = (set(atoms), res, mwm)
    return v

# -----------------------------------------------------------------------------
#
def find_simulated_map(atoms, res, mwm):

    a = set(atoms)
    from VolumeViewer import volume_list
    for v in volume_list():
      if hasattr(v, 'fitsim_params') and v.fitsim_params == (a, res, mwm):
        return v
    return None

# -----------------------------------------------------------------------------
# Geometric center of points above contour level.
#
def volume_center_point(v, xform):

    points, point_weights = map_points_and_weights(v, above_threshold = True,
                                                   point_to_world_xform = xform)
    if len(points) == 0:
        points = v.xyz_bounds()
    from numpy import sum, float64
    c = sum(points, axis=0, dtype = float64) / len(points)
    return c

# -----------------------------------------------------------------------------
# Return indices of points that are closer to refpt then any symmetrically
# transformed copy of refpt.
#
def asymmetric_unit_points(points, refpt, symmetries):

    diff = points - refpt
    from numpy import sum, minimum, nonzero
    d = sum(diff*diff, axis = 1)
    dsmin = d.copy()
    import Matrix as M
    for sym in symmetries:
        srefpt = M.apply_matrix(sym, refpt)
        diff = points - srefpt
        ds = sum(diff*diff, axis = 1)
        minimum(dsmin, ds, dsmin) 
    indices = nonzero(d == dsmin)[0]
        
    return indices
