# -----------------------------------------------------------------------------
# Layout single strand RNA with specified base pairing.
#

# Series of stems and loops.
class Circuit:
    def __init__(self, stems_and_loops):
        self.stems_and_loops = stems_and_loops

    # -------------------------------------------------------------------------
    # Compute 3-d layout for circuit with stems and loops placed on a circle.
    # The layout leaves space for a stem at the bottom (negative y axis) of the
    # circle.
    #
    # The returned coordinates are a dictionary mapping residue number to a
    # transform (3 by 4 matrix) which takes (0,0,0) to the phosphor position
    # and the x-axis is in the direction of the base.
    #
    def layout(self, params, circle = True):

        # Compute stem and loop segment layouts.
        sl = self.stems_and_loops
        n = len(sl)
        segs = sum([e.layout(params, n) for e in sl], [])

        if circle:
            coords = self.circle_layout(segs, params)
        else:
            coords = self.straight_layout(segs, params)

        return coords

    def circle_layout(self, segs, params):

        coords = {}
        p = params

        # Compute circle radius
        wc = value_counts([w for c,w in segs if w > 0] + [p.pair_width])
        radius = polygon_radius(list(wc.items()) + [(p.loop_spacing, len(segs)+1)])

        # Layout loops and stems on a circle
        stem_angle_step = circle_angle(p.pair_width, radius)
        gap_step = circle_angle(p.loop_spacing, radius)
        angle = 0.5 * stem_angle_step + gap_step
        from math import pi, sin, cos
        a = 0.5*stem_angle_step*pi/180
        from random import random
        import Matrix as M
        stf = M.translation_matrix((radius*sin(a), -radius+radius*cos(a), 0))
        for scoords, seg_width in segs:
            angle_step = circle_angle(seg_width, radius)
            rtf = M.rotation_transform((0,0,1), 180 - 0.5*angle_step)
            if p.branch_tilt != 0:
                btf = M.rotation_transform((1,0,0), p.branch_tilt * (1-2*random()))
                rtf = M.multiply_matrices(rtf, btf)
            ptf = M.rotation_transform((0,0,1), -angle, center = (0,radius,0))
            ctf = M.multiply_matrices(stf, ptf, rtf)
            for b, tf in scoords.items():
                coords[b] = M.multiply_matrices(ctf, tf)
            # Next position along circle.
            angle += angle_step + gap_step

        return coords

    def straight_layout(self, segs, params):

        coords = {}
        s = 0
        import Matrix as M
        for i, (scoords, seg_width) in enumerate(segs):
            rtf = M.rotation_transform((1,0,0), params.branch_twist * i)
            stf = M.translation_matrix((s, 0, 0))
            ptf = M.multiply_matrices(stf, rtf)
            for b, tf in scoords.items():
                coords[b] = M.multiply_matrices(ptf, tf)
            # Next position along line
            s += seg_width + params.loop_spacing

        return coords

# Duplex RNA segment.
class Stem:
    def __init__(self, base5p, base3p, length, circuit):
        self.base5p = base5p
        self.base3p = base3p
        self.length = length
        self.circuit = circuit  # Circuit at far end of stem

    def layout(self, params, nseg):

        p = params
        coords = {}
        import Matrix as M
        rtf = M.rotation_transform((0,1,0), p.stem_twist,
                                   center = (0.5*p.pair_width,0,p.pair_off_axis))
        ttf = M.translation_matrix((0,p.pair_spacing,0))
        stf = M.multiply_matrices(ttf, rtf)
        tf1 = M.identity_matrix()
        tf2 = ((-1,0,0,p.pair_width),(0,-1,0,0),(0,0,1,0))
        for i in range(self.length):
            coords[self.base5p+i] = tf1
            coords[self.base3p-i] = tf2
            tf1 = M.multiply_matrices(stf, tf1)
            tf2 = M.multiply_matrices(stf, tf2)

        # Added circuit at end of stem.
        ccoords = self.circuit.layout(p)

        # Motion to end of stem assumes the stem end x-axis points
        # to base pair partner.
        stf = coords[self.base5p + self.length - 1]
        for b, tf in ccoords.items():
            coords[b] = M.multiply_matrices(stf, tf)

        return [(coords, p.pair_width)]

