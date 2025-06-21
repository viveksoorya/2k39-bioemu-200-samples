# -----------------------------------------------------------------------------
#
polygon_colors = {
    3: (.5,1,0,1),
    4: (1,0,.5,1),
    5: (1,.5,0,1),
    6: (0,.5,1,1),
    7: (.5,0,1,1),
    }
polygon_names = {
    3: 'triangle',
    4: 'square',
    5: 'pentagon',
    6: 'hexagon',
    7: 'septagon',
    }

# -----------------------------------------------------------------------------
#
def attach_polygons(edges, n, edge_length = 1, edge_thickness = 0.2,
                    edge_inset = 0.1, color = None, vertex_degree = None):

    if edges == 'selected':
        edges = selected_edges()

    if color is None:
        global polygon_colors
        color = polygon_colors[n] if n in polygon_colors else (.7,.7,.7,1)
            
    from math import pi, sin
    radius = 0.5*edge_length / sin(pi/n)
    if len(edges) == 0:
        p = Polygon(n, radius, edge_thickness, edge_inset, color = color)
        polygons =  [p]
    else:
        polygons = []
        for e in edges:
            if joined_edge(e) is None:
                p = Polygon(n, radius, edge_thickness, edge_inset,
                            color = color, marker_set = e.marker1.marker_set)
                polygons.append(p)
                join_edges(p.edges[0], e, vertex_degree)
    select_polygons(polygons)
    return polygons

# -----------------------------------------------------------------------------
#
def select_polygons(polygons):
    
    ab = sum([[m.atom for m in p.vertices] + [l.bond for l in p.edges]
              for p in polygons], [])
    from chimera import selection
    selection.setCurrent(ab)

# -----------------------------------------------------------------------------
#
def ordered_link_markers(link):

    m0, m1 = link.marker1, link.marker2
    idiff = m0.id - m1.id
    if idiff == 1 or idiff < -1:
        m0, m1 = m1, m0
    return m0, m1
    
# -----------------------------------------------------------------------------
#
def ordered_vertex_edges(marker):

    links = marker.links()
    if len(links) != 2:
        return links
    l0, l1 = links
    if l0.marker2 is marker:
        return l0,l1
    return l1,l0
    
# -----------------------------------------------------------------------------
#
def connected_markers(m):

    mlist = [m]
    reached = set(mlist)
    i = 0
    while i < len(mlist):
        mi = mlist[i]
        for ml in mi.linked_markers():
            if not ml in reached:
                mlist.append(ml)
                reached.add(ml)
        i += 1
    return mlist

