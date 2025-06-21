from chimera.extension import EMO, manager

# -----------------------------------------------------------------------------
#
class Cage_EMO(EMO):

  def name(self):
    return 'Cage Builder'
  def description(self):
    return 'Build cages having polygonal facets'
  def categories(self):
    return ['Higher-Order Structure']
  def icon(self):
    return self.path('cage.png')
  def activate(self):
    self.module('gui').show_cage_dialog()
    return None

# -----------------------------------------------------------------------------
#
manager.registerExtension(Cage_EMO(__file__))

# -----------------------------------------------------------------------------
#
degree = [3]
def attach_polygons(n, degree=degree):
  def attach(n=n, degree=degree):
    from CageBuilder import cage
    cage.attach_polygons('selected', n, vertex_degree = degree[0])
  return attach
def join_edges():
  from CageBuilder import cage
  cage.join_edges()
def unjoin_edges():
  from CageBuilder import cage
  cage.unjoin_edges()
def optimize_shape():
  from CageBuilder import cage
  cage.optimize_shape()
def optimize_shape_10():
  from CageBuilder import cage
  for i in range(10):
    cage.optimize_shape()
def expand():
  from CageBuilder import cage
  cage.expand(cage.selected_polygons(), 1.0)
def align_molecule():
  from CageBuilder import cage
  cage.align_molecule()
def delete_polygons():
  from CageBuilder import cage
  cage.delete_polygons()
def vertex_degree(d, degree=degree):
  def set_degree(d=d, degree=degree):
    degree[0] = d
  return set_degree
def toggle_inset():
  from CageBuilder import cage
  cage.toggle_inset()
def make_mesh():
  from CageBuilder import cage
  cage.make_mesh()
  
# -----------------------------------------------------------------------------
#
from Accelerators import add_accelerator
add_accelerator('p3', 'Attach triangle', attach_polygons(3))
add_accelerator('p4', 'Attach square', attach_polygons(4))
add_accelerator('p5', 'Attach pentagon', attach_polygons(5))
add_accelerator('p6', 'Attach hexagon', attach_polygons(6))
add_accelerator('p7', 'Attach septagon', attach_polygons(7))
for d in range(3,7):
  add_accelerator('P%d' % d, 'Set vertex degree %d' % d, vertex_degree(d))
add_accelerator('pj', 'Join shape edges', join_edges)
add_accelerator('pb', 'Unjoin shape edges', unjoin_edges)
add_accelerator('p0', 'Optimize shape', optimize_shape)
add_accelerator('po', 'Optimize shape 10 rounds', optimize_shape_10)
add_accelerator('pE', 'Expand cage', expand)
add_accelerator('pM', 'Align molecule to cage polygons', align_molecule)
add_accelerator('pD', 'Delete selected polygons', delete_polygons)
add_accelerator('pi', 'Toggle polygon inset', toggle_inset)
add_accelerator('pm', 'Make polygon mesh', make_mesh)