# Single strand RNA segment.
class Loop:
    def __init__(self, base5p, length):
        self.base5p = base5p
        self.length = length

    def layout(self, params, nseg):
        n = self.length
        b = self.base5p
        mls = params.min_lobe_size
        if n < mls:
            seg_width = 0
            segs = [({b + i: ((0,1,0,0),(-1,0,0,0),(0,0,1,0))}, seg_width)
                    for i in range(n)]
        else:
            # Lobe layout.
            mxs = params.max_lobe_size
            lsp = params.lobe_spacing if nseg > 1 else params.end_lobe_spacing()
            segs = [({b+i: ((0,1,0,0),(-1,0,0,0),(0,0,1,0))}, 0)
                    for i in range(lsp)]
            nl = n-lsp
            bl = b+lsp
            while nl >= mls+lsp:
                c = (nl+mxs+lsp-1) / (mxs+lsp)
                ls = nl/c - lsp
                if (ls - mls) % 2 == 1:
                    ls -= 1
                ns = (ls - mls) / 2
                segs.append(self.lobe_segment(ns, mls, params.loop_spacing, bl))
                ll = 2*ns + mls
                bl += ll
                nl -= ll
                for i in range(lsp):
                    segs.append(({bl+i:((0,1,0,0),(-1,0,0,0),(0,0,1,0))}, 0))
                bl += lsp
                nl -= lsp
            for i in range(nl):
                segs.append(({bl+i:((0,1,0,0),(-1,0,0,0),(0,0,1,0))}, 0))
        return segs

    def lobe_segment(self, ns, nc, ls, b):

        c = {}
        for i in range(ns):
            c[b+i] = ((1,0,0,0),(0,1,0,i*ls),(0,0,1,0))
        from math import pi, cos, sin
        r = 0.5*ls/sin(0.5*pi/(nc-1))
        for i in range(nc):
            a = i*pi/(nc-1)
            ca, sa = cos(a), sin(a)
            c[b+ns+i] = ((ca,sa,0,r*(1-ca)),(-sa,ca,0,r*sa+ns*ls),(0,0,1,0))
        for i in range(ns):
            c[b+ns+nc+i] = ((-1,0,0,2*r),(0,-1,0,(ns-1-i)*ls),(0,0,1,0))
        return (c, 2*r)

class Layout_Parameters:

    def __init__(self, loop_spacing = 7,
                 min_lobe_size = 8, max_lobe_size = 28, lobe_spacing = 0,
                 pair_spacing = 4, pair_width = 19, pair_off_axis = 2,
                 stem_twist = 36, branch_twist = 145, branch_tilt = 0):
        self.loop_spacing = loop_spacing
        self.min_lobe_size = min_lobe_size
        self.max_lobe_size = max_lobe_size
        self.lobe_spacing = lobe_spacing
        self.pair_spacing = pair_spacing
        self.pair_width = pair_width
        self.pair_off_axis = pair_off_axis
        self.stem_twist = stem_twist
        self.branch_twist = branch_twist
        self.branch_tilt = branch_tilt

    def end_lobe_spacing(self):

        from math import pi, ceil
        gap = pi*self.lobe_radius() - (self.pair_width + 2*self.loop_spacing)
        els = max(0, int(ceil(0.5*gap / self.loop_spacing)))
        return els

    def lobe_radius(self):
        from math import pi, sin
        r = 0.5*self.loop_spacing/sin(0.5*pi/(self.min_lobe_size-1))
        return r

