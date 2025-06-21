# ----------------------------------------------------------------------------
# Volume series command.
#
#   Syntax: vseries <operation> <mapSpec>
#
from Commands import CommandError

players = set()         # Active players.

def vseries_command(cmdname, args):

    from Commands import bool_arg, float_arg, enum_arg, int_arg, string_arg
    from Commands import floats_arg, parse_subregion, volume_arg, color_arg
    from Commands import perform_operation
    ops = {
        'open': (open_op,
                 (('paths', string_arg),),
                 (),
                 ()),
        'align': (align_op,
                  (('series', series_arg),),
                  (),
                  (('encloseVolume', float_arg),
                   ('fastEncloseVolume', float_arg))),
        'save': (save_op,
                 (('series', series_arg),
                  ('path', string_arg)),
                 (),
                 (('subregion', parse_subregion),
                  ('valueType', string_arg),
                  ('threshold', float_arg),
                  ('zeroMean', bool_arg),
                  ('scaleFactor', float_arg),
                  ('encloseVolume', float_arg),
                  ('fastEncloseVolume', float_arg),
                  ('normalizeLevel', float_arg),
                  ('align', bool_arg),
                  ('onGrid', volume_arg),
                  ('mask', volume_arg),
                  ('finalValueType', string_arg),
                  ('compress', bool_arg)),
                 ),
        'measure': (measure_op,
                    (('series', series_arg),),
                    (),
                    (('output', string_arg),
                     ('centroids', bool_arg),
                     ('color', color_arg),
                     ('radius', float_arg),
                    )),
        'close': (close_op,
                 (('series', series_arg),),
                 (),
                 ()),
        'play': (play_op,
                 (('series', series_arg),),
                 (),
                 (('loop', bool_arg),
                  ('direction', enum_arg,
                   {'values':('forward', 'backward', 'oscillate')}),
                  ('normalize', bool_arg),
                  ('maxFrameRate', float_arg),
                  ('showMarkers', bool_arg),
                  ('precedingMarkerFrames', int_arg),
                  ('followingMarkerFrames', int_arg),
                  ('colorRange', float_arg),
                  ('cacheFrames', int_arg),
                  ('jumpTo', int_arg),
                  )),
        'stop': (stop_op,
                 (('series', series_arg),),
                 (),
                 ()),
        }

    perform_operation(cmdname, args, ops)

# -----------------------------------------------------------------------------
#
def play_op(series, direction = 'forward', loop = False, maxFrameRate = None,
            jumpTo = None, normalize = False, showMarkers = False,
            precedingMarkerFrames = 0, followingMarkerFrames = 0,
            colorRange = None, cacheFrames = 1):

    tstart = len(series[0].data_regions)-1 if direction == 'backward' else 0
    import play
    p = play.Play_Series(series,
                         start_time = tstart,
                         play_direction = direction,
                         loop = loop,
                         max_frame_rate = maxFrameRate,
                         normalize_thresholds = normalize,
                         show_markers = showMarkers,
                         preceding_marker_frames = precedingMarkerFrames,
                         following_marker_frames = followingMarkerFrames,
                         color_range = colorRange,
                         rendering_cache_size = cacheFrames)
    if not jumpTo is None:
        p.change_time(jumpTo)
    else:
        global players
        players.add(p)
        p.play()
    release_stopped_players()

# -----------------------------------------------------------------------------
#
def stop_op(series):

    for p in players:
        for s in series:
            if s in p.series:
                p.stop()
    release_stopped_players()
    
# -----------------------------------------------------------------------------
#
def open_op(paths):

    from OpenSave import tildeExpand
    pspec = tildeExpand(paths)
    if ',' in pspec:
        path_list = pspec.split(',')
    else:
        import glob
        path_list = glob.glob(pspec)
        path_list.sort()
    if len(path_list) == 0:
        raise CommandError('vseries: No files specified by "%s"' % paths)
    from .openseries import open_series
    open_series(path_list)

# -----------------------------------------------------------------------------
#
def close_op(series):

    import gui
    d = gui.volume_series_dialog()
    for s in series:
        d.close_series(s)

# -----------------------------------------------------------------------------
#
def align_op(series, encloseVolume = None, fastEncloseVolume = None):
    for s in series:
        align_series(s, encloseVolume, fastEncloseVolume)

