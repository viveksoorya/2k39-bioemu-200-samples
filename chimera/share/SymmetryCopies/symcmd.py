# -----------------------------------------------------------------------------
# Command to make copies of a molecule positioned using volume data symmetries
# or BIOMT PDB header matrices, with positions updated whenever the original
# PDB model is moved relative to a reference volume model.
#

# -----------------------------------------------------------------------------
#
def symmetry_copies_command(cmdname, args):

    from Commands import parse_arguments
    from Commands import molecules_arg, model_arg, openstate_arg
    from Commands import string_arg, float_arg, bool_arg, model_id_arg

    req_args = ()
    opt_args = (('molecules', molecules_arg),
                ('coordinateSystem', openstate_arg),)
    kw_args = (('group', string_arg),
               ('center', string_arg),
               ('axis', string_arg),
               ('contact', float_arg),
               ('range', float_arg),
               ('occupancy', float_arg),
               ('update', bool_arg),
               ('biomtSet', bool_arg),
               ('surfaces', string_arg),
               ('resolution', float_arg),
               ('modelId', model_id_arg),
               )
    kw = parse_arguments(cmdname, args, req_args, opt_args, kw_args)
    symmetry_copies(**kw)
                    
# -----------------------------------------------------------------------------
#
def symmetry_copies(molecules = None, group = 'biomt',
                    center = (0,0,0), axis = (0,0,1), coordinateSystem = None,
                    contact = None, range = None, occupancy = None,
                    update = False, biomtSet = True,
                    surfaces = False, resolution = None, modelId = None):

    from Commands import CommandError, bool_arg

    if molecules is None:
        dmol = default_molecule()
        if dmol:
            molecules = [dmol]

    if molecules is None or len(molecules) == 0:
        raise CommandError('No molecules specified')

    tflist, csys = parse_symmetry(group, center, axis, coordinateSystem,
                                  molecules[0], 'sym')

    if surfaces and surfaces != 'all':
        surfaces = bool_arg(surfaces)
        
    cc = 0
    for m in molecules:
        tflist = filter_transforms(m, tflist, csys, contact, range, occupancy)
        copies = create_symmetry_copies(m, tflist, csys, surfaces, resolution,
                                        modelId)
        cc += len(copies)
        if copies and update and m.openState != csys:
            add_symmetry_update_handler(m)
        if copies and biomtSet:
            m.sym_set_biomt = True
            set_pdb_biomt_remarks(m)

    if cc == 0 and surfaces != 'all':
        raise CommandError('No symmetric molecule copies')

# -----------------------------------------------------------------------------
#
def set_pdb_biomt_remarks(m):

    xflist = symmetry_xforms(m)
    import PDBmatrices
    PDBmatrices.set_pdb_biomt_remarks(m, xflist)

# -----------------------------------------------------------------------------
#
def parse_symmetry(group, center, axis, csys, molecule, cmdname):

    from Commands import parse_center_axis
    c, a, csys_ca = parse_center_axis(center, axis, csys, cmdname)

    # Handle products of symmetry groups.
    groups = group.split('*')
    tflists = []
    import Matrix as M
    for g in groups:
        tflist, csys_g = group_symmetries(g, c.data(), a.data(), csys, molecule)
        if csys is None:
            csys = csys_g or csys_ca or molecule.openState
        elif csys_g and not csys_g is csys:
            ctf = M.multiply_matrices(M.xform_matrix(csys_g.xform.inverse()),
                                      M.xform_matrix(csys.xform))
            tflist = M.coordinate_transform_list(tflist, ctf)
        tflists.append(tflist)

    tflist = reduce(M.matrix_products, tflists)
    
    return tflist, csys