# -----------------------------------------------------------------------------
#
class Polygon:

    def __init__(self, n, radius = 1.0, edge_thickness = 0.2, inset = 0.1,
                 color = (.7,.7,.7,1), marker_set = None,
                 mlist = None, elist = None):

        if mlist is None or elist is None:
            if marker_set is None:
                msets = cage_marker_sets()
                if msets:
                    marker_set = msets[0]
                else:
                    from VolumePath import Marker_Set
                    marker_set = Marker_Set('Cage')
            mlist = []
            r = radius - inset
            edge_radius = 0.5*edge_thickness
            from math import pi, cos, sin
            for a in range(n):
                angle = a*2*pi/n
                p = (r*cos(angle), r*sin(angle), 0)
                m = marker_set.place_marker(p, color, edge_radius)
                mlist.append(m)

            from VolumePath import Link
            elist = [Link(m, mlist[(i+1)%n], color, edge_radius)
                     for i,m in enumerate(mlist)]
            
        self.n = n
        self.radius = radius
        self.thickness = edge_thickness
        self.inset = inset
        self.using_inset = True

        self.marker_set = mlist[0].marker_set
        self.vertices = mlist
        self.edges = elist
        for v in mlist:
            v.polygon = self
        for e in elist:
            e.polygon = self

        if mlist:
            # Register placement method so sym command can place molecule
            # copies on cage polygons.
            mset = self.marker_set
            mol = mset.marker_molecule()
            if not hasattr(mol, 'placements'):
                p = lambda name,mset=mset: placements(name, marker_set=mset)
                mol.placements = p

        if mlist:
            enable_session_save()

    # -------------------------------------------------------------------------
    #
    def center(self):

        return marker_center(self.vertices)

    # -------------------------------------------------------------------------
    #
    def normal(self):

        from numpy import array
        x0,x1,x2 = [array(m.xyz()) for m in self.vertices[:3]]
        import Matrix as M
        n = array(M.normalize_vector(M.cross_product(x1-x0, x2-x1)))
        return n
        
    # -------------------------------------------------------------------------
    #
    def edge_length(self):

        from math import pi, sin
        edge_length = 2*self.radius*sin(pi/self.n)
        return edge_length
        
    # -------------------------------------------------------------------------
    #
    def use_inset(self, use):

        use = bool(use)
        if self.using_inset == use:
            return

        self.using_inset = use
        self.reposition_vertices()

    # -------------------------------------------------------------------------
    #
    def reposition_vertices(self):

        r = self.radius
        ri = (r - self.inset) if self.using_inset else r
        c = self.center()
        from math import sqrt
        for m in self.vertices:
            d = m.xyz()-c
            f = ri/sqrt((d*d).sum())
            m.set_xyz(c + f*d)

    # -------------------------------------------------------------------------
    #
    def inset_scale(self):

        r = self.radius
        s = (r - self.inset) / r if self.using_inset else 1.0
        return s
        
    # -------------------------------------------------------------------------
    #
    def neighbor_polygons(self):

        plist = []
        reached = set([self])
        for l0 in self.edges:
            l1 = joined_edge(l0)
            if l1:
                pn = l1.polygon
                if not pn in reached:
                    reached.add(pn)
                    plist.append(pn)
        return plist

    # -------------------------------------------------------------------------
    # Marker position without inset.
    #
    def vertex_xyz(self, m):

        c = self.center()
        xyz = c + (m.xyz() - c)/self.inset_scale()
        return xyz
    
    # -------------------------------------------------------------------------
    #
    def resize(self, edge_length, edge_thickness, edge_inset):

        from math import pi, sin
        radius = 0.5*edge_length / sin(pi/self.n)
        if radius != self.radius or edge_inset != self.inset:
            self.radius = radius
            self.inset = edge_inset
            self.reposition_vertices()
            c = self.center()
            for m in self.vertices:
                xyz = c + (m.xyz() - c)/self.inset_scale()

        self.thickness = edge_thickness
        r = 0.5*edge_thickness
        for m in self.vertices:
            m.set_radius(r)
        for e in self.edges:
            e.set_radius(r)
        
    # -------------------------------------------------------------------------
    #
    def delete(self):

        elist = [joined_edge(e) for e in self.edges if joined_edge(e)]
        unjoin_edges(elist)
        for v in self.vertices:
            v.delete()

# -----------------------------------------------------------------------------
#
def marker_center(markers):

    from numpy import sum
    c = sum([m.xyz() for m in markers], axis=0) / len(markers)
    return c
        
# -----------------------------------------------------------------------------
#
def joined_edge(e):

    if hasattr(e, 'joined_edge'):
        if e.joined_edge.bond.__destroyed__:
            return None
        return e.joined_edge
    elif not hasattr(e, 'polygon'):
        restore_polygons(e.marker1.marker_set)
        if hasattr(e, 'joined_edge'):
            return e.joined_edge
    return None

