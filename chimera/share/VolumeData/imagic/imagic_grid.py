#
# ---------------------------------------------------------------------------------
# Wrap IMAGIC image data as grid data for displaying surface, meshes, and volumes.
# ---------------------------------------------------------------------------------
# Modification by Dr Sayan Bhakta to be able to read more than one 3D volume from
# the same multiple 3D volume file.
# ---------------------------------------------------------------------------------
#

from VolumeData import Grid_Data

class IMAGIC_Grid(Grid_Data):

  def __init__(self, path, file_type = 'hed', grid_id = None):

    import imagic_format
    h = imagic_format.IMAGIC_Data(path, file_type)

    self.imagic_data = h
    grid_id = h.data_offset

    Grid_Data.__init__(self, h.data_size, h.element_type,
                       h.data_origin, h.data_step, h.cell_angles, h.rotation,
                       path = path, file_type = file_type, grid_id = grid_id)

    self.unit_cell_size = h.unit_cell_size
  
  def read_matrix(self, ijk_origin, ijk_size, ijk_step, progress):

    return self.imagic_data.read_matrix(ijk_origin, ijk_size, ijk_step, progress)