# -----------------------------------------------------------------------------
#
def group_symmetries(group, center, axis, csys, mol):

    import Symmetry
    from Commands import CommandError

    g0 = group[:1].lower()
    gfields = group.split(',')
    nf = len(gfields)
    recenter = True
    if g0 in ('c', 'd'):
        # Cyclic or dihedral symmetry: C<n>, D<n>
        try:
            n = int(group[1:])
        except ValueError:
            raise CommandError('Invalid symmetry group syntax "%s"' % group)
        if n < 1:
            raise CommandError('Cn or Dn with n = %d < 1' % (n,))
        if g0 == 'c':
            tflist = Symmetry.cyclic_symmetry_matrices(n)
        else:
            tflist = Symmetry.dihedral_symmetry_matrices(n)
    elif g0 == 'i':
        # Icosahedral symmetry: i[,<orientation>]
        if nf == 1:
            orientation = '222'
        elif nf == 2:
            orientation = gfields[1]
            if not orientation in Symmetry.icosahedral_orientations:
                raise CommandError('Unknown icosahedron orientation "%s"'
                                   % orientation)
        else:
            raise CommandError('Invalid symmetry group syntax "%s"' % group)
        tflist = Symmetry.icosahedral_symmetry_matrices(orientation)
    elif g0 == 't' and nf <= 2:
        # Tetrahedral symmetry t[,<orientation]
        if nf == 1:
            orientation = '222'
        elif nf == 2:
            orientation = gfields[1]
            if not orientation in Symmetry.tetrahedral_orientations:
                tos = ', '.join(Symmetry.tetrahedral_orientations)
                raise CommandError('Unknown tetrahedral symmetry orientation %s'
                                   ', must be one of %s' % (gfields[1], tos))
        else:
            raise CommandError('Invalid symmetry group syntax "%s"' % group)
        tflist = Symmetry.tetrahedral_symmetry_matrices(orientation)
    elif g0 == 'o':
        # Octahedral symmetry
        if nf == 1:
            tflist = Symmetry.octahedral_symmetry_matrices()
        else:
            raise CommandError('Invalid symmetry group syntax "%s"' % group)
    elif g0 == 'h':
        # Helical symmetry: h,<rise>,<angle>,<n>[,<offset>]
        if nf < 4 or nf > 5:
            raise CommandError('Invalid symmetry group syntax "%s"' % group)
        try:
            param = [float(f) for f in gfields[1:]]
        except ValueError:
            raise CommandError('Invalid symmetry group syntax "%s"' % group)
        if len(param) == 3:
            param.append(0.0)
        rise, angle, n, offset = param
        n = int(n)
        tflist = [Symmetry.helical_symmetry_matrix(rise, angle, n = i+offset)
                  for i in range(n)]
    elif gfields[0].lower() == 'shift' or (g0 == 't' and nf >= 3):
        # Translation symmetry: t,<n>,<distance> or t,<n>,<dx>,<dy>,<dz>
        if nf != 3 and nf != 5:
            raise CommandError('Invalid symmetry group syntax "%s"' % group)
        try:
            param = [float(f) for f in gfields[1:]]
        except ValueError:
            raise CommandError('Invalid symmetry group syntax "%s"' % group)
        n = param[0]
        if n != int(n):
            raise CommandError('Invalid symmetry group syntax "%s"' % group)
        n = int(n)
        if nf == 3:
          delta = (0,0,param[1])
        else:
          delta = param[1:]
        tflist = Symmetry.translation_symmetry_matrices(n, delta)
    elif group.lower() == 'biomt':
        # Biological unit
        from Molecule import biological_unit_matrices
        tflist = biological_unit_matrices(mol)
        if len(tflist) == 0:
            raise CommandError('Molecule %s has no biological unit info'
                               % mol.name)
        from Matrix import is_identity_matrix
        if len(tflist) == 1 and is_identity_matrix(tflist[0]):
            from chimera import replyobj
            replyobj.status('Molecule %s is the biological unit' % mol.name)
        if csys is None:
            csys = mol.openState
        else:
            tflist = transform_coordinates(tflist, mol.openState, csys)
        recenter = False
    elif g0 == '#':
        from Commands import models_arg
        if nf == 1:
            mlist = [m for m in models_arg(group) if model_symmetry(m, csys)]
            if len(mlist) == 0:
                raise CommandError('No symmetry for "%s"' % group)
            elif len(mlist) > 1:
                raise CommandError('Multiple models "%s"' % group)
            m = mlist[0]
            tflist = model_symmetry(m, csys)
            if csys is None:
                csys = m.openState
            recenter = False
        elif nf == 2:
            gf0, gf1 = gfields
            mlist = [m for m in models_arg(gf0)
                     if hasattr(m, 'placements') and callable(m.placements)]
            if len(mlist) == 0:
                raise CommandError('No placements for "%s"' % gf0)
            elif len(mlist) > 1:
                raise CommandError('Multiple models with placements "%s"' % gf0)
            m = mlist[0]
            tflist = m.placements(gf1)
            if len(tflist) == 0:
                raise CommandError('No placements "%s" for "%s"' % (gf1, gf0))
            import Molecule as MC, Matrix as M
            c = MC.molecule_center(mol)
            cg = M.apply_matrix(M.xform_matrix(mol.openState.xform), c)
            cm = M.apply_matrix(M.xform_matrix(m.openState.xform.inverse()), cg)
            tflist = make_closest_placement_identity(tflist, cm)
            if csys is None:
                csys = m.openState
            recenter = False
    else:
        raise CommandError('Unknown symmetry group "%s"' % group)

    # Apply center and axis transformation.
    if recenter and (tuple(center) != (0,0,0) or tuple(axis) != (0,0,1)):
        import Matrix as M
        tf = M.multiply_matrices(M.vector_rotation_transform(axis, (0,0,1)),
                                 M.translation_matrix([-c for c in center]))
        tflist = M.coordinate_transform_list(tflist, tf)

    return tflist, csys

