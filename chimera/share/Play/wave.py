# ------------------------------------------------------------------------------
# Move multiscale model chains from one configuration to another starting
# from specified chains and expanding out to nearest neighbors in waves.
#
def wave(model1, model2, distanceStep, pairChains = None, groupChains = None,
         equivalentChains = None, pairingMethod = 'match', frames = 25):

    # Find multiscale chain pieces.
    cp1list = multiscale_chains(model1)
    cp2list = multiscale_chains(model2)

    # Find chain groups.
    if groupChains is None:
        cids = set(cp.lan_chain.chain_id for cp in cp1list)
        gids = tuple((cid,) for cid in cids)
    else:
        cgps = groupChains.split(',')
        gids = tuple(tuple(sorted(cg.split('+'))) for cg in cgps)
    groups = chain_groups(cp1list, gids)

    # Compute wave layers.
    gstart = loaded_groups(groups)
    glayers, grest = chain_group_layers(gstart, groups, distanceStep)
    if grest:
        from Commands import CommandError
        raise CommandError('%d chain groups not reached' % (len(grest),))
        
    # Pair groups of chains in the two models
    cidmap = ({} if pairChains is None
              else dict(cp.split('=') for cp in pairChains.split(',')))
    if pairingMethod == 'match':
        # Pair the same transform numbers.
        cppairs = chain_pairs(cp1list, cp2list, cidmap)
        gpairs = group_pairs(groups, cppairs)
    elif pairingMethod in ('push', 'pull', 'pushpull'):
        eqgid = parse_equivalent_groups(equivalentChains)
        gpairs, glayers = close_pairs(glayers, groups, gids, cidmap, eqgid,
                                      cp2list, distanceStep, pairingMethod)
    else:
        from Commands import CommandError
        raise CommandError('unrecognized motion "%s"' % motion)

    # Compute chain group motions.
    check_atom_counts(gpairs)
    gxfc = dict((g1,chain_group_transform(g1, g2)) for g1,g2 in gpairs)

    # Find chain motion for each frame.
    fcp = chain_motion_frames(glayers, gxfc, frames)

    # Register motion update handler.
    args = [(cpxflist,) for cpxflist in fcp]
    import Play
    Play.call_for_n_frames(set_chain_piece_transforms, frames, args)

# -----------------------------------------------------------------------------
# Find multiscale model chain pieces.
#
def multiscale_chains(model):

    from Commands import CommandError
    import MultiScale as MS
    mm = MS.multiscale_manager(create = False)
    if mm is None:
        raise CommandEror('No multiscale models open')
    s2mm = dict((m.surf_model, m) for m in mm.models)
    if not model in s2mm:
        raise CommandError('Model %s is not a multiscale model'
                           % model.oslIdent())

    m = s2mm[model]
    cplist = MS.find_pieces([m], MS.Chain_Piece)
    return cplist

# -----------------------------------------------------------------------------
#
def chain_groups(cplist, gids = ()):

    gidmap = {}
    for cids in gids:
        for cid in cids:
            gidmap[cid] = cids

    glist = []
    gmap = {}
    for cp in cplist:
        lc = cp.lan_chain
        cid = lc.chain_id
        gid = (lc.lan_molecule, gidmap.get(cid, (cid,)))
        if gid in gmap:
            gmap[gid].append(cp)
        else:
            gc = [cp]
            glist.append(gc)
            gmap[gid] = gc

    for g in glist:
        g.sort(compare_chain_ids)
    glist = [tuple(g) for g in glist]

    return glist

# -----------------------------------------------------------------------------
#
def loaded_groups(groups):

    return [g for g in groups if is_group_loaded(g)]

# -----------------------------------------------------------------------------
#
def is_group_loaded(g):

    for cp in g:
        if cp.lan_chain.is_loaded():
            return True
    return False

# -----------------------------------------------------------------------------
#
def translate_group_ids(gids, cidmap):

    tgids = tuple(tuple(sorted(cidmap.get(cid,cid) for cid in gid))
                  for gid in gids)
    return tgids

