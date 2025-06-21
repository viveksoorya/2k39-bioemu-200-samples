# -----------------------------------------------------------------------------
# Read in an STL file and create a surface.
# 
def read_stl(path, average_normals = True, color = (.7,.7,.7,1)):

    f = open(path, 'rb')

    # First read 80 byte comment line.
    comment = f.read(80)

    # Next read uint32 triangle count.
    from numpy import fromstring, uint32, empty, float32
    tc = fromstring(f.read(4), uint32)        # triangle count

    # Next read 50 bytes per triangle containing float32 normal vector
    # followed three float32 vertices, followed by two "attribute bytes"
    # sometimes used to hold color information, but ignored by this reader.
    nv = empty((tc,12), float32)
    for t in range(tc):
        nt = f.read(12*4 + 2)
        nv[t,:] = fromstring(nt[:48], float32)

    f.close()

    va, na, ta = stl_geometry(nv, average_normals)

    from _surface import SurfaceModel
    s = SurfaceModel()
    from os.path import basename
    s.name = basename(path)
    p = s.addPiece(va, ta, color)
    p.normals = na
    p.save_in_session = True

    return s

# -----------------------------------------------------------------------------
#
def stl_geometry(nv, average_normals = True):

    if not average_normals:
        return stl_geometry_with_creases(nv)

    tc = nv.shape[0]

    # Assign numbers to vertices.
    from numpy import empty, int32, uint32, float32, zeros
    tri = empty((tc, 3), int32)
    vnum = {}
    for t in range(tc):
        v0, v1, v2 = nv[t,3:6], nv[t,6:9], nv[t,9:12]
        for a, v in enumerate((v0, v1, v2)):
            tri[t,a] = vnum.setdefault(tuple(v), len(vnum))

    # Make vertex coordinate array.
    vc = len(vnum)
    vert = empty((vc,3), float32)
    for v, vn in vnum.items():
        vert[vn,:] = v

    # Make average normals array.
    normals = zeros((vc,3), float32)
    for t,tvi in enumerate(tri):
        for i in tvi:
            normals[i,:] += nv[t,0:3]
    import Matrix
    Matrix.normalize_vectors(normals)

    return vert, normals, tri
  
# -----------------------------------------------------------------------------
#
def stl_geometry_with_creases(nv):

    # Combine identical vertices.  The must have identical normals too.
    from numpy import empty, uint32, float32
    tri = empty((tc, 3), uint32)
    vnum = {}
    for t in range(tc):
        normal = nv[t,0:3]
        v0, v1, v2 = nv[t,3:6], nv[t,6:9], nv[t,9:12]
        for a, v in enumerate((v0, v1, v2)):
            tri[t,a] = vnum.setdefault((v,normal), len(vnum))

    nv = len(vnum)
    vert = empty((vnum, 3), float32)
    normals = empty((vnum, 3), float32)
    for (v, n), vn in vnum.items():
        vert[vn,:] = v
        normals[vn,:] = n

  # If two triangle edges have the same vertex positions in opposite order
  # but use different normals then stictch them together with zero area
  # triangles.

  # TODO: Not finished.
