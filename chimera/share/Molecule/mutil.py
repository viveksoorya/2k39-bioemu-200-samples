# -----------------------------------------------------------------------------
# Molecule utility functions.
#
          
# -----------------------------------------------------------------------------
#
def atom_positions(atoms, xform = None):

    import _multiscale
    xyz = _multiscale.get_atom_coordinates(atoms, transformed = True)
    if xform:
        from Matrix import xform_matrix
        tf = xform_matrix(xform.inverse())
        from _contour import affine_transform_vertices
        affine_transform_vertices(xyz, tf)
    return xyz
  
# -----------------------------------------------------------------------------
# Move atoms in molecule coordinate system using a 3 by 4 matrix.
#
def transform_atom_positions(atoms, tf, from_atoms = None):

    if from_atoms is None:
        from_atoms = atoms
    import _multiscale
    xyz = _multiscale.get_atom_coordinates(from_atoms, transformed = False)
    from _contour import affine_transform_vertices
    affine_transform_vertices(xyz, tf)
    from chimera import Point
    for i,a in enumerate(atoms):
        a.setCoord(Point(*xyz[i]))

# -----------------------------------------------------------------------------
#
def atom_rgba(a):

    c = a.color
    if c is None:
        c = a.molecule.color
    return c.rgba()

# -----------------------------------------------------------------------------
#
def bond_rgba(b):

    c = b.color
    if c is None:
        c = b.molecule.color
    return c.rgba()
          
# -----------------------------------------------------------------------------
#
def interatom_bonds(atoms):

    bset = set()
    aset = set(atoms)
    for a in atoms:
        for b in a.bonds:
            if b.otherAtom(a) in aset:
                bset.add(b)
    bonds = list(bset)
    return bonds

# -----------------------------------------------------------------------------
#
def molecule_center(molecule):

  from _multiscale import get_atom_coordinates
  xyz = get_atom_coordinates(molecule.atoms)
  if len(xyz) == 0:
    return (0,0,0)
  c = tuple(xyz.mean(axis = 0))
  return c

# -----------------------------------------------------------------------------
# Return cell size and angles (a, b, c, alpha, beta, gamma, space_group, z).
# Angles are in radians.
#
def unit_cell_parameters(molecule):

    import PDBmatrices as pm
    if hasattr(molecule, 'pdbHeaders') and molecule.pdbHeaders:
        cp = pm.crystal_parameters(molecule.pdbHeaders)
    elif hasattr(molecule, 'mmCIFHeaders'):
        cp = pm.mmcif_unit_cell_parameters(molecule.mmCIFHeaders)
    elif hasattr(molecule, 'cifHeaders'):
        cp = pm.cif_unit_cell_parameters(molecule.cifHeaders)
    else:
        cp = None
    return cp

# -----------------------------------------------------------------------------
# To get all the transformations needed to build the unit cell, multiply all
# crystallographic symmetry matrices by all non-crystallographic symmetry
# matrices.
#
# The pack argument can be set to a pair of points
# (molecule-center, unit-cell-origin) and the unit cell transforms will be
# translated to put all molecule centers in the unit cell box.
#
def unit_cell_matrices(molecule, pack = None, group = False, cells = (1,1,1)):

    if tuple(cells) == (1,1,1):
        import PDBmatrices as pm
        if hasattr(molecule, 'pdbHeaders') and molecule.pdbHeaders:
            m = pm.pdb_unit_cell_matrices(molecule.pdbHeaders, pack, group)
        elif hasattr(molecule, 'mmCIFHeaders'):
            m = pm.mmcif_unit_cell_matrices(molecule.mmCIFHeaders, pack, group)
        elif hasattr(molecule, 'cifHeaders'):
            m = pm.cif_unit_cell_matrices(molecule.cifHeaders, pack, group)
        else:
            m = []
    else:
        cp = unit_cell_parameters(molecule)
        if cp is None:
            m = []
        else:
            import Crystal
            a, b, c, alpha, beta, gamma = cp[:6]
            cell_axes = Crystal.unit_cell_axes(a, b, c, alpha, beta, gamma)
            cranges = [(int(2-c)/2,int(c)/2)for c in cells]
            mlist = Crystal.translation_matrices(cell_axes, cranges)
            clist = unit_cell_matrices(molecule, pack = pack, group = group)
            m = Crystal.matrix_products(mlist, clist, group)
        
    return m

