# -----------------------------------------------------------------------------
# Save and restore surface capping state.
#
  
# -----------------------------------------------------------------------------
#
def save_capper_state(file):

  import gui
  capper_dialog = gui.capper_dialog(create = False)
  if capper_dialog:
    ds = Capper_Dialog_State()
    ds.state_from_dialog(capper_dialog)
    from SessionUtil import objecttree
    dst = objecttree.instance_tree_to_basic_tree(ds)

    file.write('\n')
    file.write('def restore_surface_capping():\n')
    file.write(' capper_dialog_state = \\\n')
    objecttree.write_basic_tree(dst, file, indent = '  ')
    file.write('\n')
    file.write(' import SurfaceCap.session\n')
    file.write(' SurfaceCap.session.restore_capper_dialog_state(capper_dialog_state)\n')
    file.write('\n')
    file.write('try:\n')
    file.write(' restore_surface_capping()\n')
    file.write('except:\n')
    file.write(" reportRestoreError('Error restoring surface capping')\n")
    file.write('\n')

  save_capper_attributes(file)

# -----------------------------------------------------------------------------
#
def save_capper_attributes(file):

  import surfcaps
  capper = surfcaps.capper(create = False)
  if capper:
    ca = Caps_State()
    ca.state_from_capper(capper)
    from SessionUtil import objecttree
    cas = objecttree.instance_tree_to_basic_tree(ca)
    file.write('\n')
    file.write('def restore_cap_attributes():\n')
    file.write(' cap_attributes = \\\n')
    objecttree.write_basic_tree(cas, file, indent = '  ')
    file.write('\n')
    file.write(' import SurfaceCap.session\n')
    file.write(' SurfaceCap.session.restore_cap_attributes(cap_attributes)\n')
    file.write('registerAfterModelsCB(restore_cap_attributes)\n')
    file.write('\n')
  
# -----------------------------------------------------------------------------
#
def restore_capper_dialog_state(capper_dialog_basic_state):

  classes = (
    Capper_Dialog_State,
    )
  name_to_class = {}
  for c in classes:
    name_to_class[c.__name__] = c

  from SessionUtil import objecttree
  s = objecttree.basic_tree_to_instance_tree(capper_dialog_basic_state,
                                             name_to_class)

  import SurfaceCap.gui
  d = SurfaceCap.gui.capper_dialog(create = True)
  s.restore_state(d)

# -----------------------------------------------------------------------------
# This function name is needed for restoring older sessions.
#
restore_capper_state = restore_capper_dialog_state
  
# -----------------------------------------------------------------------------
#
def restore_cap_attributes(cap_attributes_basic_state):

  classes = (
    Caps_State,
    Model_Capper_State,
    )
  name_to_class = {}
  for c in classes:
    name_to_class[c.__name__] = c

  from SessionUtil import objecttree
  s = objecttree.basic_tree_to_instance_tree(cap_attributes_basic_state,
                                             name_to_class)
  import surfcaps
  s.restore_state(surfcaps.capper())

# -----------------------------------------------------------------------------
#
class Capper_Dialog_State:

  version = 1
  
  state_attributes = ('is_visible',
                      'geometry',
		      'show_caps',
		      'color_caps',
		      'cap_rgba',
		      'cap_style',
		      'subdivision_factor',
                      'cap_offset',
		      'version',
                      )
  
  # ---------------------------------------------------------------------------
  #
  def state_from_dialog(self, capper_dialog):

    d = capper_dialog

    self.is_visible = d.isVisible()
    t = d.uiMaster().winfo_toplevel()
    self.geometry = t.wm_geometry()

    self.show_caps = d.show_caps.get()
    self.color_caps = d.use_cap_color.get()
    self.cap_rgba = d.cap_color.rgba
    self.cap_style = d.cap_style.get()
    self.subdivision_factor = d.subdivision_factor.get()
    self.cap_offset = d.cap_offset.get()

  # ---------------------------------------------------------------------------
  #
  def restore_state(self, capper_dialog):

    d = capper_dialog
    if self.is_visible:
      d.enter()

    t = d.uiMaster().winfo_toplevel()
    t.wm_geometry(self.geometry)
    t.wm_geometry('')		# restore standard size

    d.show_caps.set(self.show_caps, invoke_callbacks = False)
    d.use_cap_color.set(self.color_caps, invoke_callbacks = False)
    d.cap_color.showColor(self.cap_rgba, doCallback = False)
    d.cap_style.set(self.cap_style, invoke_callbacks = 0)
    d.subdivision_factor.set(self.subdivision_factor, invoke_callbacks = 0)
    d.cap_offset.set(self.cap_offset, invoke_callbacks = 0)

    d.settings_changed_cb()