# -----------------------------------------------------------------------------
# Create a Circuit object representing RNA topology from a list of 
# (start, end, length) base paired segments.
#
def circuit(pair_map, start, end):

    sl = []
    s = start
    while s <= end:
        if s in pair_map and pair_map[s] <= end:
            e = pair_map[s]
            l = 1
            while pair_map.get(s+l) == e-l:
                l += 1
            sl.append(Stem(s, e, l, circuit(pair_map, s+l, e-l)))
            s = e + 1
        else:
            l = 1
            while s+l not in pair_map and s+l <= end:
                l += 1
            sl.append(Loop(s,l))
            s += l
    c = Circuit(sl)
    return c

# -----------------------------------------------------------------------------
#
def polygon_radius(lnlist):

    from math import pi, asin
    l = sum(n*l for l,n in lnlist)
    r0 = l/(2*pi)
    r1 = l/2
    while r1-r0 > 1e-5 * l:
        rm = 0.5*(r0+r1)
        if sum(n*asin(min(1.0,l/(2*rm))) for l,n in lnlist) > pi:
            r0 = rm
        else:
            r1 = rm
    return rm

# -----------------------------------------------------------------------------
#
def circle_angle(side_length, radius):

    from math import asin, pi
    return 2*asin(min(1.0,0.5*side_length/radius)) * (180/pi)

# -----------------------------------------------------------------------------
#
def value_counts(values):

    vc = {}
    for v in values:
        if v in vc:
            vc[v] += 1
        else:
            vc[v] = 1
    return vc

# -----------------------------------------------------------------------------
# Base pair file is 3 integer columns start, end, length.  Each line indicates
# a base paired region of specified length with paired sequence positions
# (s,e), (s+1,e-1), ... (s+length-1,e-(length-1)).
#
# This is the format of the supplementary material from the Kevin Weeks
# HIV RNA secondary structure paper.
#
def read_base_pairs(path):

    f = open(path, 'r')
    lines = f.readlines()
    f.close()
    pairs = []
    for line in lines:
        s, e, l = [int(f) for f in line.split()]
        pairs.append((s,e,l))
    return pairs

# -----------------------------------------------------------------------------
# Detect whether base pairing forms a tree of branched stems and loops, or
# whether there are cycles.  The layout algorithm here only handles a tree.
# The Kevin Weeks HIV RNA secondary structure has no cycles.
#
def check_interleaves(pairs):

    for s,e,l in pairs:
        b = i = 0
        for s2,e2,l2 in pairs:
            b1 = (s2 > s and s2 < e)
            b2 = (e2 > s and e2 < e)
            if b1 and b2:
                b += 1
            elif (b1 and not b2) or (not b1 and b2):
                i += 1
        if i > 0:
            print '%5d %5d %3d %3d %3d' % (s,e,l,b,i)
        else:
            print '%5d %5d %3d %3d' % (s,e,l,b)

# -----------------------------------------------------------------------------
# Pairs is a list of triplets of residue positions p1, p2 and length where
# p1 is base paired with p2, p1+1 is base paired with p2-1, ..., and
# p1+len-1 is base paired with p2-(len-1).
#
# The returned pair map maps a base position to its paired position.
# Positions which are not paired do not appear in the map.
#
def pair_map(pairs):

    p = {}
    for s,e,l in pairs:
        for i in range(l):
            p[s+i] = e-i
            p[e-i] = s+i
    return p
    
# -----------------------------------------------------------------------------
#
def place_markers(coords, radius = 0.5, color = (.7,.7,.7,1), name = 'path',
                  pair_map = {}):

    from VolumePath import Marker_Set, Marker, Link
    mset = Marker_Set(name)

    # Create markers.
    mmap = {}
    btf = sorted(coords.items())
    for b, tf in btf:
        xyz = (tf[0][3], tf[1][3], tf[2][3])
        mmap[b] = m = Marker(mset, b, xyz, color, radius)
        m.extra_attributes = e = {'base_placement':tf}
        if b in pair_map:
            e['paired_with'] = pair_map[b]

    # Link consecutive markers.
    rl = 0.5*radius
    for b, tf in btf:
        if b+1 in mmap:
            Link(mmap[b], mmap[b+1], color, rl)

    # Link base pairs.
    for b1,b2 in pair_map.items():
        if b1 < b2 and b1 in mmap and b2 in mmap:
            Link(mmap[b1], mmap[b2], color, rl)
        
    return mset

