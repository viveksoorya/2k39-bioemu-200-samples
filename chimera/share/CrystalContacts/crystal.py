from math import pi

# -----------------------------------------------------------------------------
# Non-crystallographic symmetry (NCS) asymmetric unit.
#
class NCS_Asymmetric_Unit:

    def __init__(self, ncs_index, smtry_index, unit_cell_index, transform):

        self.ncs_index = ncs_index
        self.smtry_index = smtry_index
        self.unit_cell_index = unit_cell_index
        self.transform = transform

# -----------------------------------------------------------------------------
# Symmetry matrices and crystal parameters from PDB header.
#
class Crystal:

    def __init__(self, molecule):

        import Molecule as m
        self.ncs_matrices = m.noncrystal_symmetries(molecule)
        self.smtry_matrices = m.crystal_symmetries(molecule)
        
        a, b, c, alpha, beta, gamma = m.unit_cell_parameters(molecule)[:6]
        from Crystal import unit_cell_axes
        self.axes = unit_cell_axes(a, b, c, alpha, beta, gamma)

        self.identity_smtry_index = identity_matrix_index(self.smtry_matrices)
        
    # -------------------------------------------------------------------------
    # Return transformation matrix for a specific asymmetric unit.
    #
    def transform(self, ncs_index, smtry_index, unit_cell_index):

        ncs = self.ncs_matrices[ncs_index]
        sym = self.smtry_matrices[smtry_index]
        from Matrix import multiply_matrices
        sym_ncs = multiply_matrices(sym, ncs)
        trans = unit_cell_translation(unit_cell_index, self.axes)
        trans_sym_ncs = translate_matrix(trans, sym_ncs)
        return trans_sym_ncs

# -----------------------------------------------------------------------------
# Create a ball and stick model where balls represent asymmetric units of
# a crystal structure and sticks connect clashing asymmetric units.  Or make
# copies of contacting asymmetric units.
#
def show_crystal_contacts(molecule, dist,
                          make_copies = False,
                          schematic = True,
                          residue_info = False,
                          buried_areas = False,
                          probe_radius = 1.4,
                          intra_biounit = True,
                          angle_tolerance = pi/1800,   # 0.1 degrees
                          shift_tolerance = 0.1,       # Angstroms
			  replace = False):

    from Molecule import unit_cell_parameters
    if (not hasattr(molecule, 'pdbHeaders') or
        unit_cell_parameters(molecule) is None):
        return None

    # Find all unique pairs of contacting asymmetric units.
    clist = report_crystal_contacts(molecule, dist,
                                    residue_info, buried_areas, probe_radius,
                                    intra_biounit,
                                    angle_tolerance, shift_tolerance)

    crystal = Crystal(molecule)

    # Incorrect matrices in PDB header may not be orthogonal.  Check.
    check_orthogonality(crystal.ncs_matrices, 'NCS', tolerance = 1e-3)
    check_orthogonality(crystal.smtry_matrices, 'SMTRY', tolerance = 1e-3)

    # Get list of clashing asymmetric units.
    asu_list = contacting_asymmetric_units(clist, crystal,
                                           include_000_unit_cell = True)

    cmodels = []
    
    # Place markers representing each asym unit.
    if schematic:
        marker_set = contact_marker_model(molecule, crystal, clist, asu_list)
        cmodels.append(marker_set.marker_model())

    if make_copies:
        # Make molecule copies.
	cm = make_asu_copies(molecule, contacting_asu(clist), crystal)
        cmodels.extend(cm)

    # Zoom to show all asym units.
    zoom_to_fit(padding = 0.05)

    # Remember contact models so they can be replaced if recalculated.
    if replace and hasattr(molecule, 'crystal_contact_models'):
        from chimera import openModels
        openModels.close(molecule.crystal_contact_models)
    molecule.crystal_contact_models = cmodels

    return cmodels