# -----------------------------------------------------------------------------
# Save attributes like color and display style for caps.
#
class Caps_State:

  version = 1
  
  state_attributes = ('shown',
                      'cap_color',
                      'mesh_style',
                      'subdivision_factor',
                      'default_cap_offset',
                      'cap_offset',
                      'cap_attributes',
		      'version',
                      )
  
  # ---------------------------------------------------------------------------
  #
  def state_from_capper(self, capper):

    c = capper

    self.shown = c.caps_shown()
    self.cap_color = c.cap_color
    self.mesh_style = c.mesh_style
    self.subdivision_factor = c.subdivision_factor
    self.default_cap_offset = c.default_cap_offset
    self.cap_offset = c.cap_offset

    ca = []
    import surfcaps
    for s in surfcaps.capped_surfaces():
      mcs = Model_Capper_State()
      mcs.state_from_model_capper(surfcaps.model_capper(s))
      ca.append(mcs)
    self.cap_attributes = ca

  # ---------------------------------------------------------------------------
  #
  def restore_state(self, capper):

    c = capper

    c.cap_color = self.cap_color
    c.mesh_style = self.mesh_style
    c.subdivision_factor = self.subdivision_factor
    c.default_cap_offset = self.default_cap_offset
    c.cap_offset = self.cap_offset
    for cas in self.cap_attributes:
      cas.restore_state()

    if hasattr(self, 'shown'):
      if self.shown:
        c.show_caps()
      else:
        c.unshow_caps()

# -----------------------------------------------------------------------------
# Save attributes like color and display style for caps.
#
class Model_Capper_State:

  version = 1
  
  state_attributes = ('surface',
                      'cap_color',
                      'display_style',
		      'version',
                      )
  
  # ---------------------------------------------------------------------------
  # Can only handle a single cap color and single display style because
  # there is no way to distinguish different cap pieces on restore.
  #
  def state_from_model_capper(self, mc):

    s = mc.model
    self.surface = (s.id, s.subid)
    cplist = mc.cap_pieces()
    cs = set(tuple(p.color) for p in cplist)
    self.cap_color = cs.pop() if len(cs) == 1 else None
    ds = set(p.displayStyle for p in cplist)
    self.display_style = ds.pop() if len(ds) == 1 else None

  # ---------------------------------------------------------------------------
  #
  def restore_state(self):

    if self.cap_color is None and self.display_style is None:
      return
    
    id, subid = self.surface
    from SimpleSession import modelMap
    from _surface import SurfaceModel
    from surfcaps import model_capper
    slist = [s for s in modelMap.get((id, subid), [])
             if isinstance(s, SurfaceModel)]
    if len(slist) != 1:
      from chimera import replyobj
      replyobj.warning('Could not restore surface cap on surface model\n'
                       'with id %d.%d because %d surfaces have that id.\n'
                       % (id, subid, len(slist)))
      return
    s = slist[0]
    mc = model_capper(s)
    if mc:
      cplist = mc.cap_pieces()
      c, ds = self.cap_color, self.display_style
      if not c is None:
        mc.restore_color = c
        for p in cplist:
          p.color = c
      if not ds is None:
        mc.restore_style = ds
        for p in cplist:
          p.displayStyle = ds