# -----------------------------------------------------------------------------
# Used for restoring polygons and joined edges from saved marker sets.
#
def restore_polygons(marker_set):

    if getattr(marker_set, 'polygons_restored', False):
        return
    marker_set.polygons_restored = True

    # Recreate joined edges.
    idmap = dict([(m.id, m) for m in marker_set.markers()])
    for link in marker_set.links():
        if hasattr(link, 'extra_attributes'):
            ea = link.extra_attributes
            if 'join' in ea:
                id1, id2 = [int(i) for i in ea['join'].split()]
                if id1 in idmap and id2 in idmap:
                    m1 = idmap[id1]
                    m2 = idmap[id2]
                    ej = m1.linked_to(m2)
                    if ej:
                        link.joined_edge = ej
                    else:
                        del ea['join']
                else:
                    del ea['join']

    # Recreate polygons
    mcon = {}
    for link in marker_set.links():
        m1, m2 = link.marker1, link.marker2
        mc1 = mcon.get(m1, [m1])
        mc2 = mcon.get(m2, [m2])
        if mc1 is mc2:
            continue
        if len(mc2) > len(mc1):
            mc2.extend(mc1)
            for m in mc1:
                mcon[m] = mc2
            mcon[m2] = mc2
        else:
            mc1.extend(mc2)
            for m in mc2:
                mcon[m] = mc1
            mcon[m1] = mc1
    for mlist in mcon.values():
        n = len(mlist)
        mlist.sort(lambda m1, m2: cmp(m1.id, m2.id))
        elist = [m.linked_to(mlist[(i+1)%n]) for i,m in enumerate(mlist)]
        if not None in elist:
            Polygon(n, mlist = mlist, elist = elist)

    
# -----------------------------------------------------------------------------
#
def join_edges(l0 = None, l1 = None, vertex_degree = None):

    if l0 is None or l1 is None:
        links = selected_edges()
        if len(links) != 2:
            return False
        l0, l1 = links
        if l0.polygon is l1.polygon:
            return False

    join(l0, l1)
    join(l1, l0)

    optimize_placement(l0.polygon, vertex_degree)

    if not vertex_degree is None:
        # Join edges to achieve given vertex degree
        vertex_join_edges(l0.marker1, vertex_degree)
        vertex_join_edges(l0.marker2, vertex_degree)

    return True

# -----------------------------------------------------------------------------
#
def join(l0, l1):

    l0j = joined_edge(l0)
    if l0j:
        unjoin_edges([l0j])
    l0.joined_edge = l1
    if not hasattr(l0, 'extra_attributes'):
        l0.extra_attributes = {}
    l0.extra_attributes['join'] = '%d %d' % (l1.marker1.id, l1.marker2.id)
    l0.set_rgba(lighten_color(l0.rgba()))

# -----------------------------------------------------------------------------
# If degree polygons are joined around a vertex but one pair of edges is not
# joined, then join that pair of edges.
#
def vertex_join_edges(m, degree):

    llist = ordered_vertex_edges(m)
    if len(llist) != 2:
        return          # Broken polygon.
    l0, l1 = llist

    e1, d1 = vertex_next_unpaired_edge(l1, 1)
    e0, d0 = vertex_next_unpaired_edge(l0, -1)
    if e0 and e1 and 1 + d0 + d1 == degree:
        join_edges(e0, e1, degree)

# -----------------------------------------------------------------------------
#
def vertex_next_unpaired_edge(edge, direction):

    e = edge
    d = 0
    while True:
        ej = joined_edge(e)
        if ej is None:
            break
        en = next_polygon_edge(ej, direction)
        if en is edge or en is None:
            e = None   # Vertex surrounded by joined polygons or polygon broken
            break
        e = en
        d += 1
    return e, d

# -----------------------------------------------------------------------------
#
def next_polygon_edge(edge, direction):

    m0, m1 = ordered_link_markers(edge)
    
    s = set(m1.links() if direction == 1 else m0.links())
    s.remove(edge)
    if len(s) == 1:
        return s.pop()
    return None

# -----------------------------------------------------------------------------
#
def unjoin_edges(edges = None):

    if edges is None:
        edges = selected_edges()
    lset = set(edges)
    for link in lset:
        lj = joined_edge(link)
        if lj:
            delattr(lj, 'joined_edge')
            del lj.extra_attributes['join']
            lj.set_rgba(darken_color(lj.rgba()))
            delattr(link, 'joined_edge')
            del link.extra_attributes['join']
            link.set_rgba(darken_color(link.rgba()))

# -----------------------------------------------------------------------------
#
def delete_polygons(plist = None):

    if plist is None:
        plist = selected_polygons()
    for p in plist:
        p.delete()
        
# -----------------------------------------------------------------------------
#
def optimize_placement(polygon, vertex_degree):

    tf = optimized_placement(polygon, vertex_degree)
    import Molecule
    Molecule.transform_atom_positions([m.atom for m in polygon.vertices], tf)

