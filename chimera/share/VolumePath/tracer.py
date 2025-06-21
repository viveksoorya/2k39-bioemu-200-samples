# -----------------------------------------------------------------------------
#
def volume_maxima(win_x, win_y, vlist):
    
    hits = []
    for v in vlist:
        if not v.shown():
            continue
        s, no_slice_warning = data_slice(win_x, win_y, v)
        if s is None:
            continue
        t_max, v_max, trace = s.first_maximum_above_threshold()
        if t_max is None:
            continue
        from Matrix import linear_combination, xform_xyz
        vxyz = linear_combination(1-t_max, s.xyz_in, t_max, s.xyz_out)
        xyz = xform_xyz(vxyz, v.model_transform())
        hits.append((xyz,v))
    return hits

# -----------------------------------------------------------------------------
#
def volume_plane_intercepts(win_x, win_y, vlist):
    
    hits = []
    for v in vlist:
        if not v.shown():
            continue
        plane = (v.single_plane() or
                 v.showing_orthoplanes() or
                 v.showing_box_faces())
        if not plane:
            continue
        s, no_slice_warning = data_slice(win_x, win_y, v)
        if s is None:
            continue
        from Matrix import linear_combination, xform_xyz
        vxyz = linear_combination(.5, s.xyz_in, .5, s.xyz_out)
        xyz = xform_xyz(vxyz, v.model_transform())
        hits.append((xyz,v))
    return hits

# -----------------------------------------------------------------------------
#
def surface_intercepts(win_x, win_y, surfaces):

    hits = []
    from VolumeViewer import slice
    xyz_in, xyz_out = slice.clip_plane_points(win_x, win_y)
    for surf in surfaces:
        if not surf.display:
            continue
        import PickBlobs
        f, p, tri = PickBlobs.surface_intercept(surf, xyz_in, xyz_out)
        if not f is None:
            import Matrix
            xyz = Matrix.linear_combination((1.0-f), xyz_in, f, xyz_out)
            hits.append((xyz, surf))
    return hits

# -----------------------------------------------------------------------------
#
def data_slice(win_x, win_y, v):

  if not v.shown():
    return None, 'Volume not shown'

  from VolumeViewer import slice
  if v.showing_orthoplanes() or v.showing_box_faces():
    xyz_in = xyz_out = slice.face_intercept_point(v, win_x, win_y)
  else:
    xyz_in, xyz_out = slice.volume_segment(v, win_x, win_y)

  if xyz_in is None or xyz_out is None:
    return None, 'No intersection with volume'

  slice = Slice(v, xyz_in, xyz_out)

  return slice, ''

# -----------------------------------------------------------------------------
# Graph the data values along a line passing through a volume on a Tkinter
# canvas.  The volume data may have multiple components.  Each component is
# graphed using a Trace object.
#
class Slice:

  def __init__(self, data_region, xyz_in, xyz_out):

    self.data_region = data_region
    self.xyz_in = xyz_in
    self.xyz_out = xyz_out

    self.canvas = None
    self.graph_width = None

    vdata = Visible_Data(self.data_region)
    t = Trace(vdata, self.xyz_in, self.xyz_out)
    self.traces = [t]

  # ---------------------------------------------------------------------------
  #
  def global_z(self, f):

    import Matrix
    vxyz = Matrix.linear_combination(1-f, self.xyz_in, f, self.xyz_out)
    xyz = Matrix.xform_xyz(vxyz, self.data_region.model_transform())
    return xyz[2]
  
  # ---------------------------------------------------------------------------
  #
  def show_slice_graph(self, canvas, fmin, fmax, use_volume_colors):

    c = canvas
    self.canvas = c
    self.graph_width = w = c.winfo_width()

    h = c.winfo_height()
    ypad = 3                                                     # pixels
    ymin = ypad
    ymax = max(ypad, h - ypad)

    for t in self.traces:
        t.draw_trace(canvas, fmin, fmax, ymin, ymax, use_volume_colors)

  # ---------------------------------------------------------------------------
  #
  def reset_thresholds(self):

    d = self.data_region.data
    if hasattr(d, 'volume_path_threshold'):
      delattr(d, 'volume_path_threshold')
    self.redraw_threshold_lines()

  # ---------------------------------------------------------------------------
  #
  def redraw_threshold_lines(self):

    for t in self.traces:
      t.redraw_threshold_line()

  # ---------------------------------------------------------------------------
  #
  def first_maximum_above_threshold(self):

    t_max = None
    v_max = None
    trace_max = None
    for trace in self.traces:
      t, v = trace.first_maximum_above_threshold()
      if t != None and (t_max == None or t < t_max):
        t_max = t
        v_max = v
        trace_max = trace
    return t_max, v_max, trace_max

