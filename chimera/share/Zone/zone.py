# -----------------------------------------------------------------------------
# Implementation of command "zone" that selects atoms or surface pieces near
# other atoms are surface pieces.
#

def zone_command(cmdname, args):
  
    from Commands import parse_arguments, specifier_arg, float_arg, bool_arg
    req_args = (('near', specifier_arg),
                ('range', float_arg))
    opt_args = (('find', specifier_arg),)
    kw_args = (('extend', bool_arg),)
    kw = parse_arguments(cmdname, args, req_args, opt_args, kw_args)
    zone(**kw)
                    
# -----------------------------------------------------------------------------
#
def zone(near, range, find = None, extend = False):

    from Commands import CommandError

    na = near.atoms()
    import Surface as s
    ns = s.selected_surface_pieces(near, include_outline_boxes = False)

    if len(na) == 0 and len(ns) == 0:
      raise CommandError('No atoms or surfaces specified')

    if find is None:
      from chimera import selection, openModels as om
      find = selection.ItemizedSelection(om.list())

    fa = find.atoms()
    fs = s.selected_surface_pieces(find, include_outline_boxes = False)

    if len(fa) == 0 and len(fs) == 0:
      raise CommandError('No target atoms or surfaces')

    # Remove near stuff.
    if na:
      fa = list(set(fa).difference(na))
    if ns:
      fs = list(set(fs).difference(ns))

    from Matrix import xform_matrix, identity_matrix
    from _multiscale import get_atom_coordinates
    naxyz = get_atom_coordinates(na, transformed = True)
    nsxyz = [(p.geometry[0],xform_matrix(p.model.openState.xform)) for p in ns]
    nxyz = [(naxyz,identity_matrix())] + nsxyz
    faxyz = get_atom_coordinates(fa, transformed = True)
    fsxyz = [(p.geometry[0],xform_matrix(p.model.openState.xform)) for p in fs]
    fxyz = [(faxyz,identity_matrix())] + fsxyz

    from _closepoints import find_close_points_sets, BOXES_METHOD
    i1, i2 = find_close_points_sets(BOXES_METHOD, nxyz, fxyz, range)

    sel = []
    from numpy import take, compress
    sel.extend(take(fa,i2[0]))
    sel.extend(compress([len(i) > 0 for i in i2[1:]],fs))
    if extend:
      sel.extend(na)
      sel.extend(ns)

    from chimera import selection
    selection.setCurrent(sel)