# -----------------------------------------------------------------------------
# Adjust coordinate frame for each residue so y-axis points from one residue
# to next.  Have old x-axis lie in xy plane of new coordinate frame.
# Origin of frames is not changed.
#
def path_coordinates(coords):

    c = {}
    import Matrix as M
    for p, tf in coords.items():
        if p+1 in coords:
            tfn = coords[p+1]
            o = [tf[a][3] for a in (0,1,2)]
            y = [tfn[a][3] - o[a] for a in (0,1,2)]
            x = [tf[a][0] for a in (0,1,2)]
            za,xa,ya = M.orthonormal_frame(y, x)
            c[p] = ((xa[0],ya[0],za[0],o[0]),
                    (xa[1],ya[1],za[1],o[1]),
                    (xa[2],ya[2],za[2],o[2]))
    return c
    
# -----------------------------------------------------------------------------
#
def place_residues(coords, seq, residue_templates_molecule):

    res = dict((r.type, r) for r in residue_templates_molecule.residues)
    if 'U' in res:
        res['T'] = res['U']

    import chimera
    m = chimera.Molecule()
    m.name = 'RNA'
    n = len(seq)
    rlist = []
    for p, tf in sorted(coords.items()):
        if p <= n:
            t = seq[p-1]
            if t in res:
                rt = res[t]
                r = copy_residue(rt, p, tf, m)
                rlist.append(r)

    # Join consecutive residues
    rprev = rlist[0]
    for r in rlist[1:]:
        if r.id.position == 1 + rprev.id.position:
            a2 = r.findAtom('P')
            a1 = rprev.findAtom("O3'")
            if a1 and a2:
                m.newBond(a1,a2)
        rprev = r
                
    chimera.openModels.add([m])
    return m

# -----------------------------------------------------------------------------
#
def copy_residue(r, p, tf, m):

    import chimera
    cr = m.newResidue(r.type, chimera.MolResId(r.id.chainId, p))
    import Matrix
    xf = Matrix.chimera_xform(tf)
    amap = {}
    for a in r.atoms:
        amap[a] = ca = m.newAtom(a.name, a.element)
        ca.setCoord(xf.apply(a.coord()))
        cr.addAtom(ca)

    bonds = set(sum((a.bonds for a in r.atoms), []))
    for b in bonds:
        a1, a2 = b.atoms
        if a1 in amap and a2 in amap:
            m.newBond(amap[a1], amap[a2])
    return cr

# -----------------------------------------------------------------------------
#
def minimize_rna_backbone(mol,
                          chunk_size = 10,
                          gradient_steps = 100,
                          conjugate_gradient_steps = 100,
                          update_interval = 10,
                          nogui = True):

    base_atoms = ('N1,C2,N2,O2,N3,C4,N4,C5,C6,N6,O6,N7,C8,N9,'
                  'H1,H21,H22,H2,H41,H42,H5,H6,H61,H62,H8')
    ng = 'true' if nogui else 'false'
    opt = ('cache false nogui %s nsteps %d cgsteps %d interval %d'
           % (ng, gradient_steps, conjugate_gradient_steps, update_interval))
    prep = True

    # Find ranges of residues for each chain id.
    cr = {}
    for r in mol.residues:
        cid = r.id.chainId
        p = r.id.position
        pmin, pmax = cr.get(cid, (p,p))
        cr[cid] = (min(p,pmin), max(p,pmax))

    # Minimize backbone atoms in blocks of chunk_size residues.
    mid = mol.oslIdent()
    from chimera import runCommand
    for cid, (pmin, pmax) in cr.items():
        c = '' if cid.isspace() else '.' + cid
        for i in range(pmin, pmax, chunk_size):
            i1 = i-1 if i > pmin else i
            i2 = i + chunk_size
            if i2+1 == pmax:
                i2 = pmax       # Always minimize at least 2 nucleotides.
            prep = '' if prep is True else 'prep false'
            cmd = 'minimize spec %s:%d-%d%s fragment true freeze %s:%d%s:%d-%d%s@%s %s %s' % (mid, i1, i2, c, mid, i1, c, i, i2, c, base_atoms, prep, opt)
            print cmd
            runCommand(cmd)
            
