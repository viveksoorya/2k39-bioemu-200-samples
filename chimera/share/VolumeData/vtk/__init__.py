# -----------------------------------------------------------------------------
# XPLOR unformatted ascii density map file reader.
#
def open(path):

  from vtk_grid import VTK_Grid
  return [VTK_Grid(path)]