# -----------------------------------------------------------------------------
#
def model_symmetry(model, csys):

    from VolumeViewer import Volume
    from chimera import Molecule
    if isinstance(model, Volume):
        tflist = model.data.symmetries
    elif isinstance(model, Molecule):
        from Molecule import biological_unit_matrices
        tflist = biological_unit_matrices(model)
    else:
        tflist = []

    if len(tflist) <= 1:
        return None

    if not csys is None:
        tflist = transform_coordinates(tflist, model.openState, csys)

    return tflist

# -----------------------------------------------------------------------------
#
def transform_coordinates(tflist, csys, to_csys):

    if to_csys == csys:
        return tflist
    xf = csys.xform.inverse()
    xf.multiply(to_csys.xform)
    import Matrix as M
    return M.coordinate_transform_list(tflist, M.xform_matrix(xf))

# -----------------------------------------------------------------------------
# Find the transform that maps (0,0,0) closest to the molecule center and
# multiply all transforms by the inverse of that transform.  This chooses
# the best placement for the current molecule position and makes all other
# placements relative to that one.
#
def make_closest_placement_identity(tflist, center):

    from numpy import array
    d = array(tflist)[:,:,3] - center
    d2 = (d*d).sum(axis = 1)
    i = d2.argmin()
    import Matrix as M
    tfinv = M.invert_matrix(tflist[i])
    rtflist = [M.multiply_matrices(tf, tfinv) for tf in tflist]
    rtflist[i] = M.identity_matrix()
    return rtflist

# -----------------------------------------------------------------------------
#
def undo_symmetry_copies_command(cmdname, args):

    from Commands import molecules_arg, parse_arguments
    req_args = ()
    opt_args = (('molecules', molecules_arg),)
    kw = parse_arguments(cmdname, args, req_args, opt_args)
    undo_symmetry_copies(**kw)
    
# -----------------------------------------------------------------------------
#
def undo_symmetry_copies(molecules = None):

    mlist = molecules
    if mlist is None:
        from chimera import openModels as om, Molecule
        mlist = om.list(modelTypes = [Molecule])

    mlist = [m for m in mlist if hasattr(m, 'symmetry_copies')]

    for mol in mlist:
        remove_symmetry_copies(mol)
    