# -----------------------------------------------------------------------------
# Graph the data values along a line passing through a volume data set.
#
class Trace:

  def __init__(self, visible_data, xyz_in, xyz_out):

    self.visible_data = visible_data

    self.canvas = None
    self.canvas_y_range = (None, None)
    self.use_volume_color = False
    self.plot_scale = (None, None)
    
    v = visible_data.data_region
    from VolumeViewer.slice import slice_data_values
    self.trace = slice_data_values(v, xyz_in, xyz_out)
    threshold = visible_data.threshold()
    self.value_range = self.calculate_value_range(threshold)

  # ---------------------------------------------------------------------------
  #
  def draw_trace(self, canvas, fmin, fmax, ymin, ymax, use_volume_color):

    self.canvas = canvas
    self.canvas_y_range = (ymin, ymax)

    self.plot_scale = self.calculate_plot_scale()

    self.use_volume_color = use_volume_color
    color = self.volume_color()
    xy_values = self.trace_values_to_canvas_xy(self.trace, fmin, fmax)
    canvas.create_line(xy_values, fill = color)

    threshold = self.visible_data.threshold()
    self.threshold_line_id = (None if threshold is None else
                              self.plot_threshold_line(threshold, color))

  # ---------------------------------------------------------------------------
  #
  def calculate_value_range(self, threshold):
    
    values = map(lambda tv: tv[1], self.trace)
    min_value = min(values)
    max_value = max(values)

    if threshold != None:
      min_value = min(min_value, threshold)
      max_value = max(max_value, threshold)
    value_range = max_value - min_value

    return (min_value, max_value)

  # ---------------------------------------------------------------------------
  #
  def calculate_plot_scale(self):

    w = self.canvas.winfo_width()
    x_scale = w
    vrange = self.value_range[1] - self.value_range[0]
    if vrange == 0:
      y_scale = 1
    else:
      ymin, ymax = self.canvas_y_range
      y_scale = max(1, ymax - ymin) / float(vrange)

    return (x_scale, y_scale)

  # ---------------------------------------------------------------------------
  #
  def trace_values_to_canvas_xy(self, tvlist, fmin, fmax):

    x_scale, y_scale = self.plot_scale
    y0 = self.canvas_y_range[1]
    v0 = self.value_range[0]
    return [(x_scale * (fmin + t*(fmax-fmin)), y0 - y_scale * (v - v0))
            for t, v in tvlist]

  # ---------------------------------------------------------------------------
  #
  def volume_color(self):

    if not self.use_volume_color:
      return 'black'
    
    color_256 = lambda c: min(255, max(0, int(256*c)))
    rgb_256 = map(color_256, self.visible_data.volume_rgba()[:3])
    color = '#%02x%02x%02x' % tuple(rgb_256)
    return color

  # ---------------------------------------------------------------------------
  #
  def plot_threshold_line(self, threshold, color):

    hline = ((0,threshold),(1,threshold))
    thresh_xy = self.trace_values_to_canvas_xy(hline, 0, 1)
    if self.visible_data.using_displayed_threshold():
      dash_pattern = '.'
    else:
      dash_pattern = '-'
    c = self.canvas
    id = c.create_line(thresh_xy, fill = color, dash = dash_pattern)
    c.tag_bind(id, "<Button1-Motion>", self.move_line_cb, add = 1)
    return id

  # ---------------------------------------------------------------------------
  #
  def redraw_threshold_line(self):

    color = self.volume_color()
    threshold = self.visible_data.threshold()
    if threshold != None:
      if self.threshold_line_id != None:
        self.canvas.delete(self.threshold_line_id)
      self.threshold_line_id = self.plot_threshold_line(threshold, color)

  # ---------------------------------------------------------------------------
  #
  def move_line_cb(self, event):

    line_id = self.threshold_line_id
    ymin, ymax = self.canvas_y_range
    min_value, max_value = self.value_range
    
    y = event.y
    c = self.canvas
    w = c.winfo_width()
    c.coords(line_id, 0, y, w, y)
    
    if ymax > ymin:
      f = float(y - ymin) / (ymax - ymin)
      threshold = (1-f) * max_value + f * min_value
      self.visible_data.set_threshold(threshold)
      c.itemconfigure(line_id, dash = '-')

  # ---------------------------------------------------------------------------
  #
  def first_maximum_above_threshold(self):

    thresh = self.visible_data.threshold()
    trace = self.trace
    n = len(trace)
    for k in range(n):
      t, v = trace[k]
      if v >= thresh:
        if ((k-1 < 0 or trace[k-1][1] < v) and
            (k+1 >= n or trace[k+1][1] <= v)):
          return t, v
    return None, None

