# -----------------------------------------------------------------------------
# Read in an Collada file and create a surface.
# 
def read_collada(path, color = (0.7,0.7,0.7,1)):

    from _surface import SurfaceModel
    s = SurfaceModel()
    from os.path import basename
    s.name = basename(path)

    from collada import Collada
    c = Collada(path)
    from Matrix import identity_matrix
    splist = surface_pieces_from_nodes(c.scene.nodes, s, color, identity_matrix(), {})
    create_surface_piece_instances(splist)

    ai = c.assetInfo
    if ai:
        s.collada_unit_name = ai.unitname
        s.collada_contributors = ai.contributors

    return s

def surface_pieces_from_nodes(nodes, surf, color, place, ginst):

    splist = []
    from collada.scene import GeometryNode, Node
    from Matrix import multiply_matrices
    for n in nodes:
        if isinstance(n, GeometryNode):
            materials = dict((m.symbol,m.target) for m in n.materials)
            g = n.geometry
            colors = g.sourceById
            if g.id in ginst:
                add_geometry_instance(g.primitives, ginst[g.id], place, color, materials)
            else:
                ginst[g.id] = spieces = geometry_surface_pieces(g.primitives, place, color, materials, colors, surf)
                splist.extend(spieces)
        elif isinstance(n, Node):
            pl = multiply_matrices(place, n.matrix[:3,:])
            splist.extend(surface_pieces_from_nodes(n.children, surf, color, pl, ginst))
    return splist

def geometry_surface_pieces(primitives, place, color, materials, colors, surf):

    from collada import polylist, triangleset

    splist = []
    for p in primitives:
        if isinstance(p, polylist.Polylist):
            p = p.triangleset()
        if not isinstance(p, triangleset.TriangleSet):
            continue        # Skip line sets.

        t = p.vertex_index            # N by 3 array of vertex indices for triangles
        t = t.copy()                  # array from pycollada is not contiguous.
        v = p.vertex                  # M by 3 array of floats for vertex positions
        ni = p.normal_index           # N by 3 array of normal indices for triangles
        n = p.normal		      # M by 3 array of floats for vertex normals

        # Collada allows different normals on the same vertex in different triangles,
        # but Hydra only allows one normal per vertex.
        if not n is None:
            from numpy import empty
            vn = empty(v.shape, n.dtype)
            vn[t.ravel(),:] = n[ni.ravel(),:]

        vcolors = vertex_colors(p, t, len(v), colors)
        c = material_color(materials.get(p.material), color)

        sp = surf.newPiece()
        sp.save_in_session = True
        sp.geometry = v, t
        if not n is None:
            sp.normals = vn
        sp.color_list = [c]
        sp.position_list = [place]
        if not vcolors is None:
            sp.vertexColors = vcolors
        splist.append(sp)

    return splist

def add_geometry_instance(primitives, spieces, place, color, materials):

    for p,sp in zip(primitives, spieces):
        c = material_color(materials.get(p.material), color)
        sp.position_list.append(place)
        sp.color_list.append(c)

def material_color(material, color):

    if material is None:
        return color
    e = material.effect
    if e is None:
        return color
    c = e.diffuse
    if c is None:
        return color
    ct = tuple(c)
    return ct

def vertex_colors(triangle_set, tarray, nv, colors):

    carray = tuple((i,aname) for i,name,aname,x in triangle_set.getInputList().getList() if name == 'COLOR')
    if len(carray) == 0:
        return None
    ci,aname = carray[0]
    tc = triangle_set.indices[:,:,ci]    # color index for each of 3 triangle vertices
    colors = colors[aname[1:]].data      # Get colors array, remove leading "#" from array name.
    # Collada allows different colors on the same vertex in different triangles,
    # but Hydra only allows one color per vertex.
    from numpy import empty
    vc = empty((nv,4), colors.dtype)
    vc[tarray.ravel(),:] = colors[tc.ravel(),:]
    return vc

def create_surface_piece_instances(plist):
    for p in plist:
        clist = p.color_list
        tflist = p.position_list
        p.color = clist[0]
        p.placement = tflist[0]
        if len(clist) > 1:
            s = p.model
            pva, ta = p.geometry
            va, na = p.unplacedVerticesAndNormals
            for c, tf in zip(clist, tflist)[1:]:
                p2 = s.newPiece()
                p2.save_in_session = True
                p2.geometry = va, ta
                p2.normals = na
                p2.color = c
                p2.placement = tf