# -----------------------------------------------------------------------------
#
def compare_chain_ids(cp1, cp2):

    return cmp(cp1.lan_chain.chain_id, cp2.lan_chain.chain_id)

# -----------------------------------------------------------------------------
#
def overlapping_layers(glayers, groups, distance):

    olayers = []
    orest = set(groups)
    cgmap = dict(sum((tuple((cp,g) for cp in g) for g in groups), ()))
    for glayer in glayers:
        olayer = contacting_groups(glayer, orest, distance, cgmap)
        olayers.append(olayer)
        orest.difference_update(olayer)
    return olayers, orest

# -----------------------------------------------------------------------------
#
def chain_group_layers(gstart, gall, distance):

    glayer = tuple(gstart)
    glayers = [glayer]
    grest = set(gall)
    grest.difference_update(glayer)
    cgmap = dict(sum((tuple((cp,g) for cp in g) for g in gall), ()))
    while grest:
        glayer = contacting_groups(glayer, grest, distance, cgmap)
        if glayer:
            glayers.append(glayer)
            grest.difference_update(glayer)
        else:
            break
    return glayers, grest
        
# -----------------------------------------------------------------------------
#
def contacting_groups(glayer, grest, distance, cgmap):

    from MultiScale import nearby as NR
    asets = NR.chain_atom_sets(sum(glayer,()))
    fsets = NR.chain_atom_sets(sum(grest,()))
    atoms1, chains1, atoms2, chains2 = \
        NR.atomic_contacts(asets, fsets, distance, load_atoms = False)
    glayer = tuple(set(cgmap[cp] for cp in chains2))
    return glayer
        
# -----------------------------------------------------------------------------
#
def close_pairs(glayers, groups, gids, cidmap, eqgid, cp2list, distance, motion):

    gmap = equivalent_groups_map(groups, gids, eqgid, cidmap, cp2list)
    gorder = sum(glayers, ())
    if motion == 'push':
        gpairs = closest_group_pairs(gorder, gmap)
    elif motion in ('pull', 'pushpull'):
        gids2 = translate_group_ids(gids, cidmap)
        groups2 = chain_groups(cp2list, gids2)
        if motion == 'pushpull':
            g2layers, g2rest = overlapping_layers(glayers, groups2, distance)
        else:
            gstart2 = loaded_groups(groups2)
            g2layers, g2rest = chain_group_layers(gstart2, groups2, distance)
        if g2rest:
            from Commands import CommandError
            raise CommandError("%d chain groups not reached" % (len(g2rest),))
        g2order = sum(g2layers, ())
        igmap = invert_group_map(gmap)
        if motion == 'pull':
            igpairs = closest_group_pairs(g2order, igmap)
            g2tog = dict(igpairs)
            glayers = tuple(tuple(g2tog[g] for g in gl) for gl in g2layers)
            gpairs = [(g,g2) for g2,g in igpairs]
        else:
            gpairs = sym_closest_group_pairs(glayers, gmap, g2layers, igmap)

    return gpairs, glayers

# -----------------------------------------------------------------------------
#
def closest_group_pairs(gorder, gmap):

    gpairs = []
    paired = set()
    for g in gorder:
        dg = ((group_distance(g,g2), g2) for g2 in gmap[g] if not g2 in paired)
        d, g2c = min(dg)
        paired.add(g2c)
        gpairs.append((g,g2c))
    return gpairs

# -----------------------------------------------------------------------------
#
def sym_closest_group_pairs(glayers, gmap, g2layers, g2map):

    gpairs = []
    paired = set()
    for glayer,g2layer in zip(glayers, g2layers):
        for g1 in glayer:
            if not g1 in paired:
                dg = ((group_distance(g1,g), g) for g in gmap[g1]
                      if not g in paired)
                d, g2c = min(dg)
                paired.add(g1)
                paired.add(g2c)
                gpairs.append((g1,g2c))
        for g2 in g2layer:
            if not g2 in paired:
                dg = ((group_distance(g,g2), g) for g in g2map[g2]
                      if not g in paired)
                d, g1c = min(dg)
                paired.add(g2)
                paired.add(g1c)
                gpairs.append((g1c,g2))
    return gpairs