# -----------------------------------------------------------------------------
# Return position and model with largest z value.
#
def closest_hit(hits):

    zmax = None
    closest = (None, None)
    for xyz, model in hits:
        if not xyz is None:
            z = xyz[2]
            if z > zmax or zmax is None:
                closest = (xyz, model)
                zmax = z
    return closest


# ---------------------------------------------------------------------------
# Find the closest displayed data color for the given data value.
# If no data value is given, use the color for the lowest threshold.
# Otherwise use the color of the first surface level below the data value
# if surfaces are shown.  If not level is below the data level use the
# color of the lowest surface.  For the interpolated solid use the
# interpolated color for the data component, or if the data value
# is outside the threshold range, use the closest endpoint color.
#
def volume_rgba(v, data_value = None):

  if v.representation in ('surface', 'mesh') and v.surface_levels:
    tclist = zip(v.surface_levels, v.surface_colors)
    tclist.sort()
    if data_value != None:
      tclower = filter(lambda tc, v=data_value: tc[0] <= v , tclist)
      if tclower:
        rgba = tclower[-1][1]
      else:
        rgba = tclist[-1][1]
    else:
      rgba = tclist[0][1]
  elif v.representation == 'solid' and v.solid and v.solid_levels:
    tclist = [(tf[0],c) for tf,c in zip(v.solid_levels, v.solid_colors)]
    tclist.sort()
    if data_value != None:
      if data_value <= tclist[0][0]:
        rgba = tclist[0][1]
      elif data_value >= tclist[-1][0]:
        rgba = tclist[-1][1]
      else:
        k = 1
        while tclist[k][0] <= data_value: 
          k = k + 1
        d0, rgba0 = tclist[k-1]
        d1, rgba1 = tclist[k]
        f = (data_value - d0) / (d1 - d0)
        rgba = map(lambda c0, c1, f=f: (1-f)*c0 + f*c1, rgba0, rgba1)
    else:
      rgba = tclist[-1][1]
  else:
    rgba = (0,0,0,0)

  return rgba

# -----------------------------------------------------------------------------
#
def visible_data_components(v):

  return [Visible_Data(v)] if v.shown() else []

# -----------------------------------------------------------------------------
#
class Visible_Data:

  def __init__(self, data_region):

    self.data_region = data_region

  # ---------------------------------------------------------------------------
  #
  def interpolated_value(self, xyz):

    vertex_xform = None
    dr = self.data_region
    values = dr.interpolated_values([xyz], vertex_xform, subregion = None)
    v = values[0]
    return v
  
  # ---------------------------------------------------------------------------
  #
  def threshold(self):

    data = self.data_region.data
    if hasattr(data, 'volume_path_threshold'):
      return data.volume_path_threshold

    threshold = None
    dr = self.data_region
    rep = dr.representation
    if rep in ('surface', 'mesh'):
      if dr.surface_levels:
        threshold = min(dr.surface_levels)
    elif rep == 'solid':
      levels = filter(lambda sl: sl[1] > 0, dr.solid_levels)
      if levels:
        threshold = min(levels)[0]

    return threshold

  # ---------------------------------------------------------------------------
  #
  def set_threshold(self, threshold):

    self.data_region.data.volume_path_threshold = threshold

  # ---------------------------------------------------------------------------
  #
  def using_displayed_threshold(self):

    return not hasattr(self.data_region.data, 'volume_path_threshold')

  # ---------------------------------------------------------------------------
  # Find the closest displayed data color for the given data value.
  # If no data value is given, use the color for the lowest threshold.
  # Otherwise use the color of the first surface level below the data value
  # if surfaces are shown.  If not level is below the data level use the
  # color of the lowest surface.  For the interpolated solid use the
  # interpolated color for the data component, or if the data value
  # is outside the threshold range, use the closest endpoint color.
  #
  def volume_rgba(self, data_value = None):

    return volume_rgba(self.data_region, data_value)
