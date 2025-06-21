from actions import surface_models
from actions import surface_pieces, selected_surface_pieces, all_surface_pieces
from actions import filter_surface_pieces
from actions import show_surfaces, hide_surfaces
from actions import color_surfaces, delete_surfaces
from actions import show_surfaces_as_mesh, show_surfaces_filled
from split import split_surfaces, split_selected_surfaces
from actions import toggle_surface_selectability

from bounds import surface_sphere, surface_box

# -----------------------------------------------------------------------------
# Used by methods that color a surface and automatically update the coloring.
# Calling this routine turns off the previous auto-coloring code.
#
def set_coloring_method(name, model, stop_cb = None):

    if hasattr(model, 'coloring_method'):
        cname, cb = model.coloring_method
        if name != cname:
            if cb:
                cb(model)
    model.coloring_method = (name, stop_cb)

# -----------------------------------------------------------------------------
# Used by methods that adjust surface visibility automatically.
# Calling this routine turns off the previous visibility-adjusting code.
#
def set_visibility_method(name, model, stop_cb = None):

    if hasattr(model, 'visibility_method'):
        cname, cb = model.visibility_method
        if name != cname:
            if cb:
                cb(model)
    model.visibility_method = (name, stop_cb)

# -----------------------------------------------------------------------------
#
def visibility_method(model):

    if hasattr(model, 'visibility_method'):
        cname, cb = model.visibility_method
        return cname
    return None

# -----------------------------------------------------------------------------
#
def visibility_updating(model):

    if hasattr(model, 'visibility_method'):
        cname, cb = model.visibility_method
        return not cb is None
    return False

# -----------------------------------------------------------------------------
#
def reshow_surface(model):

    import chimera
    if isinstance(model, chimera.MSMSModel):
        model.visibilityMode = model.ByAtom
    else:
        for p in model.surfacePieces:
            show_all_triangles(p)

# -----------------------------------------------------------------------------
#
def show_all_triangles(p):

    mask = p.triangleAndEdgeMask
    if not mask is None:
        mask |= 0x8
        p.triangleAndEdgeMask = mask

# -----------------------------------------------------------------------------
# TODO: Make set_triangle_mask() surface piece method.
#
def set_triangle_mask(p, m):

    mask = p.triangleAndEdgeMask
    if mask is None:
        mask = m * 0xf
    else:
        mask &= 0x7
        mask |= (m * 0x8)
    p.triangleAndEdgeMask = mask

# -----------------------------------------------------------------------------
#
def surface_models_with_id(model_id, require_one = False, at_most_one = False):

    from chimera import openModels as om
    if model_id is None or model_id == (om.Default, om.Default):
        return (None if require_one or at_most_one else [])

    from _surface import SurfaceModel
    id, subid = model_id
    slist = om.list(id = id, subid = subid, modelTypes = [SurfaceModel])
    if require_one or at_most_one:
        if len(slist) == 0:
            if at_most_one:
                return None
            mid = '%d' % id if subid == om.Default else '%d.%d' % (id, subid)
            from Commands import CommandError
            raise CommandError('no surfaces with model id %s' % mid)
        elif len(slist) > 1:
            mid = '%d' % id if subid == om.Default else '%d.%d' % (id, subid)
            from Commands import CommandError
            raise CommandError('multiple surfaces with model id %s' % mid)
        return slist[0]

    return slist