# -----------------------------------------------------------------------------
#
def remove_symmetry_copies(mol):
        
    if not hasattr(mol, 'symmetry_copies'):
        from Commands import CommandError
        raise CommandError('Model %s does not have symmetry copies' % mol.name)

    remove_symmetry_update_handler(mol)

    import chimera
    chimera.openModels.close(mol.symmetry_copies)
    del mol.symmetry_copies
    del mol.symmetry_reference_openstate

# -----------------------------------------------------------------------------
#
def add_symmetry_update_handler(mol):

    import chimera
    h = chimera.triggers.addHandler('OpenState', motion_cb, mol)
    mol.symmetry_handler = h

# -----------------------------------------------------------------------------
#
def remove_symmetry_update_handler(mol):

    if hasattr(mol, 'symmetry_handler'):
        import chimera
        chimera.triggers.deleteHandler('OpenState', mol.symmetry_handler)
        del mol.symmetry_handler
    
# -----------------------------------------------------------------------------
#
def motion_cb(trigger_name, mol, trigger_data):

    if not 'transformation change' in trigger_data.reasons:
        return

    if is_model_deleted(mol) or mol.symmetry_reference_openstate.__destroyed__:
        remove_symmetry_update_handler(mol)
        return

    mos = mol.openState
    ros = mol.symmetry_reference_openstate

    modified = trigger_data.modified
    if not (mos in modified or ros in modified):
        return

    xf = ros.xform.inverse()
    xf.multiply(mos.xform)
    import Matrix
    if (hasattr(mol, 'last_relative_symmetry_xform') and
        Matrix.same_xform(xf, mol.last_relative_symmetry_xform, 0.1, 0.1)):
        return
    mol.last_relative_symmetry_xform = xf

    update_symmetry_positions(mol)

# -----------------------------------------------------------------------------
#
def create_symmetry_copies(mol, transforms, csys,
                           surfaces = False, resolution = None,
                           model_id = None):

    if hasattr(mol, 'symmetry_copies'):
        remove_symmetry_copies(mol)

    if surfaces:
        surfall = (surfaces == 'all')
        copies = [symmetry_surfaces(mol, transforms, csys, resolution,
                                    surfall, model_id)]
    elif len(transforms) == 0:
        return []

    else:
        from chimera import tasks, CancelOperation
        task = tasks.Task('Symmetry copies', modal = True)

        copies = []
        from Molecule import copy_molecule
        from MoleculeCopy import molecule_copy as copy_depiction
        from Matrix import chimera_xform
        try:
            for tf in transforms:
                copy = copy_molecule(mol)
                copy_depiction(mol.atoms, copy.atoms)
                copy.symmetry_xform = chimera_xform(tf)
                copies.append(copy)
                task.updateStatus('Created symmetry copy %d of %d'
                                  % (len(copies), len(transforms)))
        except CancelOperation:
            pass
        task.finished()

        from chimera import openModels as om
        id, subid = (om.Default,om.Default) if model_id is None else model_id
        om.add(copies, id, subid, noprefs = True)

    mol.symmetry_copies = copies
    mol.symmetry_reference_openstate = csys

    # TODO: Set xform before opening so that code that detects open sees
    # the correct position.  Currently not possible.  Bug 4486.
    if not surfaces:
        update_symmetry_positions(mol)

    return copies

