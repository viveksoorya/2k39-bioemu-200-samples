# -----------------------------------------------------------------------------
# IMAGIC density map file reader.
# Used by Image Science Software GmbH
#

from imagic_write import write_imagic_grid_data

# -----------------------------------------------------------------------------
#
def open(path):

  from imagic_grid import IMAGIC_Grid
  return [IMAGIC_Grid(path)]
