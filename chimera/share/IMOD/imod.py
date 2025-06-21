# -----------------------------------------------------------------------------
# Read segmentation data from IMOD 1.2 files.
#
def read_imod_segmentation(path, mesh = True, contours = True):

    clist = read_imod(path)
    import os.path
    name = os.path.basename(path)
    mlist = imod_models(clist, name,  mesh, contours)
    return mlist

# -----------------------------------------------------------------------------
#
def read_imod(path):

    f = open(path,'rb')
    file_id = f.read(4)
    if file_id != 'IMOD':
        f.close()
        raise TypeError, 'File %s is not an IMOD binary segmentation file.  First 4 bytes are not "IMOD"' % path
    f.seek(0)
    clist = read_imod_chunks(f)
    f.close()

    return clist
            
# -----------------------------------------------------------------------------
#
def read_imod_chunks(file):

    headers = []
    while True:
        id = file.read(4)
        from IMOD.imod_spec import chunk_formats, optional_chunk_format, eof_id
        if id in chunk_formats:
            cformat = chunk_formats[id]
        elif id == eof_id:
            break
        else:
#            print 'imod unrecognized chunk id', repr(id)
            cformat = optional_chunk_format
        h = read_chunk(file, cformat)
        h['id'] = id
        headers.append(h)
    return headers
    
# -----------------------------------------------------------------------------
#
def read_chunk(file, chunk_format):

    from imod_spec import char
    h = {}
    for data_type, name in chunk_format:
        if isinstance(data_type, tuple):                    # Array
            vtype = data_type[0]
            count = data_type[1]
            if isinstance(count, str):
                count = h[count]
            dim2 = None
            if len(data_type) >= 3:
                dim2 = data_type[2]
                count *= dim2
            if len(data_type) >= 4:
                bsize = data_type[3]
                count = ((count + bsize - 1) / bsize) * bsize
            if isinstance(vtype, (list, tuple)):
                a = [read_chunk(file, vtype) for c in range(count)]
                from numpy import array, object
                a = array(a, object)
            else:
                a = read_values(vtype, count, file)
            if vtype == char and dim2 is None:
                a = terminate_string_at_null_character(a.tostring())
            if dim2 and dim2 > 1:
                a = a.reshape((count/dim2, dim2))
        else:                                               # Single value
            a = read_values(data_type, 1, file)[0]
        h[name] = a
    return h
    
# -----------------------------------------------------------------------------
#
def read_values(data_type, count, file):

    from numpy import dtype, fromstring, little_endian
    bytes = dtype(data_type).itemsize * count
    s = file.read(bytes)
    if len(s) < bytes:
        raise SyntaxError, 'Failed reading %d bytes from IMOD file' % bytes
    a = fromstring(s, data_type)
    if little_endian:
        # File format requires values always to be big endian.
        a = a.byteswap()
    return a

# -----------------------------------------------------------------------------
#
def terminate_string_at_null_character(s):

    i = s.find('\0')
    if i >= 0:
        return s[:i]
    return s
    
# -----------------------------------------------------------------------------
#
def print_table(t):

    for key, value in sorted(t.items()):
        print key, value
    
# -----------------------------------------------------------------------------
# 
def imod_models(chunk_list, name, mesh, contours):

    mlist = []

    # Get coordinate transform before mesh and contour chunks
    tf = None

    use_minx = False
    if use_minx:
        for c in chunk_list:
            if c['id'] == 'MINX':
                # MINX chunk comes after mesh and contours.
                print 'MINX cscale', c['cscale'], 'ctrans', c['ctrans'], 'otrans', c['otrans'], 'crot', c['crot']
#                t = [xo-xc for xo,xc in zip(c['otrans'], c['ctrans'])]
                t = [-xc for xc in c['ctrans']]
                rx,ry,rz = c['crot']
                rx = ry = rz = 0
                import Matrix as M
                tf = M.multiply_matrices(M.rotation_transform((0,0,1), rz),
                                         M.rotation_transform((0,1,0), ry),
                                         M.rotation_transform((1,0,0), rx),
                                         M.translation_matrix(t),
                                         M.scale_matrix(c['cscale']))

    surf_model = None
    for c in chunk_list:
        cid = c['id']
        if cid == 'IMOD':
            xyz_scale = c['xscale'], c['yscale'], c['zscale']
            pixel_size = c['pixsize']
            units = c['units']
            # Units: 0 = pixels, 3 = km, 1 = m, -2 = cm, -3 = mm, 
            #        -6 = microns, -9 = nm, -10 = Angstroms, -12 = pm
            print 'IMOD pixel size =', pixel_size, 'units', units, ' scale', xyz_scale
