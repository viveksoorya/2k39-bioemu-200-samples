# -----------------------------------------------------------------------------
# Show a series of maps.
#
class Play_Series:

  def __init__(self, series = [], start_time = None, time_step_cb = None,
               play_direction = 'forward', loop = False, max_frame_rate = None,
               show_markers = False,
               preceding_marker_frames = 0, following_marker_frames = 0,
               color_range = None,
               normalize_thresholds = False,
               rendering_cache_size = 1):

    self.series = series
    self.current_time = None
    self.start_time = start_time
    self.time_step_cb = time_step_cb

    self.play_handler = None
    self.set_play_direction(play_direction) # 'forward', 'backward', 'oscillate'
    self.loop = loop
    self.max_frame_rate = max_frame_rate
    self.last_rendering_walltime = None

    self.show_markers = show_markers
    self.preceding_marker_frames = preceding_marker_frames
    self.following_marker_frames = following_marker_frames

    self.color_range = color_range

    self.normalize_thresholds = normalize_thresholds

    self.rendering_cache_size = rendering_cache_size
    self.rendered_times = []       # For limiting cached renderings
    self.rendered_times_table = {}

    self.timer_id = {}             # For delaying update of volume dialog

  # ---------------------------------------------------------------------------
  #
  def set_play_direction(self, direction):

    self.play_direction = direction
    self.step = {'forward':1, 'backward':-1, 'oscillate':1}[direction]
  
  # ---------------------------------------------------------------------------
  #
  def play(self):

    if self.play_handler is None:
      from chimera import triggers
      h = triggers.addHandler('new frame', self.next_time_cb, None)
      self.play_handler = h
  
  # ---------------------------------------------------------------------------
  #
  def stop(self):

    if self.play_handler:
      from chimera import triggers
      triggers.deleteHandler('new frame', self.play_handler)
      self.play_handler = None

  # ---------------------------------------------------------------------------
  #
  def next_time_cb(self, trigger_name, call_data, trigger_data):

    if self.delay_next_frame():
      return
      
    t = self.current_time
    if t is None:
      if not self.start_time is None:
        self.change_time(self.start_time)
      return

    tslist = self.series
    if len(tslist) == 0:
      return
    nt = tslist[0].number_of_times()
    if nt == 0:
      return

    if self.play_direction == 'oscillate':
      if self.step > 0:
        if t == nt - 1:
          self.step = -1
      elif t == 0:
        self.step = 1

    tn = t + self.step
    if self.loop:
      tn = tn % nt
    elif tn % nt != tn:
      self.stop()       # Reached the end or the beginning
      return

    self.change_time(tn)

  # ---------------------------------------------------------------------------
  #
  def delay_next_frame(self):

    if self.max_frame_rate is None:
      return False

    t0 = self.last_rendering_walltime
    import time
    t = time.time()
    if t0 != None:
      r = self.max_frame_rate
      if r != None and (t-t0)*r < 1:
        return True
      
    self.last_rendering_walltime = t
    return False

  # ---------------------------------------------------------------------------
  #
  def change_time(self, t):

    self.current_time = t
    if t is None:
      return

    tslist = self.series
    tslist = [ts for ts in tslist
    	      if t < ts.number_of_times() and not ts.is_volume_closed(t)]

    for ts in tslist:
      t0 = self.update_rendering_settings(ts, t)
      self.show_time(ts, t)
      if ts.last_shown_time != t:
        self.unshow_time(ts, ts.last_shown_time)
      if t0 != t:
        self.unshow_time(ts, t0)
      ts.last_shown_time = t
      self.update_volume_dialog(ts, t)

    if tslist:
      self.update_marker_display()
      self.update_color_zone()

    if self.time_step_cb:
      self.time_step_cb(t)
    
  # ---------------------------------------------------------------------------
  # Update based on active volume viewer data set if it is part of series,
  # otherwise use previously shown time.
  #
  def update_rendering_settings(self, ts, t):

    t0 = self.volume_viewer_time(ts)
    if t0 is None or t0 == t:
      t0 = ts.last_shown_time

    if t0 != t:
      ts.copy_display_parameters(t0, t, self.normalize_thresholds)
      
    return t0

  # ---------------------------------------------------------------------------
  #
  def volume_viewer_time(self, ts):

    from VolumeViewer import active_volume
    v = active_volume()
    if v is None or not v.shown():
      t = None
    else:
      t = ts.volume_time(v)
    return t

  # ---------------------------------------------------------------------------
  #
  def show_time(self, ts, t):

    ts.show_time(t)
    self.cache_rendering(ts, t)

  # ---------------------------------------------------------------------------
  #
  def unshow_time(self, ts, t):

    cache_rendering = (self.rendering_cache_size > 1)
    ts.unshow_time(t, cache_rendering)
    if not cache_rendering:
      self.uncache_rendering(ts, t)

  # ---------------------------------------------------------------------------
  #
  def cache_rendering(self, ts, t):

    rtt = self.rendered_times_table
    if not (ts,t) in rtt:
      rtt[(ts,t)] = 1
      self.rendered_times.append((ts,t))
    self.trim_rendering_cache()

  # ---------------------------------------------------------------------------
  #
  def trim_rendering_cache(self):

    climit = self.rendering_cache_size
    rt = self.rendered_times
    rtt = self.rendered_times_table
    k = 0
    while len(rtt) > climit and k < len(rt):
      ts, t = rt[k]
      if ts.time_shown(t):
        k += 1
      else:
        ts.unshow_time(t, cache_rendering = False)
        del rtt[(ts,t)]
        del rt[k]
    
  # ---------------------------------------------------------------------------
  #
  def uncache_rendering(self, ts, t):

    rtt = self.rendered_times_table
    if (ts,t) in rtt:
      del rtt[(ts,t)]
      self.rendered_times.remove((ts,t))

  # ---------------------------------------------------------------------------
  #
  def marker_set(self):

    import VolumePath
    d = VolumePath.volume_path_dialog(create = False)
    if d is None:
      return None
    return d.active_marker_set

  # ---------------------------------------------------------------------------
  #
  def update_marker_display(self, mset = None):

    if mset is None:
      mset = self.marker_set()
      if mset is None:
        return

    fmin, fmax = self.marker_frame_range()
    if fmin is None or fmax is None:
      return

    mset.show_model(True)
    mir = set(markers_in_range(mset.markers(), fmin, fmax))
    for m in mset.markers():
      m.show(m in mir)
        
  # ---------------------------------------------------------------------------
  #
  def current_markers_and_links(self):

    mset = self.marker_set()
    if mset == None:
      return [], []

    t = self.current_time
    if t is None:
      return [], []

    mlist = markers_in_range(mset.markers(), t, t)
    mir = set(mlist)
    llist = [l for l in mset.links() if l.marker1 in mir and l.marker2 in mir]

    return mlist, llist
        
  # ---------------------------------------------------------------------------
  #
  def marker_frame_range(self):

    t = self.current_time
    if t is None:
      return None, None
    from CGLtk.Hybrid import integer_variable_value
    fmin = t - self.preceding_marker_frames
    fmax = t + self.following_marker_frames
    return fmin, fmax
    
  # ---------------------------------------------------------------------------
  #
  def update_color_zone(self):

    t = self.current_time
    if t is None:
      return

    tslist = self.series
    tslist = [ts for ts in tslist if not ts.surface_model(t) is None]

    for ts in tslist:
      r = self.color_range
      if not r is None:
	mlist, llist = self.current_markers_and_links()
	if mlist or llist:
	  atoms = [m.atom for m in mlist]
	  bonds = [l.bond for l in llist]
	  model = ts.surface_model(t)
	  xform_to_surface = model.openState.xform.inverse()
	  from ColorZone import points_and_colors, color_zone
	  points, point_colors = points_and_colors(atoms, bonds,
						   xform_to_surface)
	  if hasattr(model, 'series_zone_coloring'):
	    zp, zpc, zr = model.series_zone_coloring
	    from numpy import all
	    if all(zp == points) and all(zpc == point_colors) and zr == r:
	      return        # No change in coloring.
	  model.series_zone_coloring = (points, point_colors, r)
	  color_zone(model, points, point_colors, r, auto_update = True)
      else:
	for t in range(ts.number_of_times()):
	  model = ts.surface_model(t)
	  if model and hasattr(model, 'series_zone_coloring'):
	    from ColorZone import uncolor_zone
	    uncolor_zone(model)
	    delattr(model, 'series_zone_coloring')
      
  # ---------------------------------------------------------------------------
  #
  def update_volume_dialog(self, ts, t, delay_seconds = 1):

    tid = self.timer_id
    import chimera
    if delay_seconds == 0:
      ts.show_time_in_volume_dialog(t)
      if ts in tid:
        del tid[ts]
    elif not chimera.nogui:
      from chimera.tkgui import app
      if ts in tid:
        app.after_cancel(tid[ts])
      delay_msec = 1000 * delay_seconds
      tid[ts] = app.after(delay_msec, self.update_volume_dialog, ts, t, 0)

# -----------------------------------------------------------------------------
#
def markers_in_range(markers, imin, imax):

  mir = []
  for m in markers:
    if hasattr(m, 'extra_attributes') and 'frame' in m.extra_attributes:
      f = m.extra_attributes['frame']
    else:
      f = m.note_text
    if isinstance(f, basestring):
      try:
        f = int(f)
      except:
        f = None
    if f is not None and f >= imin and f <= imax:
      mir.append(m)

  return mir