# -----------------------------------------------------------------------------
# Rotate nucleotides in loops about x-axis by random amount.
#
def random_loop_orientations(coords, pmap, angle = 90, center = (0,0,0)):

    from random import random
    import Matrix as M
    for b, tf in tuple(coords.items()):
        if not b in pmap:
            a = (2*random()-1)*angle
            rx = M.rotation_transform((1,0,0), a, center)
            coords[b] = M.multiply_matrices(tf, rx)
            
# -----------------------------------------------------------------------------
#
def place_coordinate_frames(coords, radius):

    r = radius
    t = .2*r
    from VolumePath import Marker_Set, Marker, Link
    mset = Marker_Set('nucleotide orientations')
    for b, tf in coords.items():
        p0 = (tf[0][3],tf[1][3],tf[2][3])
        m0 = Marker(mset, 4*b, p0, (.5,.5,.5,1), t)
        p1 = (tf[0][3]+r*tf[0][0],tf[1][3]+r*tf[1][0],tf[2][3]+r*tf[2][0])
        m1 = Marker(mset, 4*b+1, p1, (1,.5,.5,1), t)
        Link(m0, m1, (1,.5,.5,1), t)
        p2 = (tf[0][3]+r*tf[0][1],tf[1][3]+r*tf[1][1],tf[2][3]+r*tf[2][1])
        m2 = Marker(mset, 4*b+2, p2, (.5,1,.5,1), t)
        Link(m0, m2, (.5,1,.5,1), t)
        p3 = (tf[0][3]+r*tf[0][2],tf[1][3]+r*tf[1][2],tf[2][3]+r*tf[2][2])
        m3 = Marker(mset, 4*b+3, p3, (.5,.5,1,1), t)
        Link(m0, m3, (.5,.5,1,1), t)
    return mset

# -----------------------------------------------------------------------------
#
def color_rna_path(markers, seq):

    colors = {'A': (1,.5,.5,1),
              'C': (1,1,.5,1),
              'G': (.5,1,.5,1),
              'T': (.5,.5,1,1),
              'U': (.5,.5,1,1),
              }
    n = len(seq)
    for m in markers:
        i = m.id - 1
        if i < n:
            color = colors.get(seq[i])
            if color:
                m.set_rgba(color)

# -----------------------------------------------------------------------------
#
def read_fasta(fasta_path):

    f = open(fasta_path, 'r')
    f.readline()        # header
    seq = f.read()
    f.close()
    seq = seq.replace('\n', '')
    return seq

# -----------------------------------------------------------------------------
#
def color_path_regions(markers, reg_path, seq_start):

    f = open(reg_path)
    lines = f.readlines()
    f.close()

    c3 = [line.split('\t')[:3] for line in lines]
    from chimera.colorTable import getColorByName
    regions = [(int(i1), int(i2), getColorByName(cname).rgba())
               for i1,i2,cname in c3]

    color = {}
    for i1,i2,rgba in regions:
        for i in range(i1,i2+1):
            color[i] = rgba

    for m in markers:
        i = seq_start + m.id - 1
        if i in color:
            m.set_rgba(color[i])
    