# -----------------------------------------------------------------------------
# From list of clashing pairs of asymmetric units determine list of
# asymmetric units to display.
#
def contacting_asymmetric_units(clist, crystal, include_000_unit_cell = False):

    t = {}
    for atoms1, atoms2, equiv_asu_pairs in clist:
        for a1, a2 in equiv_asu_pairs:
            t[(a2.smtry_index,a2.unit_cell_index)] = 1
    if include_000_unit_cell:
        for si in range(len(crystal.smtry_matrices)):
            t[(si,(0,0,0))] = 1
    
    ncs_count = len(crystal.ncs_matrices)
    asu_list = []
    for si, uci in t.keys():
        for ni in range(ncs_count):
            tf = crystal.transform(ni, si, uci)
            asu_list.append(NCS_Asymmetric_Unit(ni, si, uci, tf))
    
    return asu_list

# -----------------------------------------------------------------------------
#
def contact_marker_model(molecule, crystal, clist, asu_list):

    # Set marker and link colors and radii for clash depiction.
    xyz = atom_coordinates(molecule.atoms)
    asu_center = average_xyz(xyz)
    bbox = bounding_box(xyz)
    radius_ncs = .25*min(map(lambda a,b: a-b, bbox[1], bbox[0]))
    radius_copies = .8 * radius_ncs
    rgba_ncs = (.5, 1, .5, 1)   # NCS asym unit, light green
    rgba_uc = (.5, .8, .9, 1)   # Unit cell, light blue
    rgba_ouc = (.9, .9, .5, 1)  # Other unit cells, light yellow
    rgba_overlap = rgba_ncs[:3] + (.5,)
    link_rgba = (1, .5, .5, 1)
    link_radius = radius_copies
    uc_thickness = .4 * radius_ncs

    # Create markers and links depicting asym units and clashes.
    from VolumePath import Marker_Set
    marker_set = Marker_Set(molecule.name + ' crystal contacts')
    markers = create_asymmetric_unit_markers(marker_set, asu_list, asu_center,
                                             crystal.identity_smtry_index,
                                             rgba_ncs, rgba_uc, rgba_ouc,
                                             radius_ncs, radius_copies)
    n = len(molecule.atoms)
    links = create_clash_links(clist, n, link_radius, link_rgba, markers)

    # Make marker transparent when clashing asym unit are close.
    for l in links:
        if distance(l.marker1.xyz(), l.marker2.xyz()) < .5 * radius_ncs:
            l.marker1.set_rgba(rgba_overlap)

    create_unit_cell(marker_set, crystal.axes, rgba_uc, uc_thickness)

    return marker_set
    
# -----------------------------------------------------------------------------
# Create a sphere representing each asymmetric unit.  The sphere is created
# using the volume path tracer module.
#
def create_asymmetric_unit_markers(marker_set, asu_list, asu_center,
                                   identity_smtry_index,
                                   rgba_ncs, rgba_uc, rgba_ouc,
                                   radius_ncs, radius_copies):

    markers = {}
    from Matrix import apply_matrix
    for asu in asu_list:
        c = apply_matrix(asu.transform, asu_center)
        if asu.unit_cell_index != (0,0,0):
            color = rgba_ouc
            r = radius_copies
        elif asu.smtry_index == identity_smtry_index:
            color = rgba_ncs
            r = radius_ncs
        else:
            color = rgba_uc
            r = radius_copies
        m = marker_set.place_marker(c, color, r)
        m.atom.name = ('n%d s%d %d %d %d' %
                       ((asu.ncs_index, asu.smtry_index) + asu.unit_cell_index))
        markers[(asu.ncs_index, asu.smtry_index, asu.unit_cell_index)] = m

    return markers

