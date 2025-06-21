# -----------------------------------------------------------------------------
#
def open_stl(path):
  import ReadSTL
  return [ReadSTL.read_stl(path)]

import chimera
fi = chimera.fileInfo
fi.register('STL surface', open_stl, ['.stl'], ['stl'], category = fi.GENERIC3D)
