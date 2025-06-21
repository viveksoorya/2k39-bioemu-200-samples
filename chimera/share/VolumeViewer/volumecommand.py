# -----------------------------------------------------------------------------
# Implementation of "volume" command.
#
def volume_command(cmdname, args):

    from Commands import parse_arguments
    from Commands import string_arg, bool_arg, bool3_arg, enum_arg
    from Commands import float_arg, floats_arg, float3_arg
    from Commands import int_arg, ints_arg, int3_arg, color_arg
    from Commands import volume_region_arg, openstate_arg

    from VolumeData.fileformats import file_writers
    stypes = [fw[1] for fw in file_writers]
    from VolumeViewer.volume import Rendering_Options
    ro = Rendering_Options()
    allow_1_or_3 = {'allowed_counts': (1,3)}

    req_args = ()
    opt_args = (('volumes', string_arg),)
    kw_args = (('style', enum_arg, {'values': ('surface', 'mesh', 'solid')}),
               ('show', ()),
               ('hide', ()),
               ('toggle', ()),
               ('level', floats_arg, {'allowed_counts': (1,2)}, 'multiple'),
               ('rmsLevel', floats_arg, {'allowed_counts': (1,2)}, 'multiple'),
               ('sdLevel', floats_arg, {'allowed_counts': (1,2)}, 'multiple'),
               ('encloseVolume', floats_arg),
               ('fastEncloseVolume', floats_arg),
               ('color', color_arg, 'multiple'),
               ('brightness', float_arg, {'min': 0.0}),
               ('transparency', float_arg, {'min': 0.0, 'max':1.0}),
               ('step', ints_arg, allow_1_or_3),
               ('region', volume_region_arg),
               ('nameRegion', string_arg),
               ('expandSinglePlane', bool_arg),
               ('origin', floats_arg, allow_1_or_3),
               ('originIndex', floats_arg, allow_1_or_3),
               ('voxelSize', floats_arg, allow_1_or_3),
               ('planes', planes_arg),
               ('dumpHeader', bool_arg),
# Symmetry assignment.
               ('symmetry', string_arg),
               ('center', string_arg),
               ('centerIndex', floats_arg),
               ('axis', string_arg),
               ('coordinateSystem', openstate_arg),
# File saving options.
               ('save', string_arg),
               ('saveFormat', enum_arg, {'values': stypes}),
               ('saveRegion', volume_region_arg),
               ('saveStep', ints_arg, allow_1_or_3),
               ('maskZone', bool_arg),
               ('chunkShapes', enum_arg,
                {'values':('zyx','zxy','yxz','yzx','xzy','xyz'),
                 'multiple':True}),
               ('append', bool_arg),
               ('compress', bool_arg),
               ('baseIndex', int_arg),
# Global options.
               ('dataCacheSize', float_arg),
               ('showOnOpen', bool_arg),
               ('voxelLimitForOpen', float_arg),
               ('showPlane', bool_arg),
               ('voxelLimitForPlane', float_arg),
# Rendering options.
               ('showOutlineBox', bool_arg),
               ('outlineBoxRgb', color_arg),
               ('outlineBoxLinewidth', float_arg),
               ('limitVoxelCount', bool_arg),
               ('voxelLimit', float_arg),
               ('colorMode', enum_arg, {'values': ro.color_modes}),
               ('projectionMode', enum_arg, {'values': ro.projection_modes}),
               ('btCorrection', bool_arg),
               ('minimalTextureMemory', bool_arg),
               ('maximumIntensityProjection', bool_arg),
               ('linearInterpolation', bool_arg),
               ('dimTransparency', bool_arg),
               ('dimTransparentVoxels', bool_arg),
               ('lineThickness', float_arg),
               ('smoothLines', bool_arg),
               ('meshLighting', bool_arg),
               ('twoSidedLighting', bool_arg),
               ('flipNormals', bool_arg),
               ('subdivideSurface', bool_arg),
               ('subdivisionLevels', int_arg),
               ('surfaceSmoothing', bool_arg),
               ('smoothingIterations', int_arg),
               ('smoothingFactor', float_arg),
               ('squareMesh', bool_arg),
               ('capFaces', bool_arg),
               ('boxFaces', bool_arg),
               ('orthoplanes', enum_arg,
                {'values':('xyz', 'xy', 'xz', 'yz', 'off')}),
               ('positionPlanes', int3_arg),
               )
    kw = parse_arguments(cmdname, args, req_args, opt_args, kw_args)

    # Extra parsing.
    for aname in ('step', 'origin', 'originIndex', 'voxelSize', 'centerIndex',
                  'saveStep'):
        if aname in kw and len(kw[aname]) == 1:
            x = kw[aname][0]
            kw[aname] = (x,x,x)
    if 'outlineBoxRgb' in kw:
        kw['outlineBoxRgb'] = kw['outlineBoxRgb'][:3]

    # Special defaults
    if kw.get('boxFaces', None):
        defaults = (('style', 'solid'), ('colorMode', 'opaque8'),
                    ('showOutlineBox', True), ('expandSinglePlane', True),
                    ('orthoplanes', 'off'))
    elif kw.get('orthoplanes', 'off') != 'off':
        defaults = (('style', 'solid'), ('colorMode', 'opaque8'),
                    ('showOutlineBox', True), ('expandSinglePlane', True))
    elif 'boxFaces' in kw or 'orthoplanes' in kw:
        defaults = (('colorMode', 'auto8'),)
    else:
        defaults = ()
    for opt, value in defaults:
        if not opt in kw:
            kw[opt] = value
            
    volume(**kw)
    
