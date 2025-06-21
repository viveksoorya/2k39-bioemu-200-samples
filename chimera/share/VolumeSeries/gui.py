# -----------------------------------------------------------------------------
# Dialog for controlling display of volume series.
#

import chimera
from chimera.baseDialog import ModelessDialog
import VolumeSeries

# -----------------------------------------------------------------------------
#
class Volume_Series_Dialog(ModelessDialog):

  title = 'Volume Series'
  name = 'volume series'
  buttons = ('Open...', 'Close Series', 'Close',)
  help = 'ContributedSoftware/volseries/volseries.html'
  
  def fillInUI(self, parent):

    self.series = []
    import play
    self.player = play.Play_Series(time_step_cb = self.time_step_cb,
                                   loop = True)
    # TODO: Need to set player parameters and update them as GUI settings change
    self.new_marker_handler = None

    self.toplevel_widget = parent.winfo_toplevel()
    self.toplevel_widget.withdraw()

    parent.columnconfigure(0, weight=1)         # Allow scalebar to expand.
    
    row = 0

    import Tkinter
    from CGLtk import Hybrid
    from chimera import widgets

    dm = Hybrid.Option_Menu(parent, 'Data ', 'All')
    dm.frame.grid(row = row, column = 0, sticky = 'w')
    row = row + 1
    dm.add_callback(self.series_menu_cb)
    self.series_menu = dm

    tf = Tkinter.Frame(parent)
    tf.grid(row = row, column = 0, sticky = 'ew')
    tf.columnconfigure(0, weight=1)         # Allow scalebar to expand.
    row = row + 1
    
    ts = Hybrid.Scale(tf, 'Time ', 0, 100, 1, 0)
    ts.frame.grid(row = 0, column = 0, sticky = 'ew')
    ts.callback(self.time_changed_cb)
    ts.entry.bind('<KeyPress-Return>', self.time_changed_cb)
    self.time = ts

    pb = Tkinter.Button(tf, text = 'Play', command = self.play_stop_cb)
    pb.grid(row = 0, column = 1, sticky = 'w')
    self.play_stop_button = pb

    pd = Hybrid.Radiobutton_Row(parent, 'Play direction',
                                ('forward', 'backward', 'oscillate'),
                                self.update_settings_cb)
    pd.frame.grid(row = row, column = 0, sticky = 'w')
    row = row + 1
    self.play_direction = pdv = pd.variable
    pdv.add_callback(self.update_settings_cb)
    
    ps = Hybrid.Checkbutton_Entries(parent, False, 'Maximum playback speed',
                                    (2, '5'), ' steps per second')
    ps.frame.grid(row = row, column = 0, sticky = 'w')
    row = row + 1
    self.limit_frame_rate = lfr = ps.variables[0]
    self.maximum_frame_rate = mfr = ps.variables[1]
    lfr.add_callback(self.update_settings_cb)
    mfr.add_callback(self.update_settings_cb)

    nt = Hybrid.Checkbutton(parent, 'Normalize threshold levels', 0)
    nt.button.grid(row = row, column = 0, sticky = 'w')
    row = row + 1
    self.normalize_thresholds = ntv = nt.variable
    ntv.add_callback(self.update_settings_cb)

    cr = Hybrid.Checkbutton_Entries(parent, False, 'Cache', (3, '30'),
                                    ' renderings')
    cr.frame.grid(row = row, column = 0, sticky = 'w')
    row = row + 1
    self.cache_renderings = crv = cr.variables[0]
    crv.add_callback(self.update_settings_cb)
    self.rendering_cache_limit = rcl = cr.variables[1]
    rcl.add_callback(self.update_settings_cb)
    cr.entries[0].bind('<KeyPress-Return>', self.update_settings_cb)
    
    vc = Tkinter.Frame(parent)
    vc.grid(row = row, column = 0, sticky = 'w')
    row = row + 1

    from VolumeData import data_cache
    csize = data_cache.size / (2 ** 20)
    if csize == 0:
      csize = ''
    cs = Hybrid.Entry(vc, 'Data cache size (Mb)', 4, csize)
    cs.frame.grid(row = 0, column = 0, sticky = 'w')
    self.data_cache_size = cs.variable
    cs.entry.bind('<KeyPress-Return>', self.cache_size_cb)

    cu = Tkinter.Button(vc, text = 'Current use', command = self.cache_use_cb)
    cu.grid(row = 0, column = 1, sticky = 'w')

    sm = Hybrid.Checkbutton_Entries(parent, False, 'Show markers', (2, '0'),
                                    'earlier and', (2, '0'), ' later times')
    sm.frame.grid(row = row, column = 0, sticky = 'w')
    row = row + 1
    self.show_markers = smv = sm.variables[0]
    smv.add_callback(self.show_markers_cb)
    self.preceding_marker_frames = sm.variables[1]
    sm.entries[0].bind('<KeyPress-Return>', self.show_markers_cb)
    self.following_marker_frames = sm.variables[2]
    sm.entries[1].bind('<KeyPress-Return>', self.show_markers_cb)

    cz = Hybrid.Checkbutton_Entries(parent, False, 'Color zone around markers, range', (4, '1.0'))
    cz.frame.grid(row = row, column = 0, sticky = 'w')
    row = row + 1
    self.color_zone = czv = cz.variables[0]
    czv.add_callback(self.update_settings_cb)
    self.color_range = cz.variables[1]
    cz.entries[0].bind('<KeyPress-Return>', self.update_settings_cb)
    
    #
    # Specify a label width so dialog is not resized for long messages.
    #
    msg = Tkinter.Label(parent, width = 40, anchor = 'w', justify = 'left')
    msg.grid(row = row, column = 0, sticky = 'ew')
    row = row + 1
    self.message_label = msg

    chimera.triggers.addHandler(chimera.CLOSE_SESSION,
				self.close_session_cb, None)

    pdv.set('forward')
    self.update_settings_cb()
    
  # ---------------------------------------------------------------------------
  #
  def message(self, text):

    self.message_label['text'] = text
    self.message_label.update_idletasks()
    
  # ---------------------------------------------------------------------------
  #
  def series_menu_cb(self, text = None):

    tslist = self.chosen_series()
    if len(tslist) == 0:
      return

    self.time.set_range(0, tslist[0].number_of_times()-1, 1)
    self.update_settings_cb()

  # ---------------------------------------------------------------------------
  #
  def Open(self):

    self.open_cb()

  # ---------------------------------------------------------------------------
  #
  def open_cb(self):

    import openseries
    openseries.open_series_files()
      
  # ---------------------------------------------------------------------------
  #
  def CloseSeries(self):

    for ts in self.chosen_series():
      self.close_series(ts)
      
  # ---------------------------------------------------------------------------
  #
  def close_series(self, ts, close_volumes = True):

    if close_volumes:
      ts.remove_from_volume_viewer()

    i = self.series.index(ts)
    self.series_menu.remove_entry(i+1)

    del self.series[i]

    # Set menu to an open series.
    if len(self.chosen_series()) == 0:
      if self.series:
        ts_name = self.series[0].menu_name
      else:
        ts_name = 'All'
      self.series_menu.variable.set(ts_name)
    
  # ---------------------------------------------------------------------------
  #
  def close_session_cb(self, trigger, a1, a2):

    for s in list(self.series):
      self.close_series(s, close_volumes = False)

  # ---------------------------------------------------------------------------
  #
  def update_settings_cb(self, event=None):

    p = self.player

    p.series = self.chosen_series()
    p.current_time = self.time_from_gui()
    p.set_play_direction(self.play_direction.get())

    from CGLtk.Hybrid import float_variable_value, integer_variable_value
    p.max_frame_rate = (float_variable_value(self.maximum_frame_rate, None)
                        if self.limit_frame_rate.get() else None)

    p.normalize_thresholds = self.normalize_thresholds.get()
    
    rcl = integer_variable_value(self.rendering_cache_limit, 1)
    p.rendering_cache_size = rcl if self.cache_renderings.get() else 1
    p.trim_rendering_cache()

    p.show_markers = self.show_markers.get()
    pmf = integer_variable_value(self.preceding_marker_frames, 0)
    p.preceding_marker_frames = pmf
    fmf = integer_variable_value(self.following_marker_frames, 1)
    p.following_marker_frames = fmf
    p.update_marker_display()

    p.color_range = (float_variable_value(self.color_range, 0)
                     if self.color_zone.get() else None)
    p.update_color_zone()
    
  # ---------------------------------------------------------------------------
  #
  def time_changed_cb(self, event = None):

    t = self.time_from_gui()
    if t is None:
      return

    self.player.change_time(t)

  # ---------------------------------------------------------------------------
  #
  def show_markers_cb(self, event = None):

    show = self.show_markers.get()
    mset = self.player.marker_set()
    if show:
      if mset:
        self.player.update_marker_display(mset)
      else:
        self.show_path_tracer_dialog()
    elif mset:
      mset.show_markers(False)
        
    self.register_new_marker_handler(show)
    self.update_settings_cb()

  # ---------------------------------------------------------------------------
  #
  def show_path_tracer_dialog(self):

    import VolumePath
    VolumePath.show_volume_path_dialog()
    if self.player.marker_set() is None and self.series:
      VolumePath.Marker_Set(self.series[0].menu_name + ' markers')

  # ---------------------------------------------------------------------------
  #
  def register_new_marker_handler(self, register):

    if register:
      if self.new_marker_handler == None:
        from chimera import triggers
        h = triggers.addHandler('Atom', self.new_marker_cb, None)
        self.new_marker_handler = h
    else:
      if self.new_marker_handler:
        from chimera import triggers
        triggers.deleteHandler('Atom', self.new_marker_handler)
        self.new_marker_handler = None
          
  # -------------------------------------------------------------------------
  # Add current time label to new markers.
  #
  def new_marker_cb(self, trigger, user_data, changes):

    t = self.time_from_gui()
    if t == None:
      return

    mset = self.player.marker_set()
    if mset == None:
      return
    
    for a in changes.created:
      m = mset.atom_marker(a)
      if m:
        if not m.note():
          m.set_note('%d' % t)
          m.show_note(False)
        if not hasattr(m, 'extra_attributes'):
          m.extra_attributes = {}
        if 'frame' not in m.extra_attributes:
          m.extra_attributes['frame'] = t
  
  # ---------------------------------------------------------------------------
  #
  def play_stop_cb(self):

    p = self.player
    b = self.play_stop_button
    if b['text'] == 'Play':
      self.update_settings_cb()
      p.play()
      b['text'] = 'Stop'
    else:
      p.stop()
      b['text'] = 'Play'
      
  # ---------------------------------------------------------------------------
  #
  def cache_size_cb(self, event):

    from CGLtk.Hybrid import float_variable_value
    size_mb = float_variable_value(self.data_cache_size, None)
    if size_mb:
      from VolumeData import data_cache
      data_cache.resize(size_mb * (2**20))

  # ---------------------------------------------------------------------------
  #
  def cache_use_cb(self):

    # Volume data cache size is not set until first volume is opened.
    # So update the value.
    from VolumeData import data_cache
    csize = data_cache.size / (2 ** 20)
    self.data_cache_size.set(csize, invoke_callbacks = False)

    from VolumeData import memoryuse
    memoryuse.show_memory_use_dialog()

  # ---------------------------------------------------------------------------
  #
  def time_step_cb(self, t):

    self.time.set_value(t, invoke_callbacks = False)
    
  # ---------------------------------------------------------------------------
  #
  def time_from_gui(self):
 
    time = self.time.value()
    if time == None:
      self.message('Time is set to a non-numeric value')
      return None
    else:
      self.message('')
    time = int(time)
    return time
    
  # ---------------------------------------------------------------------------
  #
  def add_volume_series(self, ts):

    ts.last_shown_time = 0

    mname = self.series_menu_name(ts.name)
    ts.menu_name = mname
    self.series.append(ts)
    sm = self.series_menu
    sm.add_entry(mname)
    sm.variable.set(mname)
      
  # ---------------------------------------------------------------------------
  # Choose unique menu name for series.
  #
  def series_menu_name(self, sname):

    mname = sname
    mnames = set([ts.menu_name for ts in self.series])
    suffix = 2
    while mname in mnames:
      mname = '%s %d' % (sname, suffix)
      suffix += 1
    return mname
      
  # ---------------------------------------------------------------------------
  #
  def chosen_series(self):

    sm = self.series_menu
    name = sm.variable.get()
    if name == 'All':
      return list(self.series)          # Copy the list.
    name_to_series = {}
    for ts in self.series:
      name_to_series[ts.menu_name] = ts
    if name and name in name_to_series:
      ts = [name_to_series[name]]
    else:
      ts = []
    return ts
  
# -----------------------------------------------------------------------------
#
def add_volume_series(ts):

    import gui
    d = gui.volume_series_dialog(create = True)
    d.add_volume_series(ts)
  
# -----------------------------------------------------------------------------
#
def volume_series_dialog(create = False):

  from chimera import dialogs
  return dialogs.find(Volume_Series_Dialog.name, create=create)
  
# -----------------------------------------------------------------------------
#
def show_volume_series_dialog():

  from chimera import dialogs
  return dialogs.display(Volume_Series_Dialog.name)

# -----------------------------------------------------------------------------
#
from chimera import dialogs
dialogs.register(Volume_Series_Dialog.name, Volume_Series_Dialog,
                 replace = True)