# -----------------------------------------------------------------------------
# Create cylinders connecting spheres representing asymmetric unit that
# have close atomic contacts.  The cylinders are volume path tracer links.
#
def create_clash_links(clist, n, link_radius, link_rgba, markers):

    from VolumePath import Link
    links = []
    for atoms1, atoms2, equiv_asu_pairs in clist:
        rscale = 20*float(len(atoms1))/n
        if rscale > 1: rscale = 1
        elif rscale < .2: rscale = .2
        for a1,a2 in equiv_asu_pairs:
            m1 = markers[(a1.ncs_index, a1.smtry_index, a1.unit_cell_index)]
            m2 = markers[(a2.ncs_index, a2.smtry_index, a2.unit_cell_index)]
            l = Link(m1, m2, link_rgba, link_radius * rscale)
            links.append(l)
    return links

# -----------------------------------------------------------------------------
# Create markers and links outlining unit cell.
#
def create_unit_cell(marker_set, axes, color, thickness):

    r = 0.5 * thickness

    corner_indices = ((0,0,0), (0,0,1), (0,1,1), (0,1,0),
                      (1,0,0), (1,0,1), (1,1,1), (1,1,0))
    corners = map(lambda i: unit_cell_translation(i, axes), corner_indices)
    
    markers = []
    for c in corners:
        m = marker_set.place_marker(c, color, r)
        markers.append(m)

    edge_indices = ((0,1),(1,2),(2,3),(3,0),
                    (4,5),(5,6),(6,7),(7,4),
                    (0,4),(1,5),(2,6),(3,7))
    from VolumePath import Link
    for i,j in edge_indices:
        Link(markers[i], markers[j], color, r)

# -----------------------------------------------------------------------------
# Determine clashing asymmetric units and print a text list of clashing pairs
# having unique relative orientations.
#
def report_crystal_contacts(molecule, distance,
                            residue_info = False,
                            buried_areas = False,
                            probe_radius = 1.4,
                            intra_biounit = True,
                            angle_tolerance = pi/1800,   # 0.1 degrees
                            shift_tolerance = 0.1):      # Angstroms

    clist = asymmetric_unit_contacts(molecule, distance, intra_biounit,
                                     angle_tolerance, shift_tolerance)
    print ('%d pairs of NCS asymmetric units of %s contact at distance %.1f A' %
           (len(clist), molecule.name, distance))
    if clist:
        clist.sort(lambda c1, c2: cmp(len(c2[0]), len(c1[0])))
        print '  Atoms\t  MTRIX\t SMTRY\tUnit cell\tMTRIXref\t  Copies'
        for atoms1, atoms2, equiv_asu_pairs in clist:
            a1, a2 = equiv_asu_pairs[0]
            na = len(atoms1)
            n1 = a1.ncs_index
            n2, s2, uc2 = a2.ncs_index, a2.smtry_index, a2.unit_cell_index
            ne = len(equiv_asu_pairs)
            print ('%7d\t    %3d\t   %3d\t%2d %2d %2d \t   %3d\t %6d' %
                   (na, n2, s2, uc2[0], uc2[1], uc2[2], n1, ne))

        if residue_info:
            rc = residue_contacts(clist, distance)
            report_residue_contacts(rc)
        if buried_areas:
            if not residue_info:
                rc = residue_contacts(clist, distance)
            report_buried_areas(rc, probe_radius)

    from Accelerators.standard_accelerators import show_reply_log
    show_reply_log()

    return clist

# -----------------------------------------------------------------------------
#
def report_residue_contacts(rcontacts):

    print '\nResidue contacts, %d residues' % len(rcontacts)
    print '  residue1\t\tncs1\t  residue2\t\tncs2\tsym2\t  cell2\tdistance'
    for r1, asu1, r2list in rcontacts:
        r1name = '%s %d %s' % (r1.type, r1.id.position, r1.id.chainId)
        for r2,asu2,d in r2list:
            r2name = '%s %d %s' % (r2.type, r2.id.position, r2.id.chainId)
            uc2 = asu2.unit_cell_index
            print '%10s\t\t%3d\t%10s\t\t%3d\t%3d\t%2d %2d %2d\t  %.3g' % (r1name, asu1.ncs_index, r2name, asu2.ncs_index, asu2.smtry_index, uc2[0], uc2[1], uc2[2], d)