# -----------------------------------------------------------------------------
#
def group_distance(g1, g2):

    d2sum = n = 0
    from Matrix import xform_points
    for cp1, cp2 in zip(g1,g2):
        xyz1 = cp1.lan_chain.source_atom_xyz().copy()
        xyz2 = cp2.lan_chain.source_atom_xyz().copy()
        xf1 = cp1.surface_model().openState.xform
        xf1.multiply(cp1.xform)
        xform_points(xyz1, xf1)
        xf2 = cp2.surface_model().openState.xform
        xf2.multiply(cp2.xform)
        xform_points(xyz2, xf2)
        dxyz = xyz2 - xyz1
        d2sum += (dxyz*dxyz).sum()
        n += len(dxyz)
    from math import sqrt
    d = sqrt(d2sum/n)
    return d
        
# -----------------------------------------------------------------------------
#
def chain_pairs(cp1list, cp2list, cidmap = {}):

    cp2dict = dict(((cp.xform.id_number, cp.lan_chain.chain_id), cp) 
                   for cp in cp2list)

    cppairs = []
    unpaired = []
    for cp in cp1list:
        cid = cp.lan_chain.chain_id
        cid2 = cidmap.get(cid, cid)
        c = (cp.xform.id_number, cid2)
        if c in cp2dict:
            cp2 = cp2dict[c]
            cppairs.append((cp,cp2))
        else:
            unpaired.append(cp)

    if unpaired:
        if len(cppairs) == 0:
            from Commands import CommandError
            raise CommandError('No chain ids match')
        else:
            warn_unpaired(unpaired)

    return cppairs

# -----------------------------------------------------------------------------
#
def group_pairs(groups, cppairs):

    cpmap = dict(cppairs)
    gpairs = tuple((g1, tuple(cpmap[cp] for cp in g1)) for g1 in groups)
    return gpairs

# -----------------------------------------------------------------------------
#
def warn_unpaired(unpaired):

    upc = {}
    for cp in unpaired:
        cid = cp.lan_chain.chain_id
        upc[cid] = upc.get(cid,0) + 1
    upcs = ', '.join('%s (%d)' % (cid, count) for cid, count in upc.items())
    msg = 'Some unpaired chains %s' % upcs
    from chimera.replyobj import status, info
    status(msg)
    info(msg + '\n')

# -----------------------------------------------------------------------------
#
def compare_subunit_number(cp1, cp2):

    return cmp((cp1.xform.id_number, cp1.lan_chain.chain_id),
               (cp2.xform.id_number, cp2.lan_chain.chain_id))

# -----------------------------------------------------------------------------
#
def equivalent_groups_map(groups, gids, eqgid, cidmap, cp2list):

    gids2 = translate_group_ids(gids, cidmap)
    groups2 = chain_groups(cp2list, gids2)
    gid2map = equivalent_group_id_map(eqgid, cidmap)
    eqg2 = equivalent_groups(groups2, gid2map)
    gid2eqg = dict((gid,eqg2[gid2]) for gid, gid2 in zip(gids,gids2))
    gmap = dict((g, gid2eqg[group_id(g)]) for g in groups)
    return gmap

# -----------------------------------------------------------------------------
#
def equivalent_groups(groups, equiv):

    gmap = {}
    for g in groups:
        gid = tuple(sorted(cp.lan_chain.chain_id for cp in g))
        egid = equiv.get(gid, gid)
        if egid in gmap:
            gmap[egid].append(g)
        else:
            gmap[egid] = [g]
        if not gid in gmap:
            gmap[gid] = gmap[egid]
    return gmap

# -----------------------------------------------------------------------------
#
def parse_equivalent_groups(equiv_groups):

    if equiv_groups is None:
        equiv = {}
    else:
        equiv = tuple(tuple(tuple(sorted(g.split('+'))) for g in eg.split('='))
                      for eg in equiv_groups.split(','))
    return equiv

