# -----------------------------------------------------------------------------
#
def open_collada(path):
  import ReadCollada
  return [ReadCollada.read_collada(path)]

import chimera
fi = chimera.fileInfo
fi.register('Collada surface', open_collada, ['.dae'], ['collada'], category = fi.GENERIC3D)
