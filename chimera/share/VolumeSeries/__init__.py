# -----------------------------------------------------------------------------
#
class Volume_Series:

  def __init__(self, name, data_sets = None, volumes = None):

    self.name = name

    if volumes is None:
      from VolumeViewer import volume_from_grid_data
      vlist = [volume_from_grid_data(g, show_data = (i==0), show_dialog = False)
               for i,g in enumerate(data_sets)]
    else:
      vlist = volumes
    self.data_regions = vlist
    self.data_sets = [v.data for v in vlist]

    from chimera import addModelClosedCallback
    for t,v in enumerate(vlist):
      v.volume_series_time = t
      addModelClosedCallback(v, self.volume_closed)

    self.surface_level_ranks = []  # Cached for normalization calculation
    self.solid_level_ranks = []  # Cached for normalization calculation

  # ---------------------------------------------------------------------------
  #
  def number_of_times(self):

    return len(self.data_sets)
    
  # ---------------------------------------------------------------------------
  #
  def volume_time(self, v):

    if hasattr(v, 'volume_series_time'):
      t = v.volume_series_time
      # Make sure it belongs volume belongs to this series.
      vs = self.data_regions
      if t < len(vs) and vs[t] == v:
        return t
    return None
    
  # ---------------------------------------------------------------------------
  #
  def remove_from_volume_viewer(self):

    import chimera
    chimera.openModels.close([v for v in self.data_regions if not v is None])

  # ---------------------------------------------------------------------------
  #
  def volume_closed(self, v):

    t = v.volume_series_time
    self.data_sets[t] = None
    self.data_regions[t] = None

  # ---------------------------------------------------------------------------
  #
  def is_volume_closed(self, t):

    return self.data_regions[t] == None

  # ---------------------------------------------------------------------------
  #
  def show_time(self, time):

    v = self.data_regions[time]
    if v:
      v.show()

  # ---------------------------------------------------------------------------
  #
  def unshow_time(self, time, cache_rendering):

    v = self.data_regions[time]
    if v is None:
      return

    if v.representation == 'solid' and cache_rendering:
      vs = v.solid_model()
      if vs:
        vs.display = False
    else:
      v.show(show = False)

    if not cache_rendering:
      v.remove_surfaces()
      v.close_solid()

  # ---------------------------------------------------------------------------
  #
  def time_shown(self, time):

    dr = self.data_regions[time]
    shown = (dr and len(filter(lambda m: m.display, dr.models())) > 0)
    return shown

  # ---------------------------------------------------------------------------
  #
  def surface_model(self, time):

    return self.data_regions[time] if time >= 0 and time < len(self.data_regions) else None

  # ---------------------------------------------------------------------------
  #
  def show_time_in_volume_dialog(self, time):

    dr = self.data_regions[time]
    if dr == None:
      return

    from VolumeViewer import set_active_volume
    set_active_volume(dr)

  # ---------------------------------------------------------------------------
  #
  def copy_display_parameters(self, t1, t2, normalize_thresholds = False):

    dr1 = self.data_regions[t1]
    dr2 = self.data_regions[t2]
    if dr1 == None or dr2 == None:
      return

    dr2.data.set_step(dr1.data.step)
    dr2.data.set_origin(dr1.data.origin)
    dr2.copy_settings_from(dr1, copy_xform = False)
    if normalize_thresholds:
      self.copy_threshold_rank_levels(dr1, dr2)

  # ---------------------------------------------------------------------------
  #
  def copy_threshold_rank_levels(self, v1, v2):

    levels, ranks = equivalent_rank_values(v1, v1.surface_levels,
                                           v2, v2.surface_levels,
                                           self.surface_level_ranks)
    v2.surface_levels = levels
    self.surface_level_ranks = ranks

    lev1 = [l for l,b in v1.solid_levels]
    lev2 = [l for l,b in v2.solid_levels]
    levels, ranks = equivalent_rank_values(v1, lev1, v2, lev2,
                                           self.solid_level_ranks)
    v2.solid_levels = zip(levels, [b for lev,b in v1.solid_levels])
    self.solid_level_ranks = ranks

# -----------------------------------------------------------------------------
# Avoid creep due to rank -> value and value -> rank not being strict inverses
# by using passed in ranks if they match given values.
#
def equivalent_rank_values(v1, values1, v2, values2, ranks):

  ms1 = v1.matrix_value_statistics()
  ms2 = v2.matrix_value_statistics()
  rlev = [ms1.rank_data_value(r) for r in ranks]
  if rlev != values1:
    ranks = [ms1.data_value_rank(lev) for lev in values1]
  if [ms2.data_value_rank(lev) for lev in values2] != ranks:
    values2 = [ms2.rank_data_value(r) for r in ranks]
  return values2, ranks
