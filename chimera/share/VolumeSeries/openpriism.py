# -----------------------------------------------------------------------------
#
def open_priism_time_series(path):

  from VolumeData import open_file
  dlist = open_file(path, 'priism')
  for data in dlist:
    tgrids = [Grid_Data_T(data, t) for t in range(data.num_times)]
    from VolumeViewer import volume_from_grid_data
    vlist = [volume_from_grid_data(g, show_data = (i==0), open_model = False, show_dialog = (i==0))
             for i,g in enumerate(tgrids)]
    from chimera import openModels
    openModels.add(vlist)

# -----------------------------------------------------------------------------
#
from VolumeData import Grid_Data

# -----------------------------------------------------------------------------
#
class Grid_Data_T(Grid_Data):

  def __init__(self, data, t):

    self.data = data
    self.time = t
    self.series_index = t

    Grid_Data.__init__(self, data.size, data.value_type,
                       data.origin, data.step, 
                       name = '%s t=%d' % (data.name, t),
                       file_type = data.file_type,
                       default_color = data.rgba)
    
  # ---------------------------------------------------------------------------
  #
  def read_matrix(self, ijk_origin, ijk_size, ijk_step, progress):

    return self.data.read_matrix(ijk_origin, ijk_size, ijk_step, progress,
                                 self.time)
