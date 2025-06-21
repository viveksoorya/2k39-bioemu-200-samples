# -----------------------------------------------------------------------------
# Command to extract a piece of a volume data set within a surface.
#
#   mask <volumes> <surfaces>
#        [axis <x,y,z>]
#        [fullMap true|false]
#        [pad <d>]
#        [slab <width>|<d1,d2>]
#        [sandwich true|false]
#
#   mask #0 #1 axis 0,0,1 fullmap true pad 10
#
# masks volume #0 using surface #1 via projection along the z axis, and
# makes a full copy of the map (rather than a minimal subregion) and expands
# the surface along its per-vertex normal vectors before masking.
#
def mask_command(cmdname, args):

    from Commands import doExtensionFunc
    doExtensionFunc(mask, args, specInfo = [('surfaceSpec','surfaces',None)])

# -----------------------------------------------------------------------------
#
def mask(volumes, surfaces, axis = None, fullMap = False,
         extend = 0, pad = 0, slab = None, sandwich = True, invertMask = False,
         fillOverlap = False, spacing = None, border = 0, modelId = None):

    from Commands import CommandError, volumes_from_specifier, parse_floats
    from Commands import parse_model_id

    from Surface import selected_surface_pieces
    plist = selected_surface_pieces(surfaces, include_outline_boxes = False)
    if len(plist) == 0:
        raise CommandError, 'No surfaces specified'

    axis = parse_floats(axis, 'axis', 3, (0,1,0))

    if not isinstance(fullMap, (bool,int)):
        raise CommandError, 'fullMap option value must be true or false'
    if volumes == 'ones' and border != 0:
        fullMap = True

    if not isinstance(invertMask, (bool,int)):
        raise CommandError, 'invertMask option value must be true or false'

    if not isinstance(extend, int) or extend < 0:
        raise CommandError, 'extend option value must be a non-negative integer'

    if not isinstance(pad, (float,int)):
        raise CommandError, 'pad option value must be a number'

    if isinstance(slab, (float,int)):
        pad = (-0.5*slab, 0.5*slab)
    elif not slab is None:
        pad = parse_floats(slab, 'slab', 2)

    if not isinstance(sandwich, bool):
        raise CommandError, 'sandwich option value must be true or false'

    if not isinstance(border, (float,int)):
        raise CommandError, 'border option value must be a number'

    if not spacing is None:
        if isinstance(spacing, basestring):
            spacing = parse_floats(spacing, 'spacing', 3)
        elif not isinstance(spacing, (float,int)):
            raise CommandError, 'spacing option value must be a number'

    if volumes == 'ones':
        vlist = [ones_volume(plist, pad, spacing, border)]
    else:
        vlist = volumes_from_specifier(volumes)
    if len(vlist) == 0:
        raise CommandError, 'No volumes specified by %s' % volumes

    model_id = parse_model_id(modelId)

    mvlist = []
    from depthmask import surface_geometry, masked_volume
    from Matrix import xform_matrix, invert_matrix
    for v in vlist:
        tf = invert_matrix(xform_matrix(v.model_transform()))
        surfs = surface_geometry(plist, tf, pad)
        mv = masked_volume(v, surfs, axis, fullMap, sandwich, invertMask,
                           fillOverlap, extend, model_id)
        mvlist.append(mv)

    if volumes == 'ones':
        from chimera import openModels
        openModels.close(vlist)

    return mvlist

# -----------------------------------------------------------------------------
#
def ones_volume(plist, pad, spacing, border, default_size = 100):

    surf = plist[0].model
    xf = surf.openState.xform
    import Surface
    box = Surface.surface_box(plist, xf)
    mpad = pad if isinstance(pad, (float,int)) else max(abs(p) for p in pad)
    bsize = [s + 2*mpad + 2*border for s in (box.urb - box.llf).data()]
    if spacing is None:
        spacing = max(bsize)/default_size
    if isinstance(spacing, (float, int)):
        spacing = (spacing, spacing, spacing)
    from math import ceil
    size = [1 + int(ceil(s/sp)) for s,sp in zip(bsize,spacing)]
    origin = [x - (mpad+border) for x in box.llf.data()]
    from numpy import ones, float32
    varray = ones(size[::-1], float32)
    from VolumeData import Array_Grid_Data
    g = Array_Grid_Data(varray, origin, spacing, name = 'mask')
    import VolumeViewer
    v = VolumeViewer.volume_from_grid_data(g, model_id = (surf.id, surf.subid),
                                           show_dialog = False)
    return v

