# -----------------------------------------------------------------------------
# Dialog for coloring connected pieces of a surface chosen with mouse.
#

import chimera
from chimera.baseDialog import ModelessDialog

# -----------------------------------------------------------------------------
#
class Blob_Picker_Dialog(ModelessDialog):

  title = 'Measure and Color Blobs'
  name = 'measure and color blobs'
  buttons = ('Close',)
  help = 'ContributedSoftware/pickblobs/pickblobs.html'
  
  def fillInUI(self, parent):

    self.default_color = (0,0,0.8,1)
    self.default_box_color = (0,1,0,1)
    self.box_model = None
    
    t = parent.winfo_toplevel()
    self.toplevel_widget = t
    t.withdraw()

    parent.columnconfigure(0, weight = 1)
    row = 0

    import Tkinter
    from CGLtk import Hybrid

    mmf = Tkinter.Frame(parent)
    mmf.grid(row = row, column = 0, sticky = 'w')
    row = row + 1

    mb = Hybrid.Option_Menu(mmf, 'Use ',
                            'left', 'middle', 'right',
                            'ctrl left', 'ctrl middle', 'ctrl right')
    mb.variable.set('ctrl right')
    mb.frame.grid(row = 0, column = 0, sticky = 'w')
    mb.add_callback(self.bind_mouse_button_cb)
    self.mouse_button = mb
    self.bound_button = None
    
    mbl = Tkinter.Label(mmf, text = ' mouse button to choose blobs')
    mbl.grid(row = 0, column = 1, sticky = 'w')

    crf = Tkinter.Frame(parent)
    crf.grid(row = row, column = 0, sticky = 'ew')
    crf.columnconfigure(1, weight = 1)
    row += 1

    cl = Hybrid.Checkbutton(crf, 'Color blob ', True)
    cl.button.grid(row = 0, column = 0, sticky = 'w')
    self.color_blob = cl.variable
    
    from CGLtk.color import ColorWell
    sc = ColorWell.ColorWell(crf, color = self.default_color)
    sc.grid(row = 0, column = 1, sticky = 'w')
    self.blob_color = sc

    cc = Hybrid.Checkbutton(parent, 'Change color automatically', False)
    cc.button.grid(row = row, column = 0, sticky = 'w')
    self.change_color = cc.variable
    row += 1

    paf = Tkinter.Frame(parent)
    paf.grid(row = row, column = 0, sticky = 'ew')
    row += 1

    sb = Hybrid.Checkbutton(paf, 'Show principal axes box', False)
    sb.button.grid(row = 0, column = 0, sticky = 'w')
    self.show_box = sb.variable
    self.show_box.add_callback(self.show_box_cb)

    bc = ColorWell.ColorWell(paf, color = self.default_box_color)
    bc.grid(row = 0, column = 1, sticky = 'w')
    self.box_color = bc

    eb = Tkinter.Button(paf, text = 'Erase', command = self.erase_boxes_cb)
    eb.grid(row = 0, column = 2, sticky = 'w', padx=5)
    
    msg = Tkinter.Label(parent, anchor = 'w', justify = 'left',
                        wraplength = '15c')
    msg.grid(row = row, column = 0, sticky = 'ew')
    row += 1
    self.message_label = msg
    
    callbacks = (self.mouse_down_cb, self.mouse_drag_cb, self.mouse_up_cb)
    icon = self.mouse_mode_icon('pickblob.gif')
    from chimera import mousemodes
    mousemodes.addFunction('pick blobs', callbacks, icon)

  # ---------------------------------------------------------------------------
  #
  def message(self, text):

    self.message_label['text'] = text
    self.message_label.update_idletasks()

  # -------------------------------------------------------------------------
  #
  def mouse_mode_icon(self, filename):

    import os.path
    icon_path = os.path.join(os.path.dirname(__file__), filename)
    from PIL import Image
    image = Image.open(icon_path)
    from chimera import chimage, tkgui
    icon = chimage.get(image, tkgui.app)
    return icon

  # -------------------------------------------------------------------------
  #
  def mouse_down_cb(self, viewer, event):

    self.color_and_measure(event.x, event.y)

  # -------------------------------------------------------------------------
  #
  def color_and_measure(self, window_x, window_y):
    
    from VolumeViewer import slice
    xyz_in, xyz_out = slice.clip_plane_points(window_x, window_y)

    import PickBlobs
    smlist = PickBlobs.surface_models()
    p, vlist, tlist = PickBlobs.picked_surface_component(smlist, xyz_in, xyz_out)
    if p is None:
      self.message('No intercept with surface.')
      return

    if self.color_blob.get():
      PickBlobs.color_blob(p, vlist, self.blob_color.rgba)
      if self.change_color.get():
        from random import random as r
        from Matrix import normalize_vector
        rgba = tuple(normalize_vector((r(), r(), r()))) + (1,)
        self.blob_color.showColor(rgba)

    self.report_size(p, vlist, tlist)

  # -------------------------------------------------------------------------
  #
  def report_size(self, p, vlist, tlist):

    # Report enclosed volume and area
    import PickBlobs
    varray, tarray = PickBlobs.blob_geometry(p, vlist, tlist)
    from MeasureVolume import enclosed_volume, surface_area
    v, h = enclosed_volume(varray, tarray)
    blen = None
    if v == None:
      vstr = 'undefined (non-oriented surface)'
    else:
      vstr = '%.5g' % v
      if h > 0:
        vstr += ' (%d holes)' % h
        blen = PickBlobs.boundary_lengths(varray, tarray)
    area = surface_area(varray, tarray)

    axes, bounds = PickBlobs.principle_axes_box(varray, tarray)
    size = [bmax - bmin for bmin,bmax in bounds]

    s = p.model
    if self.show_box.get():
      b = PickBlobs.outline_box_surface(axes, bounds, s, self.box_model,
                                        rgba = self.box_color.rgba)
      self.box_model = b

    vstr = 'volume = %s' % (vstr,)
    astr = 'area = %.5g' % (area,)
    szstr = 'size = %.5g %.5g %.5g' % tuple(size)
    stats = (vstr, astr, szstr)
    if blen:
      blstr = 'boundary = %.5g' % sum(blen)
      stats += (blstr,)
      if len(blen) > 1:
        blen.sort()
        blen.reverse()
        llstr = 'loop lengths = ' + ', '.join('%.5g' % b for b in blen[:3])
        if len(blen) > 3:
          llstr += ', ...'
        stats += (llstr,)
    
    msg = ('Surface %s (%s) blob:\n  %s' %
           (s.name, s.oslIdent(), '\n  '.join(stats)))
    self.message(msg)
    from chimera.replyobj import info, status
    info(msg + '\n')
    status(', '.join(stats))

  # -------------------------------------------------------------------------
  #
  def show_box_cb(self):

    if self.box_model and not self.box_model.__destroyed__:
      self.box_model.display = self.show_box.get()

  # -------------------------------------------------------------------------
  #
  def erase_boxes_cb(self):

    if self.box_model:
      if not self.box_model.__destroyed__:
        from chimera import openModels
        openModels.close([self.box_model])
      self.box_model = None

  # -------------------------------------------------------------------------
  #
  def mouse_drag_cb(self, viewer, event):
    pass
  def mouse_up_cb(self, viewer, event):
    pass
    
  # ---------------------------------------------------------------------------
  #
  def bind_mouse_button_cb(self):

    bname = self.mouse_button.variable.get()
    button, modifiers = self.button_spec(bname)
    if self.bound_button != (button, modifiers):
      self.unbind_mouse_button()
    from chimera import mousemodes
    mousemodes.setButtonFunction(button, modifiers, 'pick blobs')
    self.bound_button = (button, modifiers)

  # ---------------------------------------------------------------------------
  #
  def map(self):

    self.bind_mouse_button_cb()

  # ---------------------------------------------------------------------------
  #
  def unmap(self):

    self.unbind_mouse_button()
    
  # ---------------------------------------------------------------------------
  # Restore mouse button binding to the default binding.
  #
  def unbind_mouse_button(self):

    if self.bound_button is None:
      return
    button, modifiers = self.bound_button
    from chimera import mousemodes
    def_mode = mousemodes.getDefault(button, modifiers)
    if def_mode:
      mousemodes.setButtonFunction(button, modifiers, def_mode)
    self.bound_button = None

  # ---------------------------------------------------------------------------
  #
  def button_spec(self, bname):

    name_to_bspec = {'left':('1', []), 'ctrl left':('1', ['Ctrl']),
                     'middle':('2', []), 'ctrl middle':('2', ['Ctrl']),
                     'right':('3', []), 'ctrl right':('3', ['Ctrl'])}
    bspec = name_to_bspec[bname]
    return bspec

# -----------------------------------------------------------------------------
#
def blob_picker_dialog(create = False):

  from chimera import dialogs
  return dialogs.find(Blob_Picker_Dialog.name, create=create)
  
# -----------------------------------------------------------------------------
#
def show_blob_picker_dialog():

  from chimera import dialogs
  return dialogs.display(Blob_Picker_Dialog.name)

# -----------------------------------------------------------------------------
#
from chimera import dialogs
dialogs.register(Blob_Picker_Dialog.name, Blob_Picker_Dialog, replace = 1)