# -----------------------------------------------------------------------------
#
def align_series(s, enclose_volume = None, fast_enclose_volume = None):

    n = len(s.data_regions)
    vprev = None
    for i,v in enumerate(s.data_regions):
        from chimera import replyobj
        replyobj.status('Aligning %s (%d of %d maps)' % (v.data.name, i+1, n))
        set_enclosed_volume(v, enclose_volume, fast_enclose_volume)
        if vprev:
            align(v, vprev)
        vprev = v

# -----------------------------------------------------------------------------
#
def set_enclosed_volume(v, enclose_volume, fast_enclose_volume):
    if not enclose_volume is None:
        level = v.surface_level_for_enclosed_volume(enclose_volume)
        v.set_parameters(surface_levels = [level])
    elif not fast_enclose_volume is None:
        level = v.surface_level_for_enclosed_volume(fast_enclose_volume,
                                                    rank_method = True)
        v.set_parameters(surface_levels = [level])

# -----------------------------------------------------------------------------
#
def align(v, vprev):

    v.openState.xform = vprev.openState.xform
    from FitMap.fitmap import map_points_and_weights, motion_to_maximum
    points, point_weights = map_points_and_weights(v, above_threshold = True)
    move_tf, stats = motion_to_maximum(points, point_weights, vprev,
                                       max_steps = 2000,
                                       ijk_step_size_min = 0.01,
                                       ijk_step_size_max = 0.5,
                                       optimize_translation = True,
                                       optimize_rotation = True)
    import Matrix
    v.openState.globalXform(Matrix.chimera_xform(move_tf))

# -----------------------------------------------------------------------------
#
def save_op(series, path, subregion = None, valueType = None,
            threshold = None, zeroMean = False, scaleFactor = None,
            encloseVolume = None, fastEncloseVolume = None, normalizeLevel = None,
            align = False, onGrid = None, mask = None, finalValueType = None, compress = False):

    if len(series) > 1:
        raise CommandError('vseries save: Can only save one series in a file, got %d'
                           % len(series))
    s = series[0]

    import OpenSave
    path = OpenSave.tildeExpand(path)

    from VolumeFilter.vopcommand import parse_value_type
    value_type = None if valueType is None else parse_value_type(valueType)
    final_value_type = None if finalValueType is None else parse_value_type(finalValueType)

    if onGrid is None and align:
        onGrid = s.data_regions[0]

    on_grid = None
    if not onGrid is None:
        vtype = s.data_regions[0].data.value_type if value_type is None else value_type
        on_grid = onGrid.writable_copy(value_type = vtype, show = False)

    n = len(s.data_regions)
    for i,v in enumerate(s.data_regions):
        from chimera import replyobj
        replyobj.status('Writing %s (%d of %d maps)' % (v.data.name, i+1, n))
        align_to = s.data_regions[i-1] if align and i > 0 else None
        d = processed_volume(v, subregion, value_type, threshold, zeroMean, scaleFactor,
                             encloseVolume, fastEncloseVolume, normalizeLevel,
                             align_to, on_grid, mask, final_value_type)
        d.name = '%04d' % i
        options = {'append': True, 'compress': compress}
        from VolumeData import cmap
        cmap.write_grid_as_chimera_map(d, path, options)

    if on_grid:
        on_grid.close()