# -----------------------------------------------------------------------------
#
def optimized_placement(polygon, vertex_degree):

    lpairs = []
    for l0 in polygon.edges:
        l0j = joined_edge(l0)
        if l0j:
            lpairs.append((l0,l0j))

    if len(lpairs) == 0:
        import Matrix
        tf = Matrix.identity_matrix()
    elif len(lpairs) == 1:
        l0,l1 = lpairs[0]
        tf = edge_join_transform(l0, l1, vertex_degree)
    else:
        xyz0 = []
        xyz1 = []
        for l0, l1 in lpairs:
            xyz0.extend(edge_alignment_points(l0))
            xyz1.extend(reversed(edge_alignment_points(l1)))
        from chimera import match
        xf, rms = match.matchPositions(xyz1, xyz0)
        import Matrix
        tf = Matrix.xform_matrix(xf)
    return tf

# -----------------------------------------------------------------------------
#
def edge_alignment_points(edge):

    p = edge.polygon
    c = p.center()
    s = 1.0/p.inset_scale()
    pts = [c + s*(m.xyz()-c) for m in ordered_link_markers(edge)]
    return pts

# -----------------------------------------------------------------------------
# Calculate transform aligning edge of one polygon with edge of another polygon.
# For hexagons put them in the same plane abutting each other.
# For pentagons make them non-coplanar so that optimization works without
# requiring symmetry breaking.
#
def edge_join_transform(link, rlink, vertex_degree):

    f0 = edge_coordinate_frame(rlink)
    f1 = edge_coordinate_frame(link)
    r = ((-1,0,0,0),
         (0,-1,0,0),
         (0,0,1,0))     # Rotate 180 degrees about z.

    if vertex_degree is None:
        ea = 0
    else:
        a = 180-360.0/link.polygon.n
        ra = 180-360.0/rlink.polygon.n
        ea = vertex_degree*(a + ra) - 720
    from Matrix import invert_matrix, multiply_matrices
    if ea != 0:
        from math import sin, cos, pi
        a = -pi/6 if ea < 0 else pi/6
        rx = ((1,0,0,0),
              (0,cos(a),sin(a),0),
              (0,-sin(a),cos(a),0))
        r = multiply_matrices(rx, r)
        
    tf = multiply_matrices(f0, r, invert_matrix(f1))
    
    return tf

# -----------------------------------------------------------------------------
# 3 by 4 matrix mapping x,y,z coordinates to center of edge with x along edge,
# and y directed away from center of the polygon, and z perpendicular to the
# plane of the polygon.
#
def edge_coordinate_frame(edge):

    x0, x1 = edge_alignment_points(edge)
    p = edge.polygon
    c = p.center()
    c01 = 0.5 * (x0+x1)
    from Matrix import cross_product, normalize_vector
    from numpy import subtract
    xa = normalize_vector(subtract(x1, x0))
    za = normalize_vector(cross_product(xa, c01-c))
    ya = cross_product(za, xa)
    tf = ((xa[0],ya[0],za[0],c01[0]),
          (xa[1],ya[1],za[1],c01[1]),
          (xa[2],ya[2],za[2],c01[2]))
    return tf

# -----------------------------------------------------------------------------
#
def optimize_shape(fixedpolys = set(), vertex_degree = None):

    links = selected_edges()
    if len(links) == 0:
        links = sum([mset.links() for mset in cage_marker_sets()], [])
    reached = set([link.polygon for link in links])
    plist = list(reached)
    i = 0
    while i < len(plist):
        p = plist[i]
        if not p in fixedpolys:
            optimize_placement(p, vertex_degree)
        for pn in p.neighbor_polygons():
            if not pn in reached:
                reached.add(pn)
                plist.append(pn)
        i += 1
    from chimera import replyobj
    replyobj.status('%s optimized' % polygon_counts(plist))
    
