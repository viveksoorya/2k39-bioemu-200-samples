# -----------------------------------------------------------------------------
#
def open_swc(path):
  import Neuron
  mset = Neuron.read_swc(path)
  mset.show_model(True)
  return []

import chimera
fi = chimera.fileInfo
fi.register('Neuron trace', open_swc, ['.swc'], ['swc'], category = fi.GENERIC3D)
