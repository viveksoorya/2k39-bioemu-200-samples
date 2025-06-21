# -----------------------------------------------------------------------------
# Simulate an electron density map for an atomic model at a specfied
# resolution.  The simulated map is useful for fitting the model into
# an experimental map using correlation coefficient as a goodness of fit.
#
def molmap_command(cmdname, args):

    from Commands import doExtensionFunc
    doExtensionFunc(molecule_map, args,
                    specInfo = [('atomSpec','atoms','atoms'),
                                ('onGridSpec', 'onGrid', 'models')])

# -----------------------------------------------------------------------------
#
from math import sqrt, pi
def molecule_map(atoms, resolution,
                 gridSpacing = None,    # default is 1/3 resolution
                 edgePadding = None,    # default is 3 times resolution
                 onGrid = None,		# use this volume model grid instead of bounding grid
                 cutoffRange = 5,       # in standard deviations
                 sigmaFactor = 1/(pi*sqrt(2)), # standard deviation / resolution
                 symmetry = None,       # Equivalent to sym group option.
                 center = (0,0,0),      # Center of symmetry.
                 axis = (0,0,1),        # Axis of symmetry.
                 coordinateSystem = None,       # Coordinate system of symmetry.
                 displayThreshold = 0.95, # fraction of total density
                 modelId = None, # integer
                 replace = True,
		 showDialog = True
                 ):

    from Commands import CommandError
    if len(atoms) == 0:
        raise CommandError, 'No atoms specified'

    for vname in ('resolution', 'gridSpacing', 'edgePadding',
                  'cutoffRange', 'sigmaFactor'):
        value = locals()[vname]
        if not isinstance(value, (float,int,type(None))):
            raise CommandError, '%s must be number, got "%s"' % (vname,str(value))

    if edgePadding is None:
        pad = 3*resolution
    else:
        pad = edgePadding

    if gridSpacing is None:
        step = (1./3) * resolution
    else:
        step = gridSpacing

    if onGrid:
        from Commands import single_volume
        on_grid = single_volume(onGrid)
    else:
        on_grid = None

    csys = None
    if symmetry is None:
        transforms = []
    else:
        from Commands import openstate_arg
        if coordinateSystem:
            csys = openstate_arg(coordinateSystem)
        from SymmetryCopies.symcmd import parse_symmetry
        transforms, csys = parse_symmetry(symmetry, center, axis, csys,
                                          atoms[0].molecule, 'molmap')

    if not modelId is None:
        from Commands import parse_model_id
        modelId = parse_model_id(modelId)

    v = make_molecule_map(atoms, resolution, step, pad, on_grid,
                          cutoffRange, sigmaFactor, transforms, csys,
                          displayThreshold, modelId, replace, showDialog)
    return v

# -----------------------------------------------------------------------------
#
def make_molecule_map(atoms, resolution, step, pad, on_grid,
                      cutoff_range, sigma_factor, transforms, csys,
                      display_threshold, model_id,
                      replace, show_dialog):

    atoms = tuple(atoms)
    grid, molecules = molecule_grid_data(atoms, resolution, step, pad, on_grid,
                                         cutoff_range, sigma_factor,
                                         transforms, csys)

    from chimera import openModels as om
    if replace:
        from VolumeViewer import volume_list
        vlist = [v for v in volume_list()
                 if getattr(v, 'molmap_atoms', None) == atoms]
        om.close(vlist)

    from VolumeViewer import volume_from_grid_data
    v = volume_from_grid_data(grid, open_model = False,
                              show_dialog = show_dialog)
    v.initialize_thresholds(mfrac = (display_threshold, 1), replace = True)
    v.show()

    v.molmap_atoms = tuple(atoms)   # Remember atoms used to calculate volume
    v.molmap_parameters = (resolution, step, pad, cutoff_range, sigma_factor)

    m0 = atoms[0].molecule
    xf = on_grid.openState.xform if on_grid else m0.openState.xform
    if len(molecules) == 1 and model_id is None and on_grid is None:
        # Use same model id with new subid
        om.add([v], baseId = m0.id, subid = max(m.subid for m in om.list(id = m0.id))+1)
        v.openState.xform = xf
    else:
        if model_id is None:
            model_id = (om.Default, om.Default)
        om.add([v], baseId = model_id[0], subid = model_id[1])
        v.openState.xform = xf

    return v