# -----------------------------------------------------------------------------
#
def symmetry_surfaces(mol, transforms, csys, resolution, surfall, model_id):

    import Matrix as M
    tflist = [M.identity_matrix()] + list(transforms)
    if csys == mol.openState:
        mtflist = tflist
    else:
        # Map transforms from csys to mol coordinates.
        xf = csys.xform.inverse()
        xf.multiply(mol.openState.xform)
        mtflist = M.coordinate_transform_list(tflist, M.xform_matrix(xf))

    import MultiScale
    mm = MultiScale.multiscale_manager()
    m = mm.molecule_multimer(mol, mtflist, show = False)

    cplist = MultiScale.find_pieces([m], MultiScale.Chain_Piece)
    xflist = [M.chimera_xform(tf) for tf in tflist]
    for cp in cplist:
        cp.symmetry_xform = xflist[cp.xform.id_number - 1]

    surf = m.surface_model(model_id = model_id)
    surf.multiscale_model = m

    scplist = cplist if surfall else [cp for cp in cplist
                                      if not cp.lan_chain.is_loaded()]
    surf_params = (mm.default_surface_resolution
                   if resolution is None else resolution,
                   mm.default_density_threshold,
                   mm.default_density_threshold_ca_only,
                   mm.default_smoothing_factor,
                   mm.default_smoothing_iterations)
    mm.show_surfaces(scplist, surf_params)
    
    return surf

# -----------------------------------------------------------------------------
#
def filter_transforms(mol, tflist, csys, cdist, rdist, occupancy,
                      exclude_identity = True):

    if exclude_identity:
        from Matrix import is_identity_matrix
        tflist = [tf for tf in tflist if not is_identity_matrix(tf)]

    close_contacts = not cdist is None
    close_centers = not rdist is None
    if not close_contacts and not close_centers:
        transforms = tflist     # Use all transforms
    elif close_contacts and not close_centers:
        transforms = contacting_transforms(mol, csys, tflist, cdist)
    elif close_centers and not close_contacts:
        transforms = close_center_transforms(mol, csys, tflist, rdist)
    else:
        transforms = unique(contacting_transforms(mol, csys, tflist, cdist) +
                            close_center_transforms(mol, csys, tflist, rdist))

    from random import random
    if not occupancy is None:
        transforms = [tf for tf in transforms if random() <= occupancy]

    return transforms

# -----------------------------------------------------------------------------
#
def contacting_transforms(mol, csys, tflist, cdist):

    from _multiscale import get_atom_coordinates
    points = get_atom_coordinates(mol.atoms)
    pxf = mol.openState.xform
    pxf.premultiply(csys.xform.inverse())
    from Matrix import xform_matrix, identity_matrix
    from numpy import array, float32
    point_tf = xform_matrix(pxf)
    from _contour import affine_transform_vertices
    affine_transform_vertices(points, point_tf) # points in reference coords
    ident = array(identity_matrix(),float32)
    from _closepoints import find_close_points_sets, BOXES_METHOD
    ctflist = [tf for tf in tflist if
               len(find_close_points_sets(BOXES_METHOD,
                                          [(points, ident)],
                                          [(points, array(tf,float32))],
                                          cdist)[0][0]) > 0]
    return ctflist

# -----------------------------------------------------------------------------
#
def close_center_transforms(mol, csys, tflist, rdist):

    have_box, box = mol.bbox()
    if not have_box:
        return []
    c = mol.openState.xform.apply(box.center()) # center
    cref = csys.xform.inverse().apply(c).data() # reference coords
    from Matrix import distance, apply_matrix
    rtflist = [tf for tf in tflist
               if distance(cref, apply_matrix(tf, cref)) < rdist]
    return rtflist

# -----------------------------------------------------------------------------
#
def update_symmetry_positions(mol):

    mol_xf = mol.openState.xform
    ref_xf = mol.symmetry_reference_openstate.xform
    mol.symmetry_copies = [m for m in mol.symmetry_copies
                           if not is_model_deleted(m)]
                                 
    for m in mol.symmetry_copies:
        if hasattr(m, 'symmetry_xform'):
            m.openState.xform = symmetry_xform(mol_xf, m.symmetry_xform, ref_xf)
        elif hasattr(m, 'multiscale_model'):
            update_multiscale_positions(m.multiscale_model, mol_xf, ref_xf)

    if getattr(mol, 'sym_set_biomt', False):
        set_pdb_biomt_remarks(mol)