# -----------------------------------------------------------------------------
#
def volume(volumes = [],
           style = None,
           show = None,
           hide = None,
           toggle = None,
           level = None,
           rmsLevel = None,
           sdLevel = None,
           encloseVolume = None,
           fastEncloseVolume = None,
           color = None,
           brightness = None,
           transparency = None,
           step = None,
           region = None,
           nameRegion = None,
           expandSinglePlane = None,
           origin = None,
           originIndex = None,
           voxelSize = None,
           planes = None,
           dumpHeader = False,
# Symmetry assignment.
           symmetry = None,
           center = (0,0,0),
           centerIndex = None,
           axis = (0,0,1),
           coordinateSystem = None,
# File saving options.
           save = None,
           saveFormat = None,
           saveRegion = None,
           saveStep = None,
           maskZone = True,
           chunkShapes = None,
           append = None,
           compress = None,
           baseIndex = 1,
# Global options.
           dataCacheSize = None,
           showOnOpen = None,
           voxelLimitForOpen = None,
           showPlane = None,
           voxelLimitForPlane = None,
# Rendering options.
           showOutlineBox = None,
           outlineBoxRgb = None,
           outlineBoxLinewidth = None,
           limitVoxelCount = None,          # auto-adjust step size
           voxelLimit = None,               # Mvoxels
           colorMode = None,                # solid rendering pixel formats
           projectionMode = None,           # auto, 2d-xyz, 2d-x, 2d-y, 2d-z, 3d
           btCorrection = None,             # brightness and transparency
           minimalTextureMemory = None,
           maximumIntensityProjection = None,
           linearInterpolation = None,
           dimTransparency = None,          # for surfaces
           dimTransparentVoxels = None,     # for solid rendering
           lineThickness = None,
           smoothLines = None,
           meshLighting = None,
           twoSidedLighting = None,
           flipNormals = None,
           subdivideSurface = None,
           subdivisionLevels = None,
           surfaceSmoothing = None,
           smoothingIterations = None,
           smoothingFactor = None,
           squareMesh = None,
           capFaces = None,
           boxFaces = None,
           orthoplanes = None,
           positionPlanes = None,
           ):

    from Commands import CommandError

    # Find volume arguments.
    if volumes == 'all':
        from volume import volume_list
        vlist = volume_list()
    else:
        import Commands
        vlist = Commands.volumes_from_specifier(volumes)

    # Adjust global settings.
    loc = locals()
    gopt = ('dataCacheSize', 'showOnOpen', 'voxelLimitForOpen',
            'showPlane', 'voxelLimitForPlane')
    gsettings = dict((n,loc[n]) for n in gopt if not loc[n] is None)
    if gsettings:
        apply_global_settings(gsettings)

    if len(gsettings) == 0 and len(vlist) == 0:
        raise CommandError('No volumes specified%s' %
                           (' by "%s"' % volumes if volumes else ''))

    # Apply volume settings.
    dopt = ('style', 'show', 'hide', 'toggle', 'level', 'rmsLevel', 'sdLevel',
            'encloseVolume', 'fastEncloseVolume',
            'color', 'brightness', 'transparency',
            'step', 'region', 'nameRegion', 'expandSinglePlane', 'origin',
            'originIndex', 'voxelSize', 'planes',
            'symmetry', 'center', 'centerIndex', 'axis', 'coordinateSystem', 'dumpHeader')
    dsettings = dict((n,loc[n]) for n in dopt if not loc[n] is None)
    ropt = (
        'showOutlineBox', 'outlineBoxRgb', 'outlineBoxLinewidth',
        'limitVoxelCount', 'voxelLimit', 'colorMode', 'projectionMode',
        'btCorrection', 'minimalTextureMemory', 'maximumIntensityProjection',
        'linearInterpolation', 'dimTransparency', 'dimTransparentVoxels',
        'lineThickness', 'smoothLines', 'meshLighting',
        'twoSidedLighting', 'flipNormals', 'subdivideSurface',
        'subdivisionLevels', 'surfaceSmoothing', 'smoothingIterations',
        'smoothingFactor', 'squareMesh', 'capFaces', 'boxFaces')
    rsettings = dict((n,loc[n]) for n in ropt if not loc[n] is None)
    if not orthoplanes is None:
        rsettings['orthoplanesShown'] = ('x' in orthoplanes,
                                         'y' in orthoplanes,
                                         'z' in orthoplanes)
    if not positionPlanes is None:
        rsettings['orthoplanePositions'] = positionPlanes

    for v in vlist:
        apply_volume_options(v, dsettings, rsettings)

    # Save files.
    fopt = ('save', 'saveFormat', 'saveRegion', 'saveStep', 'maskZone',
            'chunkShapes', 'append', 'compress', 'baseIndex')
    fsettings = dict((n,loc[n]) for n in fopt if not loc[n] is None)
    save_volumes(vlist, fsettings)
    
