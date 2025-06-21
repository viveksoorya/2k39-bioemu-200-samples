# -----------------------------------------------------------------------------
# Wrap VTK density maps as grid data for displaying surface, meshes,
# and volumes.
#
from VolumeData import Grid_Data

# -----------------------------------------------------------------------------
#
class VTK_Grid(Grid_Data):

  def __init__(self, path):

    import vtk_format
    vm = vtk_format.VTK_Map(path)
    self.density_map = vm

    Grid_Data.__init__(self, vm.grid_size, origin = vm.origin, step = vm.spacing,
                       path = path, file_type = 'vtk')
  
  # ---------------------------------------------------------------------------
  #
  def read_matrix(self, ijk_origin, ijk_size, ijk_step, progress = None):

    matrix = self.density_map.matrix(progress)
    if ijk_size != self.size:
      self.cache_data(matrix, (0,0,0), self.size, (1,1,1)) # Cache full data.
    m = self.matrix_slice(matrix, ijk_origin, ijk_size, ijk_step)
    return m