# -----------------------------------------------------------------------------
#
def polygon_counts(plist):

    c = {}
    for p in plist:
        c[p.n] = c.get(p.n,0) + 1
    pctext = ', '.join(['%d %s%s' % (cnt, polygon_names.get(n,'ngon'),
                                     's' if cnt > 1 else '')
                        for n, cnt in sorted(c.items())])
    if len(c) > 1:
        pctext += ', %d polygons' % len(plist)
    return pctext

# -----------------------------------------------------------------------------
#
def expand(polygons, distance):

    for p in polygons:
        d = distance * p.normal()
        for m in p.vertices:
            m.set_xyz(d + m.xyz())

# -----------------------------------------------------------------------------
#
def align_molecule():

    from chimera import selection
    atoms = selection.currentAtoms(ordered = True)
    mols = set([a.molecule for a in atoms])
    if len(mols) != 1:
        return
    mol = mols.pop()
    molxf = mol.openState.xform
    from Molecule import atom_positions
    axyz = atom_positions(atoms, molxf)
    from numpy import roll, float32, float64
    from Matrix import xform_matrix, xform_points
    from chimera.match import matchPositions
    xflist = []
    for mset in cage_marker_sets():
        for p in polygons(mset):
            if p.n == len(atoms):
                c = p.center()
                vxyz = [p.vertex_xyz(m) for m in p.vertices]
                exyz = (0.5*(vxyz + roll(vxyz, 1, axis = 0))).astype(float32)
                xform_points(exyz, mset.transform(), molxf)
                xf, rms = matchPositions(exyz.astype(float64),
                                         axyz.astype(float64))
                xflist.append(xf)

    molxf.multiply(xflist[0])
    mol.openState.xform = molxf

    import MultiScale
    mm = MultiScale.multiscale_manager()
    tflist = [xform_matrix(xf) for xf in xflist]
    mm.molecule_multimer(mol, tflist)

# -----------------------------------------------------------------------------
#
def polygons(mset):

    return set([m.polygon for m in mset.markers()])

# -----------------------------------------------------------------------------
#
def selected_edges():

    from VolumePath.markerset import selected_links
    links = selected_links()
    for mset in set([l.marker1.marker_set
                     for l in links if not hasattr(l, 'polygon')]):
        restore_polygons(mset)
    return [l for l in links if hasattr(l, 'polygon')]

# -----------------------------------------------------------------------------
#
def selected_vertices():

    from VolumePath.markerset import selected_markers
    markers = selected_markers()
    for mset in set([m.marker_set for m in markers
                     if not hasattr(m, 'polygon')]):
        restore_polygons(mset)
    return [m for m in markers if hasattr(m, 'polygon')]

# -----------------------------------------------------------------------------
#
def selected_polygons(full_cages = False, none_implies_all = False):

    plist = set([e.polygon for e in selected_edges() + selected_vertices()])
    if full_cages:
        cages = set([p.marker_set for p in plist])
        plist = sum([cage_polygons(c) for c in cages], [])
    if none_implies_all and len(plist) == 0:
        plist = sum([cage_polygons(c) for c in cage_marker_sets()], [])
    return plist

# -----------------------------------------------------------------------------
#
def cage_polygons(marker_set):

    plist = list(set([m.polygon for m in marker_set.markers()
                      if hasattr(m, 'polygon')]))
    return plist

# -----------------------------------------------------------------------------
#
def selected_cages():

    plist = selected_polygons()
    mslist = list(set([p.marker_set for p in plist if p.vertices]))
    return mslist

# -----------------------------------------------------------------------------
#
def cage_marker_sets():

    from VolumePath import marker_sets
    cmsets = [mset for mset in marker_sets() if mset.name == 'Cage']
    for mset in cmsets:
        mlist = mset.markers()
        if mlist and not hasattr(mlist[0], 'polygon'):
            restore_polygons(mset)
    return cmsets
    
# -----------------------------------------------------------------------------
#
def lighten_color(rgba):
    r,g,b,a = rgba
    return (r + 0.5*(1-r), g + 0.5*(1-g), b + 0.5*(1-b), a)
def darken_color(rgba):
    r,g,b,a = rgba
    return (max(0, r - (1-r)), max(0, g - (1-g)), max(0, b - (1-b)), a)

