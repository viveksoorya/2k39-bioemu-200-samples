import chimera.extension

# -----------------------------------------------------------------------------
#
class Volume_Series_EMO(chimera.extension.EMO):

  def name(self):
    return 'Volume Series'
  def description(self):
    return 'Control display of sequences of volume data sets'
  def categories(self):
    return ['Volume Data']
  def icon(self):
    return None
  def activate(self):
    self.module('gui').show_volume_series_dialog()
    return None

# -----------------------------------------------------------------------------
#
chimera.extension.manager.registerExtension(Volume_Series_EMO(__file__))

# -----------------------------------------------------------------------------
#
def open_priism_time_series(path):
  from VolumeSeries import openpriism
  return openpriism.open_priism_time_series(path)

# -----------------------------------------------------------------------------
#
from chimera import fileInfo
fileInfo.register('Priism time series', open_priism_time_series,
		  ['.xyzt'], ['priism_t'], canDecompress = False)

# -----------------------------------------------------------------------------
#
def open_series(vlist):

  for v in vlist:
    if not hasattr(v.data, 'series_index'):
      return

  from VolumeSeries import Volume_Series, gui
  vs = Volume_Series(vlist[0].name, volumes = vlist)
  gui.add_volume_series(vs)
  gui.show_volume_series_dialog()

from VolumeViewer.volume import add_volume_opened_callback
add_volume_opened_callback(open_series)

# -----------------------------------------------------------------------------
# Register vseries command.
#
def vseries_cmd(cmdname, args):
    from VolumeSeries.vseries_command import vseries_command
    vseries_command(cmdname, args)
from Midas.midas_text import addCommand
addCommand('vseries', vseries_cmd, help = True)