# -----------------------------------------------------------------------------
#
def crystal_symmetries(molecule, use_space_group_table = True):

    import PDBmatrices as pm
    if hasattr(molecule, 'pdbHeaders') and molecule.pdbHeaders:
        s = pm.pdb_smtry_matrices(molecule.pdbHeaders)
        # Handle crystal symmetry origin not equal to atom coordinate origin
        origin = pm.pdb_crystal_origin(molecule.pdbHeaders)
        if origin != (0,0,0):
            shift = [-x for x in origin]
            import Matrix as M
            s = M.coordinate_transform_list(s, M.translation_matrix(shift))
    elif hasattr(molecule, 'mmCIFHeaders'):
        s = pm.mmcif_crystal_symmetry_matrices(molecule.mmCIFHeaders)
    elif hasattr(molecule, 'cifHeaders'):
        s = pm.cif_crystal_symmetry_matrices(molecule.cifHeaders)
    else:
        s = []
    if len(s) == 0 and use_space_group_table:
        s = space_group_symmetries(molecule)
        
    return s

# -----------------------------------------------------------------------------
# In PDB files the SCALE1, SCALE2, SCALE3 remark records can indicate that
# the center of spacegroup symmetry is not 0,0,0 in atom coordinates.
# This is rare, seems to only to be older entries, for example, 1WAP.
# The PDB SMTRY remarks don't account for the different origin.
#
def crystal_symmetry_origin(molecule):
    import PDBmatrices as pm
    if hasattr(molecule, 'pdbHeaders') and molecule.pdbHeaders:
        origin = pm.pdb_crystal_origin(molecule.pdbHeaders)
    elif hasattr(molecule, 'mmCIFHeaders'):
        origin = pm.mmcif_crystal_origin(molecule.mmCIFHeaders)
    else:
        origin = (0,0,0)
    return origin

# -----------------------------------------------------------------------------
#
def noncrystal_symmetries(molecule, add_identity = True):

    import PDBmatrices as pm
    if hasattr(molecule, 'pdbHeaders') and molecule.pdbHeaders:
        s = pm.pdb_mtrix_matrices(molecule.pdbHeaders, add_identity = False)
    elif hasattr(molecule, 'mmCIFHeaders'):
        s = pm.mmcif_ncs_matrices(molecule.mmCIFHeaders, include_given = False)
    elif hasattr(molecule, 'cifHeaders'):
        s = pm.cif_ncs_matrices(molecule.cifHeaders)
    else:
        s = []
    if add_identity:
        import Matrix
        if not [m for m in s if Matrix.is_identity_matrix(m)]:
            s.append(Matrix.identity_matrix())

    return s


# -----------------------------------------------------------------------------
#
def biological_unit_matrices(molecule):

    import PDBmatrices as pm
    if hasattr(molecule, 'pdbHeaders') and molecule.pdbHeaders:
        s = pm.pdb_biomt_matrices(molecule.pdbHeaders)
    elif hasattr(molecule, 'mmCIFHeaders'):
        s = pm.mmcif_biounit_matrices(molecule.mmCIFHeaders)
    else:
        s = []
    return s

# -----------------------------------------------------------------------------
#
def space_group_symmetries(molecule):

    cp = unit_cell_parameters(molecule)
    if cp:
        a, b, c, alpha, beta, gamma, space_group, zvalue = cp
        import Crystal
        sgt = Crystal.space_group_matrices(space_group, a, b, c,
                                           alpha, beta, gamma)
    else:
        sgt = []
    return sgt
          
# -----------------------------------------------------------------------------
#
def select_next_residue(residues, backwards = False):
    rsel = []
    chains = set((r.molecule, r.id.chainId) for r in residues)
    for m,cid in chains:
        rchain = [r for r in residues if r.molecule == m and r.id.chainId == cid]
        for rc in rchain:
            rpos = rc.id.position
            if backwards:
                rbeyond = [r for r in m.residues if r.id.chainId == cid and r.id.position < rpos]
                rnext = max(rbeyond, key = lambda r: r.id.position) if rbeyond else rc
            else:
                rbeyond = [r for r in m.residues if r.id.chainId == cid and r.id.position > rpos]
                rnext = min(rbeyond, key = lambda r: r.id.position) if rbeyond else rc
            rsel.append(rnext)
    from chimera import selection, replyobj
    selection.clearCurrent()
    selection.addCurrent(rsel)
    replyobj.status('Selected %s' % ', '.join(r.oslIdent() for r in rsel))
          
# -----------------------------------------------------------------------------
#
def select_residue_interval(residues):
    rsel = []
    descrip = []
    chains = set((r.molecule, r.id.chainId) for r in residues)
    for m,cid in chains:
        rchain = [r.id.position for r in residues if r.molecule == m and r.id.chainId == cid]
        nmin, nmax = min(rchain), max(rchain)
        rbetween = [r for r in m.residues if r.id.position >= nmin and r.id.position <= nmax and r.id.chainId == cid]
        rsel.extend(rbetween)
        descrip.append('model %d, chain %s, residues %d-%d' % (m.id, cid, nmin, nmax))
    from chimera import selection, replyobj
    selection.clearCurrent()
    selection.addCurrent(rsel)
    replyobj.status('Selected %s' % ', '.join(descrip))
