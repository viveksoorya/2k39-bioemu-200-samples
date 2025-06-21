# -----------------------------------------------------------------------------
# User interface for building cages.
#
from chimera.baseDialog import ModelessDialog
import cage

# -----------------------------------------------------------------------------
#
class Cage_Dialog(ModelessDialog):

  title = 'Cage Builder'
  name = 'cage builder'
  buttons = ('Minimize', 'Options', 'Delete', 'Close',)
  help = 'ContributedSoftware/cagebuilder/cagebuilder.html'
  
  def fillInUI(self, parent ):

    import Tkinter
    from CGLtk import Hybrid
    
    frame = parent
    frame.columnconfigure(0, weight = 1)
    row = 0

    apf = Tkinter.Frame(parent)
    apf.grid(row = row, column = 0, sticky = 'w')
    
    apb = [('%d' % n , lambda n=n: self.attach_polygons(n)) for n in range(3,8)]
    ap = Hybrid.Button_Row(apf, 'Attach polygons with ', apb)
    ap.frame.grid(row = 0, column = 0, sticky = 'w')
    Tkinter.Label(apf, text = ' sides').grid(row = 0, column = 1, sticky = 'w')
    row += 1

    op = Hybrid.Popup_Panel(parent)
    opf = op.frame
    opf.grid(row = row, column = 0, sticky = 'news')
    opf.grid_remove()
    opf.columnconfigure(0, weight=1)
    self.options_panel = op.panel_shown_variable
    row += 1
    orow = 0

    cb = op.make_close_button(opf)
    cb.grid(row = orow, column = 1, sticky = 'e')
    
    jf = Tkinter.Frame(opf)
    jf.grid(row=orow, column=0, sticky='ew')
    orow += 1
    jb = Tkinter.Button(jf, text = 'Join', command = self.join_edges)
    jb.grid(row=0, column=0, sticky='w')
    jl = Tkinter.Label(jf, text = ' or ')
    jl.grid(row=0, column=1, sticky='w')
    ujb = Tkinter.Button(jf, text = 'Unjoin', command = cage.unjoin_edges)
    ujb.grid(row=0, column=2, sticky='w')
    jl = Tkinter.Label(jf, text = ' selected polygon edges')
    jl.grid(row=0, column=3, sticky='w')
    
    dg = Hybrid.Checkbutton_Entries(opf, True,
                                    'Join polygons so that ', (2,'3'),
                                    ' edges meet at a vertex')
    dg.frame.grid(row=orow, column=0, sticky='w')
    self.fixed_degree, self.vert_degree = dg.variables
    orow += 1

    sf = Tkinter.Frame(opf)
    sf.grid(row=orow, column=0, sticky='ew')
    orow += 1
    sb = Tkinter.Button(sf, text = 'Scale', command = self.scale)
    sb.grid(row=0, column=0, sticky='w')
    se = Hybrid.Entry(sf, ' cage by ', 2, '2')
    self.scale_factor = se.variable
    se.frame.grid(row=0, column=1, sticky='w')
    se.entry.bind('<KeyPress-Return>', self.scale)

    ef = Tkinter.Frame(opf)
    ef.grid(row=orow, column=0, sticky='w')
    orow += 1
    seb = Tkinter.Button(ef, text = 'Set', command = self.set_edge_size)
    seb.grid(row=0, column=0, sticky='w')
    el = Hybrid.Entry(ef, ' edge length ', 4, '1.0')
    el.frame.grid(row=0, column=1, sticky='w')
    self.edge_length = el.variable
    el.entry.bind('<KeyPress-Return>', self.set_edge_size)
    et = Hybrid.Entry(ef, ' thickness ', 4, '0.2')
    et.frame.grid(row=0, column=2, sticky='w')
    self.edge_thickness = et.variable
    et.entry.bind('<KeyPress-Return>', self.set_edge_size)
    il = Tkinter.Label(ef, text = ' ')
    il.grid(row=0, column=3, sticky='w')
    ei = Hybrid.Checkbutton_Entries(ef, True, 'inset ', (4, '0.1'))
    ei.frame.grid(row=0, column=4, sticky='w')
    self.use_inset, self.edge_inset = ei.variables
    self.use_inset.add_callback(self.toggle_inset)
    ei.entries[0].bind('<KeyPress-Return>', self.set_edge_size)

    ef = Tkinter.Frame(opf)
    ef.grid(row=orow, column=0, sticky='ew')
    orow += 1
    eb = Tkinter.Button(ef, text = 'Expand', command = self.expand)
    eb.grid(row=0, column=2, sticky='w')
    ee = Hybrid.Entry(ef, ' cage by ', 2, '1', ' times edge length')
    self.expand_distance = ee.variable
    ee.frame.grid(row=0, column=3, sticky='w')
    ee.entry.bind('<KeyPress-Return>', self.expand)

    mf = Tkinter.Frame(opf)
    mf.grid(row=orow, column=0, sticky='ew')
    orow += 1
    ml = Tkinter.Label(mf, text = 'Create ')
    ml.grid(row=0, column=0, sticky='w')
    mb = Tkinter.Button(mf, text = 'Mesh', command = self.make_mesh)
    mb.grid(row=0, column=1, sticky='w')
    ml = Tkinter.Label(mf, text = ' model from cage polygons, color')
    ml.grid(row=0, column=2, sticky='w')
    from CGLtk.color import ColorWell
    c = ColorWell.ColorWell(mf, width = 25, height = 25)
    c.showColor((.7,.7,.7,1))
    c.grid(row=0, column=3, padx = 5)
    self.mesh_color = c

  # ---------------------------------------------------------------------------
  #
  def attach_polygons(self, n):

    d = self.vertex_degree()
    length, thickness, inset = self.edge_size()
    cage.attach_polygons('selected', n, length, thickness, inset,
                         vertex_degree = d)

  # ---------------------------------------------------------------------------
  #
  def edge_size(self):

    from CGLtk import Hybrid
    edge_length = Hybrid.float_variable_value(self.edge_length, 1.0)
    edge_thickness =  Hybrid.float_variable_value(self.edge_thickness,
                                                  0.2*edge_length)
    edge_inset = Hybrid.float_variable_value(self.edge_inset, 0.2*edge_length)
    return edge_length, edge_thickness, edge_inset

  # ---------------------------------------------------------------------------
  #
  def join_edges(self):

    if not cage.join_edges(vertex_degree = self.vertex_degree()):
      from chimera.replyobj import status
      status('Must select exactly 2 polygon edges to join.')

  # ---------------------------------------------------------------------------
  #
  def toggle_inset(self):

    cage.use_inset(self.use_inset.get())
    
  # ---------------------------------------------------------------------------
  #
  def expand(self, event = None):

    length, thickness, inset = self.edge_size()
    from CGLtk import Hybrid
    e = Hybrid.float_variable_value(self.expand_distance, 1.0)
    plist = cage.selected_polygons(full_cages = True, none_implies_all = True)
    cage.expand(plist, e*length)
    
  # ---------------------------------------------------------------------------
  #
  def scale(self, event = None):

    from CGLtk import Hybrid
    f = Hybrid.float_variable_value(self.scale_factor, None)
    if f is None:
      return
    plist = cage.selected_polygons(full_cages = True, none_implies_all = True)
    cage.scale(plist, f)
 
    length, thickness, inset = self.edge_size()
    self.edge_length.set('%g' % (f*length))
    self.edge_thickness.set('%g' % (f*thickness))
    self.edge_inset.set('%g' % (f*inset))

  # ---------------------------------------------------------------------------
  #
  def vertex_degree(self):

    if self.fixed_degree.get():
      from CGLtk import Hybrid
      d = Hybrid.integer_variable_value(self.vert_degree, 3, 3)
    else:
      d = None
    return d
    
  # ---------------------------------------------------------------------------
  #
  def make_mesh(self):

    plist = cage.selected_polygons(full_cages = True, none_implies_all = True)
    length, thickness, inset = self.edge_size()
    color = self.mesh_color.rgba
    cage.make_polygon_mesh(plist, color, thickness)
    
  # ---------------------------------------------------------------------------
  #
  def Minimize(self):

    # TODO: Might provide option to choose number of minimization steps.
    for i in range(10):
      cage.optimize_shape()
    
  # ---------------------------------------------------------------------------
  #
  def Options(self):

    self.options_panel.set(not self.options_panel.get())
    
  # ---------------------------------------------------------------------------
  #
  def Delete(self):

    cage.delete_polygons()

  # ---------------------------------------------------------------------------
  #
  def set_edge_size(self, event = None):

    length, thickness, inset = self.edge_size()
    plist = cage.selected_polygons(full_cages = True, none_implies_all = True)
    for p in plist:
      p.resize(length, thickness, inset)

# -----------------------------------------------------------------------------
#
def cage_dialog(create = False):

  from chimera import dialogs
  return dialogs.find(Cage_Dialog.name, create=create)
  
# -----------------------------------------------------------------------------
#
def show_cage_dialog():

  from chimera import dialogs
  return dialogs.display(Cage_Dialog.name)

# -----------------------------------------------------------------------------
#
from chimera import dialogs
dialogs.register(Cage_Dialog.name, Cage_Dialog, replace = True)