# -----------------------------------------------------------------------------
#
def apply_global_settings(gsettings):

    gopt = dict((camel_case_to_underscores(k),v) for k,v in gsettings.items())
    from volume import default_settings
    default_settings.update(gopt)
    if 'dataCacheSize' in gsettings:
        from VolumeData import data_cache
        data_cache.resize(gsettings['dataCacheSize'] * (2**20))
    
# -----------------------------------------------------------------------------
#
def apply_volume_options(v, doptions, roptions):

    if 'style' in doptions:
        v.set_representation(doptions['style'])

    kw = level_and_color_settings(v, doptions)
    ropt = dict((camel_case_to_underscores(k),v) for k,v in roptions.items())
    kw.update(ropt)
    if kw:
        v.set_parameters(**kw)

    if 'encloseVolume' in doptions:
        levels = [v.surface_level_for_enclosed_volume(ev) for ev in doptions['encloseVolume']]
        v.set_parameters(surface_levels = levels)
    elif 'fastEncloseVolume' in doptions:
        levels = [v.surface_level_for_enclosed_volume(ev, rank_method = True)
                  for ev in doptions['fastEncloseVolume']]
        v.set_parameters(surface_levels = levels)

    if 'region' in doptions or 'step' in doptions:
        r = v.subregion(doptions.get('step', None),
                        doptions.get('region', None))
    else:
        r = None
    if not r is None:
        ijk_min, ijk_max, ijk_step = r
        v.new_region(ijk_min, ijk_max, ijk_step, show = False,
                     adjust_step = not 'step' in doptions)
    if doptions.get('expandSinglePlane', False):
        v.expand_single_plane()

    if 'nameRegion' in doptions:
        name = doptions['nameRegion']
        if r is None:
            r = v.region
        if r:
            v.region_list.add_named_region(name, r[0], r[1])

    if 'planes' in doptions:
        import volume
        volume.cycle_through_planes(v, *doptions['planes'])

    d = v.data
    if 'originIndex' in doptions:
        index_origin = doptions['originIndex']
        xyz_origin = [x0-x for x0,x in zip(d.ijk_to_xyz((0,0,0)),d.ijk_to_xyz(index_origin))]
        d.set_origin(xyz_origin)
    elif 'origin' in doptions:
        origin = doptions['origin']
        d.set_origin(origin)

    if 'voxelSize' in doptions:
        vsize = doptions['voxelSize']
        if min(vsize) <= 0:
            from Commands import CommandError
            raise CommandError('Voxel size must positive, got %g,%g,%g'
                               % tuple(vsize))
        # Preserve index origin.
        index_origin = d.xyz_to_ijk((0,0,0))
        d.set_step(vsize)
        xyz_origin = [x0-x for x0,x in zip(d.ijk_to_xyz((0,0,0)),d.ijk_to_xyz(index_origin))]
        d.set_origin(xyz_origin)

    if 'symmetry' in doptions:
        sym, c, a = doptions['symmetry'], doptions['center'], doptions['axis']
        csys = doptions.get('coordinateSystem', v.openState)
        if 'centerIndex' in doptions:
            c = v.data.ijk_to_xyz(doptions['centerIndex'])
            if csys != v.openState:
                import Matrix as M
                c = M.xform_xyz(c, v.openState.xform, csys.xform)
        from SymmetryCopies import symcmd
        tflist, csys = symcmd.parse_symmetry(sym, c, a, csys, v, 'volume')
        if csys != v.openState:
            tflist = symcmd.transform_coordinates(tflist, csys, v.openState)
        d.symmetries = tflist

    if 'show' in doptions:
        v.initialize_thresholds()
        v.show()
    elif 'hide' in doptions:
        v.unshow()
    elif 'toggle' in doptions:
        if v.shown():
            v.unshow()
        else:
            v.show()
    elif v.shown():
        v.show()
    elif v.representation in ('surface', 'mesh'):
        mesh = (v.representation == 'mesh')
        v.update_surface(mesh, v.rendering_options)
    elif v.representation == 'solid' and v.solid:
        v.update_solid(v.rendering_options, show = False)

    if 'dumpHeader' in doptions and doptions['dumpHeader']:
        show_file_header(v.data)