# -----------------------------------------------------------------------------
#
def report_buried_areas(rcontacts, probe_radius):

    areas = []
    for r1, asu1, r2list in rcontacts:
        a = buried_area(r1, asu1.transform,
                        [(r2, asu2.transform) for r2, asu2, d in r2list],
                        probe_radius)
        areas.append((r1, asu1, a))

    print '\nResidue buried areas, %d residues' % len(areas)
    print '  residue\t\tncs\t  buried'
    for r1, asu1, a in areas:
        r1name = '%s %d %s' % (r1.type, r1.id.position, r1.id.chainId)
        if a is None:
            print '%10s\t\t%3d\t calculation_failed' % (r1name, asu1.ncs_index)
        else:
            print '%10s\t\t%3d\t %.3g' % (r1name, asu1.ncs_index, a)
            r1.maxCrystalBuriedArea = max(a, getattr(r1,'maxCrystalBuriedArea',0))

# -----------------------------------------------------------------------------
#
def buried_area(r, tf, rlist, probeRadius = 1.4, vertexDensity = 2.0):

    xyzr12 = residue_xyzr([(r,tf)] + rlist)
    na = len(r.atoms)
    xyzr1 = xyzr12[:na]

    from MoleculeSurface import calcsurf, Surface_Calculation_Error
    try:
        s1 = calcsurf.run_mscalc(xyzr1, probeRadius, vertexDensity,
                                 fallback_to_single_component = False,
                                 report_stderr = False)
        s12 = calcsurf.run_mscalc(xyzr12, probeRadius, vertexDensity,
                                  fallback_to_single_component = False,
                                  report_stderr = False)
    except Surface_Calculation_Error:
        return None
    bsas = 0
    aareas1, aareas12 = s1[3], s12[3]
    for ai in range(na):
        bsas += aareas1[ai,1] - aareas12[ai,1]

    return bsas

# -----------------------------------------------------------------------------
#
def residue_xyzr(rtflist):

    from _contour import affine_transform_vertices
    n = sum([len(r.atoms) for r,tf in rtflist])
    from numpy import empty, float32
    xyzr = empty((n,4), float32)
    b = 0
    for r,tf in rtflist:
        for i,a in enumerate(r.atoms):
            xyzr[b+i,:] = a.coord().data() + (a.radius,)
        n = len(r.atoms)
        affine_transform_vertices(xyzr[b:b+n,:3], tf)
        b += n
    return xyzr

# -----------------------------------------------------------------------------
#
def residue_contacts(clist, distance):

    rclose = {}
    for atoms1, atoms2, equiv_asu_pairs in clist:
        asu1, asu2 = equiv_asu_pairs[0]
        apairs = close_atom_pairs(atoms1, asu1, atoms2, asu2, distance)
        rpairs = close_residue_pairs(apairs)
        for r1,r2,d in rpairs:
            if (r1,asu1) in rclose:
                rclose[(r1,asu1)].append((r2,asu2,d))
            else:
                rclose[(r1,asu1)] = [(r2,asu2,d)]
    rc = [(r1, asu1, r2list) for (r1,asu1), r2list in rclose.items()]
    rc.sort(lambda o1,o2: cmp((o1[0].id.chainId, o1[0].id.position),
                              (o2[0].id.chainId, o2[0].id.position)))
    return rc

# -----------------------------------------------------------------------------
#
def close_atom_pairs(atoms1, asu1, atoms2, asu2, distance):

    from _contour import affine_transform_vertices
    xyz1 = atom_coordinates(atoms1)
    affine_transform_vertices(xyz1, asu1.transform)
    xyz2 = atom_coordinates(atoms2)
    affine_transform_vertices(xyz2, asu2.transform)

    close = []
    import  numpy
    dist = numpy.zeros((len(atoms2),), numpy.float32)
    import _distances
    for i1, a1 in enumerate(atoms1):
        _distances.distances_from_origin(xyz2, xyz1[i1,:], dist)
        for i2, a2 in enumerate(atoms2):
            if dist[i2] <= distance:
                close.append((a1, a2, dist[i2]))

    return close