# -----------------------------------------------------------------------------
#
def rna_path(sequence_length, pair_map, circle = False, marker_radius = 2,
             random_branch_tilt = 0, name = 'rna layout'):

    # Compute layout.
    c = circuit(pair_map, 1, sequence_length)
    params = Layout_Parameters(
        loop_spacing = 5,   # Angstroms between consecutive nucleotides in loop.
        pair_width = 9, 
        pair_off_axis = 4,
        stem_twist = 36,    # Degrees twist from one base pair to next base pair
        branch_tilt = random_branch_tilt    # Random branch tilt range
        )
    coords = c.layout(params, circle = circle)
    #random_loop_orientations(coords, pair_map, 90, center = (0,8,0))

    # Place a marker at each nucleotide position.
    if name is None:
        return coords

    mset = place_markers(coords, radius = marker_radius, name = name,
                         pair_map = pair_map)

    # Place coordinate frames for debugging.
    #place_coordinate_frames(coords, marker_radius)

    return mset, coords

# -----------------------------------------------------------------------------
# Color loops and stems.
#
def color_path(markers, pair_map, loop_color, stem_color):

    for m in markers:
        m.set_rgba(stem_color if m.id in pair_map else loop_color)

# -----------------------------------------------------------------------------
#
def rna_atomic_model(sequence, base_placements, name = 'RNA',
                     nucleotide_templates = 'rna-templates.pdb'):

    # Place residues at each position to build an atomic model.
    templates = template_molecule('rna-templates.pdb')
    mol = place_residues(base_placements, sequence, templates)
    mol.name = name
    return mol

# -----------------------------------------------------------------------------
#
template_mol = {}
def template_molecule(nucleotide_templates):

    from os.path import join, dirname
    path = join(dirname(__file__), nucleotide_templates)

    global template_mol
    if path in template_mol:
        return template_mol[path]

    import chimera
    pdbio = chimera.PDBio()
    tmol = pdbio.readPDBfile(path)[0]
    template_mol[path] = tmol

    return tmol
    
# -----------------------------------------------------------------------------
#
def color_stems_and_loops(mol, pair_map, loopColor, stemColor):

    from chimera import MaterialColor
    scol, lcol = MaterialColor(*stemColor), MaterialColor(*loopColor)
    for a in mol.atoms:
        a.color = (scol if a.residue.id.position in pair_map else lcol)
    for r in mol.residues:
        r.ribbonColor = (scol if r.id.position in pair_map else lcol)
    
# -----------------------------------------------------------------------------
#
def make_hiv_rna():

    sequence_length = 9254
    
    # Read secondary structure.
    hivdir = '/usr/local/src/staff/goddard/presentations/hiv-rna-may2011'
    from os.path import join, dirname
    pairs_file = join(hivdir, 'pairings.txt')
    pairs = read_base_pairs(path)
    #check_interleaves(pairs)
    pmap = pair_map(pairs)
    print '%d stems involving %d nucleotides' % (len(pmap), len(pairs))

    sequence_file = join(hivdir, 'hiv-pNL4-3.fasta')
    sequence_start = 455
    
    mset, coords = rna_path(sequence_length, pmap,
                            circle = False,
#                            random_branch_tilt = 45,
                            )

    # Set placement matrices for use with sym command each 10 nucleotides.
    sym_spacing = 10
    mm = mset.marker_molecule()
    tfplace = [tf for b, tf in sorted(coords.items())[::sym_spacing]]
    mm.placements = lambda name,tfplace=tfplace: tfplace

    # Color nucleotides by type (A = red, C = yellow, G = green, T = U = blue).
    color_rna_path(mset.markers(), sequence)
    color_path(mset.markers(), pmap,
               loop_color = (.5,.5,.5,1), stem_color = (1,1,0,1))

    # Color segments listed in a text file.
    #regions_file = join(hivdir, 'regions.txt')
    #color_path_regions(mset.markers(), regions_file, sequence_start)

    # Read nucleotide sequence.
    seq = read_fasta(sequence_file)[sequence_start-1:]

    mol = rna_atomic_model(seq, coords)
    minimize_rna_backbone(mol)
