# ----------------------------------------------------------------------------
#
os_dialog = None
def open_series_files():

  global os_dialog
  if os_dialog == None:
    os_dialog = Open_Series_Dialog()
  else:
    os_dialog.enter()

# -----------------------------------------------------------------------------
#
import OpenSave
class Open_Series_Dialog(OpenSave.OpenModeless):

  def __init__(self):

    from VolumeData.opendialog import file_type_filters
    filters = file_type_filters()

    self.priism_type = 'Priism time series'
    filters.append((self.priism_type, ['*.xyzt']))
    
    OpenSave.OpenModeless.__init__(self,
                                   title = 'Open Volume Series',
                                   filters = filters,
                                   clientPos = 's',
                                   clientSticky = 'w')
    
  # ---------------------------------------------------------------------------
  #
  def fillInUI(self, parent):

    OpenSave.OpenModeless.fillInUI(self, parent)

    import Tkinter
    msg = Tkinter.Label(self.clientArea, justify='left', anchor='w',
                        wraplength = '10c')     # 10 centimeters
    msg.grid(row=0, column=0, sticky='w')
    self.message = msg

  # ---------------------------------------------------------------------------
  # Don't close if there was an error opening a file.
  # The error message is displayed in the open file dialog.
  #
  def OK(self):

    if self.Apply():
      self.Close()

  # ---------------------------------------------------------------------------
  # Handle single and multiple file series.
  #
  def Apply(self):

    paths_and_types = self.getPathsAndTypes()

    paths = []
    for path, ftype in paths_and_types:
        if ftype == self.priism_type:
            import openpriism
            openpriism.open_priism_time_series(path)
        else:
          paths.append(path)

    open_series(paths)
    return True

def open_series(paths):
    vlist = []
    for path in paths:
      import VolumeViewer
      maps = VolumeViewer.open_volume_file(path, show_data = False, open_models = False)
      vlist.extend(maps)

    if vlist:
      for i,v in enumerate(vlist):
        v.data.series_index = i
      from chimera import openModels
      openModels.add(vlist)
      v0 = vlist[0]
      v0.initialize_thresholds()
      v0.show()