# -----------------------------------------------------------------------------
#
def close_residue_pairs(apairs):

    rdist = {}
    for a1, a2, dist in apairs:
        rp = (a1.residue, a2.residue)
        if rp in rdist:
            rdist[rp] = min(rdist[rp], dist)
        else:
            rdist[rp] = dist
    rpairs = [(rp[0], rp[1], d) for rp, d in rdist.items()]
    return rpairs

# -----------------------------------------------------------------------------
# Find the atoms of the asymmetric unit that make contacts with
# other asymmetric units anywhere in the crystal.
#
def crystal_contact_atoms(molecule, distance,
                          intra_biounit = True,
                          angle_tolerance = pi/1800,   # 0.1 degrees
                          shift_tolerance = 0.1):      # Angstroms

    clist = asymmetric_unit_contacts(molecule, distance, intra_biounit,
                                     angle_tolerance, shift_tolerance)
    catoms = set()
    for atoms1, atoms2, equiv_asu_pairs in clist:
        catoms.update(atoms1)
    alist = list(catoms)
    return alist

# -----------------------------------------------------------------------------
# Angle and shift tolerance values are used to eliminate equivalent pairs
# of asymmetric units. To find only contacts between different biological
# units (defined by PDB BIOMT matrices) use intra_biounit = False.
#
def asymmetric_unit_contacts(molecule, distance, intra_biounit,
                             angle_tolerance, shift_tolerance):

    plist = nearby_asymmetric_units(molecule, distance)
    if not intra_biounit:
        plist = interbiounit_asu_pairs(molecule, plist,
                                       angle_tolerance, shift_tolerance)
    uplist = unique_asymmetric_unit_pairs(plist, angle_tolerance,
                                          shift_tolerance)
    
    alist = molecule.atoms
    xyz = atom_coordinates(alist)

    catoms = []
    for equiv_asu_pairs in uplist:
        asu1, asu2 = equiv_asu_pairs[0]
        t1 = transform_as_numeric_array(asu1.transform)
        t2 = transform_as_numeric_array(asu2.transform)
        from _closepoints import find_close_points_sets, BOXES_METHOD
        i1, i2 = find_close_points_sets(BOXES_METHOD,
                                        [(xyz, t1)], [(xyz, t2)],
                                        distance)
        if len(i1[0]) > 0:
            atoms1 = [alist[i] for i in i1[0]]
            atoms2 = [alist[i] for i in i2[0]]
            catoms.append((atoms1, atoms2, equiv_asu_pairs))

    return catoms

# -----------------------------------------------------------------------------
# Find nearby asymmetric units in a crystal by looking for overlapping bounding
# boxes.  Contacts with each non-crystallographic symmetry (NCS) position
# are considered.  Returns a list of triples, the first item being the NCS
# matrix, the second being a another matrix for symmetry placing an asymmetric
# unit nearby, and the third being identifiers for these two matrices
# positions (NCS1, NCS2, SMTRY2, unitcell2).  The matrices are relative to
# the given molecule's local coordinates.
#
def nearby_asymmetric_units(molecule, distance):

    from Molecule import unit_cell_parameters
    if (not hasattr(molecule, 'pdbHeaders') or
        unit_cell_parameters(molecule) is None):
        return []

    xyz = atom_coordinates(molecule.atoms)
    bbox = bounding_box(xyz)
    pbox = pad_box(bbox, .5 *distance)

    crystal = Crystal(molecule)

    plist = nearby_boxes(pbox, crystal)
    
    return plist

