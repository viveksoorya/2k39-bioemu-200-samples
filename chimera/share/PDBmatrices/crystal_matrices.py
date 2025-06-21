# -----------------------------------------------------------------------------
#
from Crystal import space_group_matrices, unit_cell_axes, unit_cell_skew
from Crystal import unit_cell_to_xyz_matrix, cell_origin, cell_center
from Crystal import close_packing_matrices, pack_unit_cell
from Crystal import matrix_products, is_transform, space_group_matrices
from Crystal import translation_matrices, unit_cell_translations
from Crystal import unit_cell_matrices

# -----------------------------------------------------------------------------
# To get all the transformations needed to build the unit cell, multiply all
# SMTRY (crystallographic symmetry) matrices by all MTRIX (non-crystallographic
# symmetry) matrices.
#
# The pack argument can be set to a pair of points
# (molecule-center, unit-cell-origin) and the unit cell transforms will be
# translated to put all molecule centers in the unit cell box.
#
def pdb_unit_cell_matrices(pdb_headers, pack = None, group = False):

  slist = crystal_symmetry_matrices(pdb_headers)
  import parsepdb
  mlist = parsepdb.pdb_mtrix_matrices(pdb_headers)

  cp = crystal_parameters(pdb_headers)
  uc = cp[:6] if cp else None
  smlist = unit_cell_matrices(slist, mlist, uc, pack, group)
  return smlist

# -----------------------------------------------------------------------------
#
def pdb_3x3x3_unit_cell_matrices(pdb_headers, pack = None, group = False):

  cell_axes = pdb_unit_cell_axes(pdb_headers)
  mlist = translation_matrices(cell_axes, ((-1,1), (-1,1), (-1,1)))
  clist = pdb_unit_cell_matrices(pdb_headers, pack = pack, group = group)
  plist = matrix_products(mlist, clist, group)
  
  return plist

# -----------------------------------------------------------------------------
# Use SMTRY matrices if available, otherwise use space group matrices.
#
def crystal_symmetry_matrices(pdb_headers):

  import parsepdb
  slist = parsepdb.pdb_smtry_matrices(pdb_headers)
  if len(slist) == 0:
    slist = pdb_space_group_matrices(pdb_headers)

  # Handle crystal symmetry origin not equal to atom coordinate origin
  origin = parsepdb.pdb_crystal_origin(pdb_headers)
  if origin != (0,0,0):
    shift = [-x for x in origin]
    import Matrix as M
    slist = M.coordinate_transform_list(slist, M.translation_matrix(shift))

  return slist

# -----------------------------------------------------------------------------
#
def pdb_space_group_matrices(pdb_headers):

  cp = crystal_parameters(pdb_headers)
  if cp == None:
    return []
  a, b, c, alpha, beta, gamma, space_group, zvalue = cp
  sgt = space_group_matrices(space_group, a, b, c, alpha, beta, gamma)
  return sgt

# -----------------------------------------------------------------------------
#
def pdb_cryst1_symmetry_matrices(cryst1_line):

    a, b, c, alpha, beta, gamma, space_group, zvalue = \
       pdb_cryst1_parameters(cryst1_line)

    matrices = symmetry_matrices(space_group, a, b, c, alpha, beta, gamma)
    return matrices

# -----------------------------------------------------------------------------
#
def crystal_parameters(pdb_headers):

  cryst1_line = cryst1_pdb_record(pdb_headers)
  if not cryst1_line:
    return None
    
  cp = pdb_cryst1_parameters(cryst1_line)
  return cp

# -----------------------------------------------------------------------------
#
def cryst1_pdb_record(pdb_headers):

  h = pdb_headers
  if not h.has_key('CRYST1') or len(h['CRYST1']) != 1:
    return None

  line = h['CRYST1'][0]
  return line
    
# -----------------------------------------------------------------------------
#
def pdb_cryst1_parameters(cryst1_line):

  line = cryst1_line

  a = float(line[6:15])
  b = float(line[15:24])
  c = float(line[24:33])
  import math
  degrees_to_radians = math.pi / 180
  alpha = degrees_to_radians * float(line[33:40])
  beta = degrees_to_radians * float(line[40:47])
  gamma = degrees_to_radians * float(line[47:54])
  space_group = line[55:66].strip()
  zstr = line[66:70].strip()
  if zstr == '':
    zvalue = None
  else:
    zvalue = int(zstr)

  return a, b, c, alpha, beta, gamma, space_group, zvalue

# -----------------------------------------------------------------------------
#
def pdb_unit_cell_axes(pdb_headers):

  line = cryst1_pdb_record(pdb_headers)
  if line == None:
    return ((1,0,0), (0,1,0), (0,0,1))

  a, b, c, alpha, beta, gamma, space_group, zvalue = pdb_cryst1_parameters(line)
  axes = unit_cell_axes(a, b, c, alpha, beta, gamma)
  return axes

# -----------------------------------------------------------------------------
# Return a list of symmetry matrices by adding translations to tflist matrices
# so that they map ref_point into the unit cell box containing ref_point.
# The origin of the unit cell grid is given by grid_origin.
#
def pack_matrices(pdb_headers, grid_origin, ref_point, tflist):

    cp = crystal_parameters(pdb_headers)
    if cp is None:
      return tflist
    return pack_unit_cell(cp[:6], grid_origin, ref_point, tflist)