# -----------------------------------------------------------------------------
#
def processed_volume(v, subregion = None, value_type = None, threshold = None,
                     zeroMean = False, scaleFactor = None,
                     encloseVolume = None, fastEncloseVolume = None, normalizeLevel = None,
                     align_to = None, on_grid = None, mask = None, final_value_type = None):
    d = v.data
    if not subregion is None:
        ijk_min, ijk_max = subregion
        from VolumeData import Grid_Subregion
        d = Grid_Subregion(d, ijk_min, ijk_max)

    if (value_type is None and threshold is None and not zeroMean and
        scaleFactor is None and align_to is None and on_grid is None and
        mask is None and final_value_type is None):
        return d

    m = d.full_matrix()
    if not value_type is None:
        m = m.astype(value_type)

    if not threshold is None:
        from numpy import array, putmask
        t = array(threshold, m.dtype)
        putmask(m, m < t, 0)
        
    if zeroMean:
        from numpy import float64
        mean = m.mean(dtype = float64)
        m = (m - mean).astype(m.dtype)

    if not scaleFactor is None:
        m = (m*scaleFactor).astype(m.dtype)

    if not encloseVolume is None or not fastEncloseVolume is None:
        set_enclosed_volume(v, encloseVolume, fastEncloseVolume)

    if not normalizeLevel is None:
        if len(v.surface_levels) == 0:
            raise CommandError('vseries save: normalizeLevel used but no level set for volume %s' % v.name)
        level = max(v.surface_levels)
        if zeroMean:
            level -= mean
        scale = normalizeLevel / level
        m = (m*scale).astype(m.dtype)

    if not align_to is None:
        align(v, align_to)

    if not on_grid is None:
        vc = v.writable_copy(value_type = m.dtype, show = False)
        vc.full_matrix()[:,:,:] = m
        m = on_grid.full_matrix()
        m[:,:,:] = 0
        on_grid.add_interpolated_values(vc)
        vc.close()
        d = on_grid.data

    if not mask is None:
        m[:,:,:] *= mask.full_matrix()

    if not final_value_type is None:
        m = m.astype(final_value_type)

    from VolumeData import Array_Grid_Data
    d = Array_Grid_Data(m, d.origin, d.step, d.cell_angles, d.rotation)

    return d

# -----------------------------------------------------------------------------
#
def measure_op(series, output = None, centroids = True, color = (.7,.7,.7,1), radius = None):

    from Measure import center
    import MeasureVolume as MV
    meas = []
    for s in series:
        n = s.number_of_times()
        for t in range(n):
            if t > 0:
                s.copy_display_parameters(0, t)
            shown = s.time_shown(t)
            s.show_time(t)
            v = s.data_regions[t]
            level = min(v.surface_levels)
            ci = center.volume_center_of_mass(v, level)
            c = v.data.ijk_to_xyz(ci)
            vol, area, holes = MV.surface_volume_and_area(v)
            meas.append((level, c, vol, area))
            if not shown:
                s.unshow_time(t, cache_rendering = False)

        if centroids:
            from VolumePath import Marker_Set, Link
            mset = Marker_Set('%s centroids' % s.name)
            mprev = None
            if radius is None:
                radius = min(v.data.step)
            lradius = 0.5*radius
            for i, (level, c, vol, area) in enumerate(meas):
                m = mset.place_marker(c, color, radius)
                m.set_note('%d' % i)
                m.show_note(False)
                m.extra_attributes = {'frame':t}
                if not mprev is None:
                    Link(m, mprev, color, lradius)
                mprev = m
            mset.marker_molecule().openState.xform = s.data_regions[0].openState.xform

        # Make text output
        lines = ['# Volume series measurements: %s\n' % s.name,
                 '#   n        level         x            y           z           step       distance       volume        area\n']
        d = 0
        cprev = None
        step = 0
        from Matrix import distance
        for n, (level, c, vol, area) in enumerate(meas):
            if cprev:
                step = distance(cprev, c)
                d += step
            cprev = c
            lines.append('%5d %12.5g %12.5g %12.5g %12.5g %12.5g %12.5g %12.5g %12.5g\n' %
                         (n, level, c[0], c[1], c[2], step, d, vol, area))
        text = ''.join(lines)
        if output:
            import OpenSave
            path = OpenSave.tildeExpand(output)
            f = open(path, 'w')
            f.write(text)
            f.close()
        else:
            from chimera import replyobj
            replyobj.info(text)
        
# -----------------------------------------------------------------------------
#
def series_arg(s):

  import Commands
  vlist = Commands.volumes_arg(s)
  sset = set()
  import gui
  d = gui.volume_series_dialog(create = False)
  if d:
    for v in vlist:
      for ser in d.series:
        if v in ser.data_regions:
          sset.add(ser)
  ns = len(sset)
  if ns == 0:
    raise CommandError('"%s" does not specify a volume series' % s)
  return list(sset)

# -----------------------------------------------------------------------------
#
def release_stopped_players():

  players.difference_update([p for p in players if p.play_handler is None])