# -----------------------------------------------------------------------------
# Filter out pairs of asymmetric units that are within the same biological unit
# defined by PDB BIOMT matrices.
#
def interbiounit_asu_pairs(molecule, plist, angle_tolerance, shift_tolerance):

    # Get biomt matrices.
    import Molecule
    biomt = Molecule.biological_unit_matrices(molecule)
    if len(biomt) <= 1:
        return plist

    # Make sure biomt matrices contain identity.
    # This finds all relative biomt transforms.  We assume they form a group
    # (in mathematical sense, closed under multiplication) otherwise it isn't
    # clear how the biounits are layed out in the crystal.
    # TODO: Check group assumption and warn if does not hold.
    from Matrix import is_identity_matrix, invert_matrix, multiply_matrices
    have_identity = False
    for tf in biomt:
        if is_identity_matrix(tf):
            have_identity = True
            break
    if not have_identity:
        tfinv = invert_matrix(biomt[0])
        biomt = [multiply_matrices(tfinv, tf) for tf in biomt]

    # Bin relative biomt matrices for fast approximate equality test.
    from bins import Binned_Transforms
    b = Binned_Transforms(angle_tolerance, shift_tolerance)
    for tf in biomt:
        b.add_transform(tf)

    # Filter out asu pairs that belong to same biological unit.
    ilist = []
    for asu1, asu2 in plist:
        rel = multiply_matrices(invert_matrix(asu1.transform), asu2.transform)
        if not b.close_transforms(rel):
            ilist.append((asu1, asu2))
    return ilist

# -----------------------------------------------------------------------------
# Group pairs of asymmetric units that have the same relative orientation
# together.
#
def unique_asymmetric_unit_pairs(plist, angle_tolerance, shift_tolerance):

    from bins import Binned_Transforms
    b = Binned_Transforms(angle_tolerance, shift_tolerance)

    from Matrix import invert_matrix, multiply_matrices
    
    uplist = []
    tf1_inverse_cache = {}
    equiv_asu_pairs = {}
    for asu1, asu2 in plist:
        tf1_index = asu1.ncs_index
        if tf1_index in tf1_inverse_cache:
            tf1_inv = tf1_inverse_cache[tf1_index]
        else:
            tf1_inv = invert_matrix(asu1.transform)
            tf1_inverse_cache[tf1_index] = tf1_inv
        rel = multiply_matrices(tf1_inv, asu2.transform)
        close = b.close_transforms(rel)
        if close:
            equiv_asu_pairs[close[0]].append((asu1, asu2))    # duplicate
        else:
            b.add_transform(rel)
            equiv_asu_pairs[rel] = [(asu1, asu2)]
            uplist.append(equiv_asu_pairs[rel])

    return uplist

# -----------------------------------------------------------------------------
# Apply crystal symmetry to given box and find all boxes that intersect any
# NCS symmetry of the given box.
#
def nearby_boxes(box, crystal):

    from Matrix import multiply_matrices, invert_matrix

    act = basis_coordinate_transform(crystal.axes)
    isi = crystal.identity_smtry_index

    box2_cache = {}
    
    plist = []
    for ncs1index, ncs1 in enumerate(crystal.ncs_matrices):
        ncs1_inv = invert_matrix(ncs1)
        box1 = transformed_bounding_box(box, multiply_matrices(act, ncs1))
        asu1 = NCS_Asymmetric_Unit(ncs1index, isi, (0,0,0), ncs1)
        for ncs2index, ncs2 in enumerate(crystal.ncs_matrices):
            for symindex, sym in enumerate(crystal.smtry_matrices):
                identity_sym = (symindex == isi)
                if (ncs2index, symindex) in box2_cache:
                    sym_ncs2, box2 = box2_cache[(ncs2index, symindex)]
                else:
                    sym_ncs2 = multiply_matrices(sym, ncs2)
                    box2_tf = multiply_matrices(act, sym_ncs2)
                    box2 = transformed_bounding_box(box, box2_tf)
                    box2_cache[(ncs2index, symindex)] = (sym_ncs2, box2)
                tlist = overlapping_translations(box1, box2, crystal.axes)
                for t, ucijk in tlist:
                    if (identity_sym and ucijk == (0,0,0) and
                        ncs1index >= ncs2index):
                        continue        # Include only 1 copy of pair
                    trans_sym_ncs2 = translate_matrix(t, sym_ncs2)
                    asu2 = NCS_Asymmetric_Unit(ncs2index, symindex, ucijk,
                                               trans_sym_ncs2)
                    plist.append((asu1, asu2))

    return plist