# -----------------------------------------------------------------------------
#
def molecule_grid_data(atoms, resolution, step, pad, on_grid,
                       cutoff_range, sigma_factor,
                       transforms = [], csys = None):

    from _multiscale import get_atom_coordinates
    xyz = get_atom_coordinates(atoms, transformed = True)

    # Transform coordinates to local coordinates of the molecule containing
    # the first atom.  This handles multiple unaligned molecules.
    # Or if on_grid is specified transform to grid coordinates.
    m0 = atoms[0].molecule
    xf = on_grid.openState.xform if on_grid else m0.openState.xform
    import Matrix as M
    M.transform_points(xyz, M.xform_matrix(xf.inverse()))
    if csys:
        xf.premultiply(csys.xform.inverse())
    tflist = M.coordinate_transform_list(transforms, M.xform_matrix(xf))

    anum = [a.element.number for a in atoms]

    molecules = set([a.molecule for a in atoms])
    if len(molecules) > 1:
        name = 'molmap res %.3g' % (resolution,)
    else:
        name = 'molmap %s res %.3g' % (m0.name, resolution)

    if on_grid:
        from numpy import float32
        grid = on_grid.region_grid(on_grid.region, float32)
    else:
        grid = bounding_grid(xyz, step, pad, tflist)
    grid.name = name

    sdev = resolution * sigma_factor
    add_gaussians(grid, xyz, anum, sdev, cutoff_range, tflist)

    return grid, molecules

# -----------------------------------------------------------------------------
#
def bounding_grid(xyz, step, pad, transforms):

    xyz_min, xyz_max = point_bounds(xyz, transforms)
    origin = [x-pad for x in xyz_min]
    from math import ceil
    shape = [int(ceil((xyz_max[a] - xyz_min[a] + 2*pad) / step)) for a in (2,1,0)]
    from numpy import zeros, float32
    matrix = zeros(shape, float32)
    from VolumeData import Array_Grid_Data
    grid = Array_Grid_Data(matrix, origin, (step,step,step))
    return grid

# -----------------------------------------------------------------------------
#
def add_gaussians(grid, xyz, weights, sdev, cutoff_range, transforms = []):

    from numpy import zeros, float32, empty
    sdevs = zeros((len(xyz),3), float32)
    for a in (0,1,2):
        sdevs[:,a] = sdev / grid.step[a]

    import Matrix as M
    if len(transforms) == 0:
        transforms = [M.identity_matrix()]
    from _gaussian import sum_of_gaussians
    ijk = empty(xyz.shape, float32)
    matrix = grid.matrix()
    for tf in transforms:
        ijk[:] = xyz
        M.transform_points(ijk, M.multiply_matrices(grid.xyz_to_ijk_transform, tf))
        sum_of_gaussians(ijk, weights, sdevs, cutoff_range, matrix)

    from math import pow, pi
    normalization = pow(2*pi,-1.5)*pow(sdev,-3)
    matrix *= normalization

# -----------------------------------------------------------------------------
#
def point_bounds(xyz, transforms = []):

    from _multiscale import bounding_box
    if transforms:
        from numpy import empty, float32
        xyz0 = empty((len(transforms),3), float32)
        xyz1 = empty((len(transforms),3), float32)
        txyz = empty(xyz.shape, float32)
        import Matrix as M
        for i, tf in enumerate(transforms):
            txyz[:] = xyz
            M.transform_points(txyz, tf)
            xyz0[i,:], xyz1[i,:] = bounding_box(txyz)
        xyz_min, xyz_max = xyz0.min(axis = 0), xyz1.max(axis = 0)
    else:
        xyz_min, xyz_max = bounding_box(xyz)

    return xyz_min, xyz_max