# -----------------------------------------------------------------------------
#
def equivalent_group_id_map(eqgids, cidmap):

    eqmap = {}
    for eqgid in eqgids:
        egm = [tuple(sorted(cidmap.get(cid,cid) for cid in gid))
               for gid in eqgid]
        for eg2 in egm:
            eqmap[eg2] = egm[0]
    return eqmap

# -----------------------------------------------------------------------------
#
def invert_group_map(gmap):

    igmap = {}
    for g, eqg2 in gmap.items():
        for g2 in eqg2:
            if g2 in igmap:
                igmap[g2].append(g)
            else:
                igmap[g2] = [g]
    return igmap

# -----------------------------------------------------------------------------
#
def group_id(g):

    return tuple(cp.lan_chain.chain_id for cp in g)

# -----------------------------------------------------------------------------
#
def check_atom_counts(gpairs):

    for g1, g2 in gpairs:
        for cp1, cp2 in zip(g1, g2):
            n1 = len(cp1.lan_chain.source_atom_xyz())
            n2 = len(cp2.lan_chain.source_atom_xyz())
            if n1 != n2:
                from Commands import CommandError
                raise CommandError('Paired chains have different number'
                                   ' of atoms (%s %d, %s %d)'
                                   % (cp1.surface_piece.oslIdent(), n1,
                                      cp2.surface_piece.oslIdent(), n2))
            
# -----------------------------------------------------------------------------
# Compute transform aligning one group of chains to another.
# Transform maps local coordinates of model g1 to local coordinates of model g1.
#
def chain_group_transform(g1, g2):

    xyz1 = group_atoms_xyz(g1)
    xyz2 = group_atoms_xyz(g2)
    from numpy import float64   # Required by matchPoints()
    from chimera import match
    xf, rms = match.matchPositions(xyz2.astype(float64), xyz1.astype(float64))
    center = xyz1.mean(axis = 0)
    xf1 = g1[0].surface_model().openState.xform
    xf2 = g2[0].surface_model().openState.xform
    xf.premultiply(xf2)
    xf.premultiply(xf1.inverse())
    return xf, center

# -----------------------------------------------------------------------------
# Atom coordinates returned in one array in local model coordinate system.
# All chains are assumed to belong to the same model.
#
def group_atoms_xyz(g):

    n = sum(len(cp.lan_chain.source_atom_xyz()) for cp in g)
    from numpy import empty, float32
    xyz = empty((n,3), float32)
    s = 0
    import Matrix
    for cp in g:
        sxyz = cp.lan_chain.source_atom_xyz()
        m = len(sxyz)
        xyz[s:s+m,:] = sxyz
        Matrix.xform_points(xyz[s:s+m,:], cp.xform)
        s += m
    return xyz

# -----------------------------------------------------------------------------
#
def chain_motion_frames(glayers, gxfc, frames):

    from chimera import Xform
    fcpxf = [[] for i in range(frames)]
    nlayer = len(glayers)
    for l, glayer in enumerate(glayers):
        fstart = int(frames*float(l)/nlayer)
        fend = min(frames-1,int(frames*float(l+1)/nlayer))
        for g in glayer:
            xf, center = gxfc[g]
            for f in range(fstart, fend+1):
                frac = float(f-fstart+1)/(fend-fstart+1)
                fxf = fractional_transform(xf, center, frac)
                for cp in g:
                    cfxf = Xform(cp.xform)
                    cfxf.premultiply(fxf)
                    fcpxf[f].append((cp,cfxf))
    return fcpxf

# -----------------------------------------------------------------------------
#
def fractional_transform(xf, center, frac):

    from chimera import Point, Xform
    c = Point(*center)
    xfc = xf.apply(c)
    fc = c + frac*(xfc - c)

    fxf = Xform.translation(Point()-c)
    axis, angle = xf.getRotation()
    fr = Xform.rotation(axis, angle * frac)
    fxf.premultiply(fr)
    fxf.premultiply(Xform.translation(fc-Point()))

    return fxf

# -----------------------------------------------------------------------------
#
def set_chain_piece_transforms(cpxflist):

    from chimera import Xform
    for cp, xf in cpxflist:
        cp.set_xform(xf)