# -----------------------------------------------------------------------------
# Boxes are in crystal axes coordinates.
#
def overlapping_translations(box1, box2, axes):

    from math import ceil, floor
    tintervals = []
    for a in range(3):
        t0 = int(ceil(box1[0][a]-box2[1][a]))
        t1 = int(floor(box1[1][a]-box2[0][a]))
        if t0 > t1:
            return []
        tintervals.append(range(t0, t1+1))

    ar, br, cr = tintervals
    tlist = []
    for i in ar:
        for j in br:
            for k in cr:
                t = unit_cell_translation((i,j,k), axes)
                tlist.append((t,(i,j,k)))
    return tlist

# -----------------------------------------------------------------------------
# Transformation from xyz position to unit cell indices.
#
def basis_coordinate_transform(axes):

    from Matrix import invert_matrix
    bct = invert_matrix(((axes[0][0], axes[1][0], axes[2][0], 0),
                         (axes[0][1], axes[1][1], axes[2][1], 0),
                         (axes[0][2], axes[1][2], axes[2][2], 0)))
    return bct

# -----------------------------------------------------------------------------
# Translation vector for a unit cell with given indices.
#
def unit_cell_translation(ijk, axes):

    i,j,k = ijk
    t = (i*axes[0][0]+j*axes[1][0]+k*axes[2][0],
         i*axes[0][1]+j*axes[1][1]+k*axes[2][1],
         i*axes[0][2]+j*axes[1][2]+k*axes[2][2])
    return t

# ---------------------------------------------------------------------------
#
def zoom_to_fit(padding):

    import chimera
    have_bbox, bbox = chimera.openModels.bbox()
    if not have_bbox:
        return False

    z1 = bbox.llf.z
    z2 = bbox.urb.z             # z2 > z1
    zsize = z2 - z1
    xsize = bbox.urb.x - bbox.llf.x
    ysize = bbox.urb.y - bbox.llf.y

    import chimera
    v = chimera.viewer
    c = v.camera

    v.setViewSizeAndScaleFactor(.5 * (1.0 + 2*padding) * max(xsize, ysize), 1)
    v.clipping = False
    c.center = bbox.center().data()
    c.viewDistance = zsize

    return True
    
# -----------------------------------------------------------------------------
#
def atom_coordinates(atoms):

    from _multiscale import get_atom_coordinates
    xyz = get_atom_coordinates(atoms)
    return xyz

# -----------------------------------------------------------------------------
#
def average_xyz(xyz):

    from numpy import sum
    a = sum(xyz, axis=0) / len(xyz)
    return a

# -----------------------------------------------------------------------------
#
def bounding_box(xyz):

    from numpy import ndarray, single as floatc, array
    if type(xyz) != ndarray or xyz.dtype != floatc:
        xyz = array(xyz, floatc)

    import _multiscale
    xyz_min, xyz_max = _multiscale.bounding_box(xyz)
    return xyz_min, xyz_max
    
# -----------------------------------------------------------------------------
#
def box_center(box):

    c = map(lambda a,b: .5*(a+b), box[0], box[1])
    return c
    
# -----------------------------------------------------------------------------
#
def pad_box(box, padding):

    xyz_min = map(lambda x: x-padding, box[0])
    xyz_max = map(lambda x: x+padding, box[1])
    pbox = (xyz_min, xyz_max)
    return pbox
    
