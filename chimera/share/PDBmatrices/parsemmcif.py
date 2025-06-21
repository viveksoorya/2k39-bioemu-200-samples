# -----------------------------------------------------------------------------
#
def mmcif_unit_cell_matrices(mmcif_headers, pack = None, group = False):

  slist = mmcif_crystal_symmetry_matrices(mmcif_headers)
  mlist = mmcif_ncs_matrices(mmcif_headers)

  cp = mmcif_unit_cell_parameters(mmcif_headers)
  uc = cp[:6] if cp else None
  import Crystal
  smlist = Crystal.unit_cell_matrices(slist, mlist, uc, pack, group)
  return smlist

# -----------------------------------------------------------------------------
#
def mmcif_unit_cell_parameters(mmcif_headers):

  if not 'cell' in mmcif_headers:
    return None

  t = mmcif_headers['cell'][0]
  pnames = ('length_a', 'length_b', 'length_c',
            'angle_alpha', 'angle_beta', 'angle_gamma')
  params = [t.get(pname, None) for pname in pnames]
  
  # Cell parameters can have uncertainty in parentheses at end.  Ick.
  try:
    cell = [float(a) for a in params]
  except ValueError:
    return None

  from math import pi
  cell = cell[:3] + [a*pi/180 for a in cell[3:]]  # convert degrees to radians

  if 'z_pdb' in t:
    try:
      z = int(t['z_pdb'])
    except ValueError:
      z = None
  if 'symmetry' in mmcif_headers:
    st = mmcif_headers['symmetry'][0]
    sg = st.get('space_group_name_h-m', None)
  else:
    sg = None

  return cell + [sg, z]

# -----------------------------------------------------------------------------
#
def mmcif_crystal_symmetry_matrices(mmcif_headers):

  # TODO: No crystal symmetry matrices in example file 1bbt.cif.  Probably
  #       have to use space group name to lookup symmetries.
  cp = mmcif_unit_cell_parameters(mmcif_headers)
  if cp:
    a, b, c, alpha, beta, gamma, space_group, zvalue = cp
    import Crystal
    sgt = Crystal.space_group_matrices(space_group, a, b, c, alpha, beta, gamma)
  else:
    sgt = []

  # Handle crystal symmetry origin not equal to atom coordinate origin
  origin = mmcif_crystal_origin(mmcif_headers)
  print 'mmcif origin', origin
  if origin != (0,0,0):
    shift = [-x for x in origin]
    import Matrix as M
    sgt = M.coordinate_transform_list(sgt, M.translation_matrix(shift))
    
  return sgt

# -----------------------------------------------------------------------------
#
def mmcif_ncs_matrices(mmcif_headers, include_given = True):

  if not 'struct_ncs_oper' in mmcif_headers:
    return []

  t = mmcif_headers['struct_ncs_oper']
  tflist = []
  for d in t:
    if include_given or d['code'] != 'given':
      id = int(d['id'])
      tf = mmcif_matrix(d)
      tflist.append((id, tf))
  tflist.sort()
  return [tf for id, tf in tflist]

# -----------------------------------------------------------------------------
#
def mmcif_matrix(mdict):

  pnames = ('matrix[1][1]', 'matrix[1][2]', 'matrix[1][3]',
            'matrix[2][1]', 'matrix[2][2]', 'matrix[2][3]',
            'matrix[3][1]', 'matrix[3][2]', 'matrix[3][3]',
            'vector[1]', 'vector[2]', 'vector[3]')
  m11, m12, m13, m21, m22, m23, m31, m32, m33, v1, v2, v3 = \
       [float(mdict[pname]) for pname in pnames]
  tf = ((m11, m12, m13, v1),
        (m21, m22, m23, v2),
        (m31, m32, m33, v3))
  return tf

# -----------------------------------------------------------------------------
#
def mmcif_biounit_matrices(mmcif_headers):

  # TODO: mmCIF file lists multiple assemblies, not just a single biological
  # unit like PDB format files.  This code returns all assembly matrices that
  # have integer id names.
  
  if not 'pdbx_struct_oper_list' in mmcif_headers:
    return []

  ops = mmcif_headers['pdbx_struct_oper_list']
  tflist = []
  for op in ops:
    try:
      i = int(op['id'])
    except ValueError:
      continue
    tflist.append((i, mmcif_matrix(op)))
  tflist.sort()
  return [tf for i, tf in tflist]

# -----------------------------------------------------------------------------
# PDB entries allow the origin of the crystal unit cell symmetries
# to be different from the origin of atom coordinates.  It is rare, e.g. PDB 1WAP.
# Given in mmcif _atom_sites.fract_transf_vector
#
def mmcif_crystal_origin(mmcif_headers):
  a = mmcif_headers.get('atom_sites')
  print 'atom_sites', a
  if not a:
    return (0,0,0)

  a0 = a[0]
  try:
    forigin = [float(a0['fract_transf_vector[%d]' % i]) for i in (1,2,3)]
  except:
    return (0,0,0)
  print 'forigin', forigin

  # Convert fractional unit cell coordinates to atom coordinates
  cp = mmcif_unit_cell_parameters(mmcif_headers)
  print 'cell param', cp
  if cp is None:
    return (0,0,0)
  
  fx,fy,fz = forigin
  a, b, c, alpha, beta, gamma, space_group, zvalue = cp
  import Crystal
  ax,ay,az = Crystal.unit_cell_axes(a, b, c, alpha, beta, gamma)
  from Matrix import linear_combination
  origin = tuple(linear_combination(fx,ax,fy,ay,fz,az))

  return origin
