import chimera.extension

class Volume_Tracer_EMO(chimera.extension.EMO):
  def name(self):
    return 'Volume Tracer'
  def description(self):
    return 'Place markers, trace paths, and trace surfaces in volume data.'
  def categories(self):
    return ['Volume Data']
  def icon(self):
    return self.path('volumepath.gif')
  def activate(self):
    self.module().show_volume_path_dialog()
    return None

# -----------------------------------------------------------------------------
#
chimera.extension.manager.registerExtension(Volume_Tracer_EMO(__file__))

# -----------------------------------------------------------------------------
#
def open_marker_set(path):
  
  import VolumePath
  VolumePath.open_marker_set(path)
  models = []
  return models

# -----------------------------------------------------------------------------
#
import chimera
fi = chimera.fileInfo
fi.register('Chimera markers', open_marker_set,
            ['.cmm'], ['markers'], category = fi.GENERIC3D)

# -----------------------------------------------------------------------------
#
def mark_zero():
  from VolumePath import place_marker, show_volume_path_dialog
  from chimera import selection as s, Point
  mlist = s.currentGraphs()
  if len(mlist) == 0:
    place_marker((0,0,0))
  else:
    for m in mlist:
      m0 = m.openState.xform.apply(Point(0,0,0)).data()
      place_marker(m0)
  show_volume_path_dialog()

# -----------------------------------------------------------------------------
#
def mark_cofr():
  from VolumePath import place_marker, show_volume_path_dialog
  from chimera import openModels
  place_marker(openModels.cofr.data())
  show_volume_path_dialog()

# -----------------------------------------------------------------------------
#
def place_marker_at_mouse():
  import VolumePath
  VolumePath.place_marker_at_mouse()

# -----------------------------------------------------------------------------
#
def place_markers_on_atoms():
  import VolumePath
  VolumePath.place_markers_on_atoms()

# -----------------------------------------------------------------------------
#
def place_marker_on_atoms():
  import VolumePath
  VolumePath.place_marker_on_atoms()

# -----------------------------------------------------------------------------
#
def place_marker_on_surface_pieces():
  import VolumePath
  VolumePath.place_marker_on_surface_pieces()
def place_markers_on_surface_pieces():
  import VolumePath
  VolumePath.place_markers_on_surface_pieces()
  
# -----------------------------------------------------------------------------
#
from Accelerators import add_accelerator
add_accelerator('mz', 'Place marker at position (0,0,0)', mark_zero)
add_accelerator('mc', 'Place marker at center of rotation', mark_cofr)
add_accelerator('mk', 'Place marker under mouse', place_marker_at_mouse)
add_accelerator('mS', 'Place markers on selected atoms', place_markers_on_atoms)
add_accelerator('mC', 'Place marker at center of selected atoms',
                place_marker_on_atoms)
add_accelerator('mE', 'Place markers at area-weighted centers of selected surface pieces',
                place_markers_on_surface_pieces)
add_accelerator('mP', 'Place marker at area-weighted center of selected surface pieces',
                place_marker_on_surface_pieces)

  
# -----------------------------------------------------------------------------
# Register "markers" selector.
#
from chimera.selection.manager import selMgr
selMgr.addSelector('volume tracer', [selMgr.STRUCTURE, 'markers'],
                   'import VolumePath\nsel.merge(selection.REPLACE, selection.ItemizedSelection([ms.molecule for ms in VolumePath.marker_sets() if ms.molecule]))',
                   makeCallbacks = True)