# -----------------------------------------------------------------------------
#
def transformed_bounding_box(box, tf):

    (x0,y0,z0), (x1,y1,z1) = box
    corners = ((x0,y0,z0), (x0,y0,z1), (x0,y1,z0), (x0,y1,z1),
               (x1,y0,z0), (x1,y0,z1), (x1,y1,z0), (x1,y1,z1))
    from Matrix import apply_matrix
    tf_corners = map(lambda c: apply_matrix(tf, c), corners)
    tf_box = bounding_box(tf_corners)
    return tf_box

# -----------------------------------------------------------------------------
#
def translate_matrix(t, m):

    m0, m1, m2 = m
    return ((m0[0], m0[1], m0[2], m0[3]+t[0]),
            (m1[0], m1[1], m1[2], m1[3]+t[1]),
            (m2[0], m2[1], m2[2], m2[3]+t[2]))
    
# -----------------------------------------------------------------------------
#
def transform_as_numeric_array(tf):

    from numpy import array, single as floatc
    a = array(tf, floatc)
    return a
    
# -----------------------------------------------------------------------------
#
def identity_matrix_index(matrices):

    from Matrix import is_identity_matrix
    for i in range(len(matrices)):
        if is_identity_matrix(matrices[i]):
            return i
    return None
    
# -----------------------------------------------------------------------------
#
def check_orthogonality(matrices, name, tolerance):

    from Matrix import transpose_matrix, multiply_matrices, is_identity_matrix
    for mindex, m in enumerate(matrices):
        mr = zero_translation(m)
        mrt = transpose_matrix(mr)
        p = multiply_matrices(mr, mrt)
        if not is_identity_matrix(p, tolerance):
            print ('%s matrix %d is not orthogonal, tolerance %.3g' %
                   (name, mindex, tolerance))
            print_matrix(m, '%10.5f')
            print '  matrix times transpose = '
            print_matrix(p, '%10.5f')

# -----------------------------------------------------------------------------
#
def print_matrix(m, format):

    lformat = ' '.join(['%10.5f']*4)
    for r in m:
        print lformat % tuple(r)
        
# -----------------------------------------------------------------------------
#
def zero_translation(m):

    return ((m[0][0], m[0][1], m[0][2], 0),
            (m[1][0], m[1][1], m[1][2], 0),
            (m[2][0], m[2][1], m[2][2], 0))
    
# -----------------------------------------------------------------------------
#
def distance(xyz1, xyz2):

    dx,dy,dz = map(lambda a,b: a-b, xyz1, xyz2)
    from math import sqrt
    d = sqrt(dx*dx + dy*dy + dz*dz)
    return d

# -----------------------------------------------------------------------------
#
def contacting_asu(clist):

    asu = {}
    for atoms1, atoms2, equiv_asu_pairs in clist:
        for a in equiv_asu_pairs[0]:
	    ai = (a.ncs_index, a.smtry_index, a.unit_cell_index)
	    if ai != (0,0,(0,0,0)):
	        asu[ai] = a
    return asu.values()

# -----------------------------------------------------------------------------
#
def make_asu_copies(m, asu_list, crystal):

    xflist = []
    names = []
    from Matrix import is_identity_matrix, chimera_xform
    for asu in asu_list:
        if is_identity_matrix(asu.transform):
            continue
        xflist.append(chimera_xform(asu.transform))
        name = '%s %s' % (m.name, '%d %d %d' % asu.unit_cell_index)
        if len(crystal.smtry_matrices) > 1:
            name += ' sym %d' % asu.smtry_index
        if len(crystal.ncs_matrices) > 1:
            name += ' ncs %d' % asu.ncs_index
        names.append(name)
    cmodels = make_molecule_copies(m, xflist, names)
    return cmodels

# -----------------------------------------------------------------------------
#
def make_molecule_copies(m, xflist, names):

    from chimera import openModels
    from Molecule import copy_molecule

    mclist = []
    for c, xf in enumerate(xflist):
        mc = copy_molecule(m)
        mclist.append(mc)
        mc.name = names[c]
        openModels.add([mc])
        mcxf = m.openState.xform
        mcxf.multiply(xf)
        mc.openState.xform = mcxf

    return mclist
