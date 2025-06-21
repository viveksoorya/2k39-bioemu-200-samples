# -----------------------------------------------------------------------------
# Dialog for applying a rotation and translation to a model's coordinate
# system or to the atom coordinates of a molecule.
#
import chimera
from chimera.baseDialog import ModelessDialog

# -----------------------------------------------------------------------------
#
class Transform_Coords_Dialog(ModelessDialog):

  title = 'Transform Coordinates'
  name = 'transform coordinates'
  buttons = ('Apply', 'Set', 'Reset', 'Close',)
  help = 'ContributedSoftware/transform/transform.html'
  
  def fillInUI(self, parent):

    self.toplevel_widget = parent.winfo_toplevel()
    self.toplevel_widget.withdraw()

    parent.columnconfigure(0, weight=1)         # Allow scalebar to expand.
    
    row = 0

    import Tkinter
    from CGLtk import Hybrid

    from chimera.widgets import ModelOptionMenu
    mm = ModelOptionMenu(parent, labelpos = 'w', label_text = 'Model ',
                            command = self.show_cumulative_transform)
    mm.grid(row = row, column = 0, sticky = 'w')
    self.model_menu = mm
    row += 1

    ea = Hybrid.Entry(parent, 'Euler angles ', 25, '0 0 0')
    ea.frame.grid(row = row, column = 0, sticky = 'e')
    row += 1
    self.euler_angles = ea.variable

    tr = Hybrid.Entry(parent, 'Shift ', 25, '0 0 0')
    tr.frame.grid(row = row, column = 0, sticky = 'e')
    row += 1
    self.translation = tr.variable

    mc = Hybrid.Checkbutton(parent, 'Move atoms instead of coordinate axes', True)
    mc.button.grid(row = row, column = 0, sticky = 'w')
    self.move_atoms_checkbutton = mc.button
    self.move_atoms = mc.variable
    row += 1

    cas = Tkinter.Label(parent, text = '', justify = 'left')
    cas.grid(row = row, column = 0, sticky = 'w')
    self.cumulative = cas
    row += 1

    self.show_cumulative_transform(self.model_menu.getvalue())
    
  # ---------------------------------------------------------------------------
  #
  def Apply(self):

    self.transform_cb()
      
  # ---------------------------------------------------------------------------
  #
  def Set(self):

    self.reset_cb()
    self.transform_cb()
      
  # ---------------------------------------------------------------------------
  #
  def Reset(self):

    self.reset_cb()

  # ---------------------------------------------------------------------------
  #
  def transform_cb(self, event = None):
    
    m = self.model_menu.getvalue()
    if m == None:
      from chimera.replyobj import warning
      warning('No model selected in Transform dialog')
      return

    try:
      ea = map(float, self.euler_angles.get().split())
      t = map(float, self.translation.get().split())
    except ValueError:
      from chimera.replyobj import warning
      warning('Error parsing Euler angle or translation number')
      return

    if len(ea) != 3:
      from chimera.replyobj import warning
      warning('Require 3 Euler angles separated by spaces')
      return

    if len(t) != 3:
      from chimera.replyobj import warning
      warning('Require 3 translation values separated by spaces')
      return

    import MoleculeTransform as mt
    xf = mt.euler_xform(ea, t)
    from chimera import Molecule
    if isinstance(m, Molecule) and self.move_atoms.get():
      mt.transform_atom_coordinates(m.atoms, xf)
    else:
      mt.transform_coordinate_axes(m, xf)
    self.record_xform(m, xf)

  # ---------------------------------------------------------------------------
  #
  def reset_cb(self, event = None):

    m = self.model_menu.getvalue()
    if m is None or not hasattr(m, 'applied_xform'):
      return

    xf = m.applied_xform.inverse()
    import MoleculeTransform as mt
    from chimera import Molecule
    if isinstance(m, Molecule) and self.move_atoms.get():
      mt.transform_atom_coordinates(m.atoms, xf)
    else:
      mt.transform_coordinate_axes(m, xf)
    self.record_xform(m, None)
    
  # ---------------------------------------------------------------------------
  #
  def record_xform(self, m, xf):

    mxf = getattr(m, 'applied_xform', None)
    if xf is None:
      if mxf:
        delattr(m, 'applied_xform')
    elif mxf:
      mxf.premultiply(xf)
      m.applied_xform = mxf
    else:
      m.applied_xform = xf
    self.show_cumulative_transform(m)
    
  # ---------------------------------------------------------------------------
  #
  def show_cumulative_transform(self, m):

    from chimera import Xform
    mxf = getattr(m, 'applied_xform', Xform())
    import Matrix
    tf = Matrix.xform_matrix(mxf)
    angles = Matrix.euler_angles(tf)
    shift = mxf.getTranslation().data()
    text = ('Cumulative:\n' +
            ' Euler angles %.5g %.5g %.5g\n' % angles +
            ' Shift: %.5g %.5g %.5g' % shift)
    self.cumulative['text'] = text

    from chimera import Molecule
    self.move_atoms_checkbutton['state'] = 'normal' if isinstance(m, Molecule) else 'disabled'
      
# -----------------------------------------------------------------------------
#
def transform_coordinates_dialog(create = False):

  from chimera import dialogs
  return dialogs.find(Transform_Coords_Dialog.name, create=create)
  
# -----------------------------------------------------------------------------
#
def show_transform_coordinates_dialog():

  from chimera import dialogs
  return dialogs.display(Transform_Coords_Dialog.name)

# -----------------------------------------------------------------------------
#
from chimera import dialogs
dialogs.register(Transform_Coords_Dialog.name, Transform_Coords_Dialog,
                 replace = True)
