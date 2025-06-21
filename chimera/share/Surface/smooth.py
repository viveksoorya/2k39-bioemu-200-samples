def smooth_surface_piece(p, factor, iterations, surf):
    from _surface import smooth_vertex_positions
    va,ta = p.geometry
    va = va.copy()
    na = p.normals.copy()
    smooth_vertex_positions(va, ta, factor, iterations)
    smooth_vertex_positions(na, ta, factor, iterations)
    if surf is None:
        p.geometry = va,ta
        p.normals = na
        np = p
    else:
        np = surf.newPiece()
        np.geometry = va,ta
        np.normals = na
        np.color = p.color
        np.displayStyle = p.displayStyle
        np.save_in_session = True
    return np