# -----------------------------------------------------------------------------
#
def update_multiscale_positions(mm, mol_xf, ref_xf):

    # Multiscale requires molecule and surface xform stay the same.
    surf = mm.surface_model()
    surf.openState.xform = mol_xf
    
    import MultiScale as MS
    cplist = MS.find_pieces([mm], MS.Chain_Piece)
    rxf = ref_xf.inverse()
    rxf.multiply(mol_xf)
    rxfinv = rxf.inverse()
    from chimera import Xform
    for cp in cplist:
        if hasattr(cp, 'symmetry_xform'):
            xf = Xform()
            xf.multiply(rxfinv)
            xf.multiply(cp.symmetry_xform)
            xf.multiply(rxf)
            cp.set_xform(xf)

# -----------------------------------------------------------------------------
#
def symmetry_xforms(mol, include_identity = True):

    from chimera import Xform
    xflist = [Xform()] if include_identity else []
    if not hasattr(mol, 'symmetry_copies'):
        return xflist
    if len(mol.symmetry_copies) == 1 and hasattr(mol.symmetry_copies[0], 'multiscale_model'):
        xflist = []

    for m in mol.symmetry_copies:
        if hasattr(m, 'symmetry_xform'):
            xflist.append(m.symmetry_xform)
        elif hasattr(m, 'multiscale_model'):
            import MultiScale as MS
            cplist = MS.find_pieces([m.multiscale_model], MS.Chain_Piece)
            found = set()
            for cp in cplist:
                if hasattr(cp, 'symmetry_xform'):
                    lm = cp.lan_chain.lan_molecule
                    if not lm in found:
                        # Keep only one transform per molecule copy.
                        found.add(lm)
                        xflist.append(cp.symmetry_xform)

    mol_xf = mol.openState.xform
    ref_xf = mol.symmetry_reference_openstate.xform
    import Matrix
    xflist = Matrix.coordinate_transform_xforms(xflist, ref_xf, mol_xf)
    
    return xflist    

# -----------------------------------------------------------------------------
#
def symmetry_xform(mol_xform, sym_xform, ref_xform):

    from chimera import Xform
    xf = Xform(mol_xform)
    xf.premultiply(ref_xform.inverse())
    xf.premultiply(sym_xform)
    xf.premultiply(ref_xform)
    return xf

# -----------------------------------------------------------------------------
#
def default_molecule():
        
    from chimera import openModels, Molecule
    mlist = openModels.list(modelTypes = [Molecule])
    mlist = [m for m in mlist if not hasattr(m, 'symmetry_xform')]
    if len(mlist) == 0:
        from Commands import CommandError
        raise CommandError('No molecules are opened')
    elif len(mlist) > 1:
        from Commands import CommandError
        raise CommandError('Multiple molecules opened, must specify one')
    mol = mlist[0]
    return mol
    
# -----------------------------------------------------------------------------
# Eliminate identical objects from list.
#
def unique(s):

    u = []
    found = {}
    for e in s:
        if not id(e) in found:
            found[id(e)] = True
            u.append(e)
    return u
    
# -----------------------------------------------------------------------------
#
def is_model_deleted(m):

    return m.__destroyed__
    
# -----------------------------------------------------------------------------
#
def set_volume_icosahedral_symmetry():

    from VolumeViewer import active_volume
    v = active_volume()
    if v is None:
        from chimera.replyobj import status
        status('Set icosahedral symmetry: No active volume data.')
        return

    from Icosahedron.gui import icosahedron_dialog
    d = icosahedron_dialog()
    if d is None:
        orientation = '222'
    else:
        orientation = d.orientation_name()

    from Icosahedron import icosahedral_symmetry_matrices
    v.data.symmetries = icosahedral_symmetry_matrices(orientation)

    from chimera.replyobj import status
    status('Set icosahedral symmetry %s of volume %s.' % (orientation, v.name))
