# -----------------------------------------------------------------------------
# rna command implementation.
#
def rna_command(cmdname, args):

    from Commands import perform_operation, string_arg
    from Commands import bool_arg, float_arg, int_arg, color_arg
    from Commands import atoms_arg, molecule_arg

    ops = {
        'path': (path_op,
                (('pairs', string_arg),),
                (('length', int_arg),),
                (('circle', bool_arg),
                 ('radius', float_arg),
                 ('randomBranchTilt', float_arg),
                 ('loopColor', color_arg),
                 ('stemColor', color_arg),
                 ('name', string_arg))),
        'model': (model_op,
                  (('sequence', string_arg),),
                  (('path', atoms_arg),),
                  (('startSequence', int_arg),
                   ('length', int_arg),
                   ('pairs', string_arg),
                   ('circle', bool_arg),
                   ('randomBranchTilt', float_arg),
                   ('loopColor', color_arg),
                   ('stemColor', color_arg),
                   ('name', string_arg))),
        'minimizeBackbone': (minimize_backbone_op,
                             (('molecule', molecule_arg),),
                             (),
                             (('chunkSize', int_arg),
                              ('steps', int_arg),
                              ('conjugateGradientSteps', int_arg),
                              ('updateInterval', int_arg),
                              ('nogui', bool_arg))),
        'smoothPath': (smooth_path_op,
                       (('path', atoms_arg),),
                       (('radius', float_arg),
                        ('spacing', float_arg)),
                       (('kinkInterval', int_arg),
                        ('kinkRadius', float_arg),
                        ('name', string_arg))),
        'duplex': (duplex_op,
                   (('path', atoms_arg),
                    ('sequence', string_arg)),
                   (),
                   (('startSequence', int_arg),
                    ('type', string_arg))),
        }

    perform_operation(cmdname, args, ops)

# -----------------------------------------------------------------------------
#
def path_op(pairs, length = None,
            circle = False, radius = 2, randomBranchTilt = 0,
            loopColor = (.4,.6,.9,1), stemColor = (1,1,0,1),
            name = 'RNA path'):

    plist = parse_pairs(pairs)
    import rna_layout as RL
    pair_map = RL.pair_map(plist)
    if length is None:
        length = max(pair_map.keys())
    mset, coords = RL.rna_path(length, pair_map,
                               circle = circle,
                               marker_radius = radius,
                               random_branch_tilt = randomBranchTilt,
                               name = name)
    RL.color_path(mset.markers(), pair_map, loopColor, stemColor)
    return mset, coords

# -----------------------------------------------------------------------------
#
def parse_pairs(pairs):

    import os.path
    if os.path.exists(pairs):
        import rna_layout as RL
        plist = RL.read_base_pairs(pairs)
        return plist

    plist = parse_pairs_string(pairs)
    if plist is None:
        from Commands import CommandError
        raise CommandError('Pairs must be a file or start,end,length '
                           'triples, got "%s"' % pairs)
    return plist

# -----------------------------------------------------------------------------
# Can specify base pairs as comma separate list of start,end,length triples.
#
def parse_pairs_string(pairs):

    try:
        p = [int(i) for i in pairs.split(',')]
    except ValueError:
        return None
    if len(p) < 3 or len(p) % 3 != 0:
        return None
    p3 = zip(p[::3], p[1::3], p[2::3])
    return p3

# -----------------------------------------------------------------------------
#
def model_op(sequence, path = None, startSequence = 1,
             length = None, pairs = None,
             circle = False, randomBranchTilt = 0,
             loopColor = (.4,.6,.9,1), stemColor = (1,1,0,1),
             name = 'RNA'):

    import rna_layout as RL
    import os.path
    seq = RL.read_fasta(sequence) if os.path.exists(sequence) else sequence
    seq = seq[startSequence-1:]

    if path is None:
        if pairs is None:
            from Commands import CommandError
            raise CommandError('Must specify either a path or base pairing')
        if length is None:
            length = len(seq)
        plist = parse_pairs(pairs)
        import rna_layout as RL
        pair_map = RL.pair_map(plist)
        base_placements = RL.rna_path(length, pair_map,
                                      circle = circle,
                                      random_branch_tilt = randomBranchTilt,
                                      name = None)
    else:
        mpath = [m for m in atoms_to_markers(path)
                 if hasattr(m, 'extra_attributes')
                 and 'base_placement' in m.extra_attributes]
        base_placements = dict((m.id, m.extra_attributes['base_placement'])
                               for m in mpath)
        pair_map = dict((m.id, m.extra_attributes['paired_with'])
                        for m in mpath if 'paired_with' in m.extra_attributes)

    mol = RL.rna_atomic_model(seq, base_placements, name)
    RL.color_stems_and_loops(mol, pair_map, loopColor, stemColor)

    return mol

# -----------------------------------------------------------------------------
#
def atoms_to_markers(atoms):

    a2m = {}
    import VolumePath as VP
    for mset in VP.marker_sets():
        a2m.update(mset.atom_to_marker)
    markers = [a2m[a] for a in atoms if a in a2m]
    return markers

# -----------------------------------------------------------------------------
#
def minimize_backbone_op(molecule, chunkSize = 10, steps = 100,
                         conjugateGradientSteps = 100, updateInterval = 10,
                         nogui = True):

    import rna_layout as RL
    RL.minimize_rna_backbone(molecule, chunkSize, steps,
                             conjugateGradientSteps, updateInterval, nogui)

# -----------------------------------------------------------------------------
#
def smooth_path_op(path, radius = 50, spacing = 3.33,
                   kinkInterval = None, kinkRadius = None,
                   name = 'smooth path'):

    markers = atoms_to_markers(path)

    import duplex
    mset = duplex.smooth_path(markers, radius, spacing,
                              kinkInterval, kinkRadius, name)
    return mset

# -----------------------------------------------------------------------------
#
def duplex_op(path, sequence, startSequence = 1, type = 'DNA'):

    from numpy import array
    path_xyz = array([atom.coord().data() for atom in path])

    import os.path
    import rna_layout as RL
    seq = RL.read_fasta(sequence) if os.path.exists(sequence) else sequence
    seq = seq[startSequence-1:]

    import duplex
    mol = duplex.make_dna_following_path(path_xyz, seq, polymer_type = type)

    return mol