# -----------------------------------------------------------------------------
#
def toggle_inset():

    clist = selected_cages()
    if len(clist) == 0:
        clist = cage_marker_sets()
    for c in clist:
        for p in polygons(c):
            p.use_inset(not p.using_inset)

# -----------------------------------------------------------------------------
#
def use_inset(use = True):

    clist = selected_cages()
    if len(clist) == 0:
        clist = cage_marker_sets()
    for c in clist:
        for p in polygons(c):
            p.use_inset(use)

# -----------------------------------------------------------------------------
#
def scale(plist, f):

    mlist = sum([p.vertices for p in plist],[])
    c = marker_center(mlist)
    for p in plist:
        shift = (f-1.0)*(p.center() - c)
        for m in p.vertices:
            m.set_xyz(shift + m.xyz())
        p.resize(f*p.edge_length(), f*p.thickness, f*p.inset)
    
# -----------------------------------------------------------------------------
#
def make_mesh(color = (.7,.7,.7,1), edge_thickness = 0.4):

    clist = selected_cages()
    if len(clist) == 0:
        clist = cage_marker_sets()
    for c in clist:
        make_polygon_mesh(polygons(c), color, edge_thickness)

# -----------------------------------------------------------------------------
#
def make_polygon_mesh(plist, color, edge_thickness):

    # Find sets of joined vertices.
    mt = {}
    for p in plist:
        for e in p.edges:
            m0, m1 = ordered_link_markers(e)
            for m in (m0, m1):
                if not m in mt:
                    mt[m] = set([m])
            je = joined_edge(e)
            if je:
                jm1, jm0 = ordered_link_markers(je)
                mt[m0].add(jm0)
                mt[m1].add(jm1)

    # Create markers at average postions of joined markers.
    from VolumePath import Marker_Set, Link
    mset = Marker_Set('Mesh')
    mm = {}
    r = 0.5*edge_thickness
    from numpy import mean
    for m, mg in mt.items():
        if not m in mm:
            xyz = mean([me.polygon.vertex_xyz(me) for me in mg], axis=0)
            mc = mset.place_marker(xyz, color, r)
            for me in mg:
                mm[me] = mc

    # Create links between markers.
    et = {}
    for p in plist:
        for e in p.edges:
            m1, m2 = mm[e.marker1], mm[e.marker2]
            if not (m1,m2) in et:
                et[(m1,m2)] = et[(m2,m1)] = Link(m1, m2, color, r)

    return mset

# -----------------------------------------------------------------------------
# Return list of transforms from origin to each polygon standard reference
# frame for placing molecule copies on cage using sym command.
#
def placements(name, marker_set):

    if name.startswith('pn'):
        ns = name[2:]
        nfold = True
    elif name.startswith('p'):
        ns = name[1:]
        nfold = False
    else:
        return []

    try:
        n = int(ns)
    except:
        return []

    plist = polygons(marker_set)
    tflist = [polygon_coordinate_frame(p) for p in plist if p.n == n]

    if nfold:
        import Symmetry as S, Matrix as M
        tflist = M.matrix_products(tflist, S.cyclic_symmetry_matrices(n))

    return tflist

# -----------------------------------------------------------------------------
# Map (0,0,0) to polygon center, (0,0,1) to polygon normal and (1,0,0) to
# normalized axis from center to the first polygon marker.
#    
def polygon_coordinate_frame(polygon):

    p = polygon
    c = p.center()
    za = p.normal()
    xa = p.vertices[0].xyz() - c
    import Matrix as M
    ya = M.normalize_vector(M.cross_product(za, xa))
    xa = M.normalize_vector(M.cross_product(ya, za))
    tf = [(xa[a], ya[a], za[a], c[a]) for a in (0,1,2)]
    return tf

# -----------------------------------------------------------------------------
#
save_session_trigger = None
def enable_session_save():

  global save_session_trigger
  if save_session_trigger:
    return
  
  def save_session_cb(trigger, x, file):
    import session
    session.save_cage_state(file)

  from SimpleSession import SAVE_SESSION
  from chimera import triggers as t
  save_session_trigger = t.addHandler(SAVE_SESSION, save_session_cb, None)