# TODO:
#  Allow quoted color names.
#  Could allow region name "full" or "back".
#  Could allow voxel_size or origin to be "original".

# -----------------------------------------------------------------------------
#
def save_volumes(vlist, doptions):

    if not 'save' in doptions:
        return
    
    path = doptions['save']
    format = doptions.get('saveFormat', None)
    from VolumeData import fileformats
    if fileformats.file_writer(path, format) is None:
        format = 'mrc'
    options = {}
    if 'chunkShapes' in doptions:
        options['chunk_shapes'] = doptions['chunkShapes']
    if 'append' in doptions and doptions['append']:
        options['append'] = True
    if 'compress' in doptions and doptions['compress']:
        options['compress'] = True
    if path in ('browse', 'browser'):
        from VolumeData import select_save_path
        path, format = select_save_path()
    if path:
        subregion = doptions.get('saveRegion', None)
        step = doptions.get('saveStep', (1,1,1))
        mask_zone = doptions.get('maskZone', True)
        base_index = doptions.get('baseIndex', 1)
        grids = [v.grid_data(subregion, step, mask_zone) for v in vlist]
        from VolumeData import save_grid_data
        if is_multifile_save(path):
            for i,g in enumerate(grids):
                save_grid_data(g, path % (i + base_index), format, options)
        else:
            save_grid_data(grids, path, format, options)
   