#            print 'IMOD flags', bin(c['flags'])
            u = -10 if units == 0 else (0 if units == 1 else units)
            import math
            pixel_size_angstroms = pixel_size * math.pow(10,10+u)
            if tf is None:
                xs, ys, zs = [s*pixel_size_angstroms for s in xyz_scale]
                tf = ((xs, 0, 0, 0),
                      (0, ys, 0, 0),
                      (0, 0, zs, 0))
        elif cid == 'OBJT':
            alpha = 1.0 - 0.01*c['trans']
            object_rgba = (c['red'], c['green'], c['blue'], alpha)
            obj_name = c['name']
            pds = c['pdrawsize']
            radius = pds * pixel_size_angstroms if pds > 0 else pixel_size_angstroms
            fill = c['flags'] & (1 << 8)
            lines = not (c['flags'] & (1 << 11))
            only_points = (not lines and not fill)
            link = not only_points
            open_contours = c['flags'] & (1 << 3)
            mset = None
        elif cid == 'MESH':
            if mesh:
                if surf_model == None:
                    import _surface
                    surf_model = _surface.SurfaceModel()
                    surf_model.name = name + ' mesh'
                    mlist.append(surf_model)
                create_mesh(c, tf, object_rgba, surf_model, obj_name)
        elif cid == 'CONT':
            if contours:
                if mset == None:
                    from VolumePath import Marker_Set
                    mname = '%s %s contours' % (name, obj_name)
                    mset = Marker_Set(mname)
                    # Marker set already added to openModels so don't return
                    # it in mlist.
                create_contour(c, tf, radius, object_rgba, link, open_contours, mset)

    return mlist
    
# -----------------------------------------------------------------------------
# 
def create_mesh(c, transform, rgba, surf_model, name):

    varray, tarray = mesh_geometry(c)
    if len(tarray) > 0:
        import Matrix
        Matrix.transform_points(varray, transform)
        p = surf_model.addPiece(varray, tarray, rgba)
        p.oslName = name
        p.save_in_session = True
        return p
    return None
    
# -----------------------------------------------------------------------------
# 
def mesh_geometry(c):

    from numpy import reshape, array, intc
    varray = reshape(c['vert'], (c['vsize'],3))
    tlist = c['index']
    t = 0
    triangles = []
    read_vertices = False
    while True:
        i = tlist[t]
        if i >= 0:
            if read_vertices:
                if normals:
                    triangles.append((tlist[t+1], tlist[t+3], tlist[t+5]))
                    t += 6
                else:
                    triangles.append((tlist[t], tlist[t+1], tlist[t+2]))
                    t += 3
            else:
                t += 1          # Ignore index
        elif i == -25:
            # vertex indices only
            read_vertices = True
            normals = False
            t += 1
        elif i == -23:
            # normal indices and vertex indices
            read_vertices = True
            normals = True
            t += 1
        elif i == -22:
            t += 1        # end of polygon
            read_vertices = False
        elif i == -1:
            # End of index list
            break
        elif i == -21:
            # Concave polygon.  Ignore.
            t += 1
        elif i == -20:
            # Normal vector index.  Ignore.
            t += 1
        elif i == -24:
            # Convex polygon boundary.  Ignore.
            t += 1
        else:
            print 'Unexpected index', i
            t += 1
    tarray = array(triangles, intc)
    # Remove normals that are mixed in with vertices in varray.
    varray, tarray = remove_unused_vertices(varray, tarray)
    return varray, tarray

# -----------------------------------------------------------------------------
# 
def remove_unused_vertices(varray, tarray):

    from numpy import bincount, greater, sum, nonzero, cumsum, intc
    v = bincount(tarray.flat)      # How many times each vertex is used
    greater(v, 0, v)               # 1 if a vertex is used, else 0
    if sum(v) == len(v):
        return varray, tarray      # All vertices used.
    used = nonzero(v)[0]
    vuarray = varray[used,:]
    cumsum(v, out=v)
    v -= 1                         # Vertex index mapping 
    tuarray = v[tarray].astype(intc)
    return vuarray, tuarray

# -----------------------------------------------------------------------------
# 
def create_contour(c, transform, radius, rgba, link, open_contours, mset):

    from numpy import reshape
    varray = reshape(c['pt'], (c['psize'],3)).copy()
    import Matrix
    Matrix.transform_points(varray, transform)
    mlist = []
    links = []
    r = radius

    from VolumePath import Link
    for xyz in varray:
        m = mset.place_marker(xyz, rgba, r)
        if link and mlist:
            l = Link(m, mlist[-1], rgba, r)
            links.append(l)
        mlist.append(m)
    if not open_contours:
        open_contours = (c['flags'] & (1 << 3))
    if link and len(mlist) >= 3 and not open_contours:
        l = Link(mlist[-1], mlist[0], rgba, radius)
        links.append(l)
    if radius == 0:
        for m in mlist:
            m.atom.drawMode = m.atom.Dot
        for l in links:
            l.bond.drawMode = l.bond.Wire
