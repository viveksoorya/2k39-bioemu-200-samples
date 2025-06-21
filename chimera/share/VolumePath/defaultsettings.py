# -----------------------------------------------------------------------------
# Save and restore volume tracer default dialog settings.
#
# This should probably be unified with session saving, but is currently
# completely separate.
#
    
# ---------------------------------------------------------------------------
#
class Volume_Tracer_Default_Settings:

  def __init__(self):

    options = self.factory_defaults()
    from chimera import preferences
    self.saved_prefs = preferences.addCategory('Volume Tracer',
                                               preferences.HiddenCategory,
                                               optDict = options)
    self.current_prefs = options.copy()
    
  # ---------------------------------------------------------------------------
  #
  def factory_defaults(self):

    defaults = {
        'shown_panels': ('Marker set menu', 'Mouse button menu', 'Marker color and radius'),
        'use_mouse': False,
        'placement_button': 'middle',
        'place_markers_on_spots': True,
        'place_markers_on_planes': True,
        'place_markers_on_surfaces': False,
        'place_markers_outside_data': False,
        'place_markers_continuously': False,
        'marker_spacing': 10,
        'move_markers': False,
        'marker_matches_volume_color': False,
        'link_to_selected': False,
        'link_consecutive': False,
        'marker_color': (1,1,0,1),
        'marker_radius': None,
        'link_color': (1,1,0,1),
        'link_radius': None,
        'note_color': (1,1,1,1),
        'curve_radius': 0,
        'curve_band_length': 0,
        'curve_segment_subdivisions': 10,
        'slice_use_volume_colors': False,
        'show_slice_line': False,
        'slice_color': (1,1,1,1),
        'cap_ends': False,
    }
    return defaults

  # ---------------------------------------------------------------------------
  #
  def __getitem__(self, key):

    return self.current_prefs[key]

  # ---------------------------------------------------------------------------
  #
  def set_gui_to_defaults(self, dialog, option_settings = True,
                          panel_settings = True):

    d = dialog
    p = self.current_prefs

    if option_settings:
      mbp = d.mouse_button_panel
      mbp.use_mouse.set(p['use_mouse'])
      mbp.placement_button.variable.set(p['placement_button'],
                                        invoke_callbacks = False)

      d.place_markers_on_spots.set(p['place_markers_on_spots'],
                                     invoke_callbacks = False)
      d.place_markers_on_planes.set(p['place_markers_on_planes'],
                                      invoke_callbacks = False)
      d.place_markers_on_surfaces.set(p['place_markers_on_surfaces'],
                                        invoke_callbacks = False)
      d.place_markers_outside_data.set(p['place_markers_outside_data'],
                                         invoke_callbacks = False)
      d.place_markers_continuously.set(p['place_markers_continuously'],
                                         invoke_callbacks = False)
      d.mouse_mode_panel.marker_spacing.set(p['marker_spacing'],
                                            invoke_callbacks = False)
      d.move_markers.set(p['move_markers'], invoke_callbacks = False)
      d.marker_matches_volume_color.set(p['marker_matches_volume_color'],
                                          invoke_callbacks = False)
      d.link_to_selected.set(p['link_to_selected'], invoke_callbacks = False)
      d.link_consecutive.set(p['link_consecutive'])

      crp = d.color_radius_panel
      crp.marker_color.showColor(p['marker_color'], doCallback = False)
      r = '' if p['marker_radius'] is None else '%g' % p['marker_radius']
      crp.marker_radius_entry.set(r, invoke_callbacks = False)
      crp.link_color.showColor(p['link_color'], doCallback = False)
      r = '' if p['link_radius'] is None else '%g' % p['link_radius']
      crp.link_radius_entry.set(r, invoke_callbacks = False)
      
      d.note_panel.note_color.showColor(p['note_color'], doCallback = False)

      sp = d.spline_panel
      sp.curve_radius.set(p['curve_radius'], invoke_callbacks = False)
      sp.curve_band_length.set(p['curve_band_length'], invoke_callbacks = False)
      sp.curve_segment_subdivisions.set(p['curve_segment_subdivisions'],
                                        invoke_callbacks = False)

      slp = d.slice_panel
      slp.use_volume_colors.set(p['slice_use_volume_colors'],
                                invoke_callbacks = False)
      slp.show_slice_line.set(p['show_slice_line'], invoke_callbacks = False)
      slp.slice_color.showColor(p['slice_color'], doCallback = False)

      d.surface_panel.cap_ends.set(p['cap_ends'], invoke_callbacks = False)

    if panel_settings:
      d.update_default_panels(p['shown_panels'])
      d.show_panels(p['shown_panels'])

  # ---------------------------------------------------------------------------
  #
  def set_defaults_from_gui(self, dialog, option_settings = True,
                            panel_settings = True):

    d = dialog
    p = self.current_prefs
    s = {}

    if option_settings:
      mbp = d.mouse_button_panel
      p['use_mouse'] = mbp.use_mouse.get()
      p['placement_button'] = mbp.placement_button.variable.get()

      p['place_markers_on_spots'] = d.place_markers_on_spots.get()
      p['place_markers_on_planes'] = d.place_markers_on_planes.get()
      p['place_markers_on_surfaces'] = d.place_markers_on_surfaces.get()
      p['place_markers_outside_data'] = d.place_markers_outside_data.get()
      p['place_markers_continuously'] = d.place_markers_continuously.get()
      p['marker_spacing'] = float_value(d.mouse_mode_panel.marker_spacing.get(),
                                        p['marker_spacing'])
      p['move_markers'] = d.move_markers.get()
      p['marker_matches_volume_color'] = d.marker_matches_volume_color.get()
      p['link_to_selected'] = d.link_to_selected.get()
      p['link_consecutive'] = d.link_consecutive.get()

      crp = d.color_radius_panel
      p['marker_color'] = crp.marker_color.rgba
      p['marker_radius'] = float_value(crp.marker_radius_entry.get(),
                                       p['marker_radius'])
      p['link_color'] = crp.link_color.rgba
      p['link_radius'] = float_value(crp.link_radius_entry.get(),
                                     p['link_radius'])
      
      p['note_color'] = d.note_panel.note_color.rgba

      sp = d.spline_panel
      p['curve_radius'] = float_value(sp.curve_radius.get(), p['curve_radius'])
      p['curve_band_length'] = float_value(sp.curve_band_length.get(),
                                           p['curve_band_length'])
      p['curve_segment_subdivisions'] = int_value(sp.curve_segment_subdivisions.get(), p['curve_segment_subdivisions'])

      slp = d.slice_panel
      p['slice_use_volume_colors'] = slp.use_volume_colors.get()
      p['show_slice_line'] = slp.show_slice_line.get()
      p['slice_color'] = slp.slice_color.rgba

      p['cap_ends'] = d.surface_panel.cap_ends.get()

    if panel_settings:
      s['shown_panels'] = [p.name for p in dialog.shown_panels()]

    self.current_prefs.update(s)

  # ---------------------------------------------------------------------------
  #
  def save_to_preferences_file(self, option_settings = True,
                               panel_settings = True):

    keys = []
    if option_settings:
      keys.extend(self.factory_defaults().keys())
      keys.remove('shown_panels')
    if panel_settings:
      keys.extend(['shown_panels'])

    s = self.saved_prefs
    p = self.current_prefs
    for key in keys:
      s.set(key, p[key], saveToFile = False)
    s.saveToFile()

  # ---------------------------------------------------------------------------
  #
  def restore_factory_defaults(self, dialog):

    options = self.factory_defaults()
    self.current_prefs = options.copy()
    self.saved_prefs.load(options.copy())
    self.set_gui_to_defaults(dialog)

# ---------------------------------------------------------------------------
#
def float_value(s, default = None):

  try:
    x = float(s)
  except ValueError:
    x = default
  return x

# ---------------------------------------------------------------------------
#
def int_value(s, default = None):

  try:
    x = int(s)
  except ValueError:
    x = default
  return x
  