# -----------------------------------------------------------------------------
# Check if file name contains %d type format specification.
#
def is_multifile_save(path):
    try:
        path % 0
    except:
        return False
    return True
   
# -----------------------------------------------------------------------------
#
def level_and_color_settings(v, options):

    kw = {}

    # Code below modifies levels, avoid modifying options argument
    from copy import deepcopy
    levels = deepcopy(options.get('level', []))
    rms_levels = deepcopy(options.get('rmsLevel', []))
    sd_levels = deepcopy(options.get('sdLevel', []))
    if rms_levels or sd_levels:
        import VolumeStatistics as vs
        mean, sd, rms = vs.mean_sd_rms(v.matrix())
        if rms_levels:
            for lvl in rms_levels:
                lvl[0] *= rms
            levels.extend(rms_levels)
        if sd_levels:
            for lvl in sd_levels:
                lvl[0] *= sd
            levels.extend(sd_levels)
        
    colors = options.get('color', [])

    # Allow 0 or 1 colors and 0 or more levels, or number colors matching
    # number of levels.
    from Commands import CommandError
    if len(colors) > 1 and len(colors) != len(levels):
        raise CommandError('Number of colors (%d) does not match number of levels (%d)' % (len(colors), len(levels)))

    style = options.get('style', v.representation)
    if style in ('mesh', None):
        style = 'surface'

    if style == 'solid':
        if [l for l in levels if len(l) != 2]:
            raise CommandError('Solid level must be <data-value,brightness-level>')
        if levels and len(levels) < 2:
            raise CommandError('Must specify 2 or more levels for solid style')
    elif style == 'surface':
        if [l for l in levels if len(l) != 1]:
            raise CommandError('Surface level must be a single data value')
        levels = [lvl[0] for lvl in levels]

    if levels:
        kw[style+'_levels'] = levels

    if len(colors) == 1:
        if levels:
            clist = [colors[0]]*len(levels)
        else:
            clist = [colors[0]]*len(getattr(v, style + '_levels'))
        kw[style+'_colors'] = clist
    elif len(colors) > 1:
        kw[style+'_colors'] = colors

    if len(levels) == 0 and len(colors) == 1:
        kw['default_rgba'] = colors[0]

    if 'brightness' in options:
        kw[style+'_brightness_factor'] = options['brightness']

    if 'transparency' in options:
        if style == 'surface':
            kw['transparency_factor'] = options['transparency']
        else:
            kw['transparency_depth'] = options['transparency']

    return kw

# -----------------------------------------------------------------------------
# Arguments are axis,pstart,pend,pstep,pdepth.
#
def planes_arg(planes):

    axis, param = (planes.split(',',1) + [''])[:2]
    from Commands import enum_arg, floats_arg, CommandError
    p = [enum_arg(axis, ('x','y','z'))]
    if param:
        p += floats_arg(param)
    if len(p) < 2 or len(p) > 5:
        raise CommandError('planes argument must have 2 to 5 comma-separated values: axis,pstart,pend,pstep,pdepth, got "%s"' % planes)
    return p
    
# -----------------------------------------------------------------------------
#
def camel_case_to_underscores(s):

    from string import uppercase
    su = ''.join([('_' + c.lower() if c in uppercase else c) for c in s])
    return su
    
# -----------------------------------------------------------------------------
#
def show_file_header(d):
    from chimera import replyobj
    if hasattr(d, 'file_header') and isinstance(d.file_header, dict):
        h = d.file_header
        klist = list(h.keys())
        klist.sort()
        msg = ('File header for %s\n' % d.path +
               '\n'.join(('%s = %s' % (k, str(h[k]))) for k in klist))
        from Accelerators.standard_accelerators import show_reply_log
        show_reply_log()
    else:
        msg = 'No header info for %s' % d.name
        replyobj.status(msg)
    replyobj.info(msg + '\n')
