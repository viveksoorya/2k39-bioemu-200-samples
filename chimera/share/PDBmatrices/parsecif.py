# -----------------------------------------------------------------------------
#
def cif_unit_cell_matrices(cif_headers, pack = None, group = False):

  slist = cif_crystal_symmetry_matrices(cif_headers)
  mlist = cif_ncs_matrices(cif_headers)

  cp = cif_unit_cell_parameters(cif_headers)
  uc = cp[:6] if cp else None
  import Crystal
  smlist = Crystal.unit_cell_matrices(slist, mlist, uc, pack, group)
  return smlist

# -----------------------------------------------------------------------------
#
def cif_unit_cell_parameters(cif_headers):

  if not 'tags' in cif_headers:
    return None

  t = cif_headers['tags']
  pnames = ('cell_length_a', 'cell_length_b', 'cell_length_c',
            'cell_angle_alpha', 'cell_angle_beta', 'cell_angle_gamma',
            'symmetry_space_group_name_h-m', 'cell_formula_units_z')
  params = [t.get(pname, None) for pname in pnames]
  
  if None in params[:6]:
    cell = [None]*6
  else:
    # Cell parameters can have uncertainty in parentheses at end.  Ick.
    cell = [float(a.split('(')[0]) for a in params[:6]]
    from math import pi
    cell = cell[:3] + [a*pi/180 for a in cell[3:]]  # convert degrees to radians

  sg = params[6]
  z = float(params[7]) if params[7] else None

  return cell + [sg, z]

# -----------------------------------------------------------------------------
#
def cif_crystal_symmetry_matrices(cif_headers):
  
  if not 'tables' in cif_headers:
    return []

  t = cif_headers['tables']
  seplist = t.get('symmetry_equiv_pos', None)
  if seplist:
    syms = []
    pnames = ('symmetry_equiv_pos_site_id', 'symmetry_equiv_pos_as_xyz')
    for sep in seplist:
      params = [sep.get(pname, None) for pname in pnames]
      if not None in params:
        syms.append((int(params[0]), params[1]))
    syms.sort()
    sops = [s[1] for s in syms]
  else:
    sgstable = None
    for tname, table in t.items():
      if (tname.startswith('table') and
          len(table) > 0 and
          'space_group_symop_operation_xyz' in table[0]):
        sgstable = table
        break
    if sgstable:
      sops = [sgs.get('space_group_symop_operation_xyz') for sgs in sgstable]
    else:
      return []

  from Crystal.space_groups import parse_symop
  ftflist = [parse_symop(sop.upper().replace(' ','')) for sop in sops]

  # Convert from fractional coordinates to xyz.
  uc = cif_unit_cell_parameters(cif_headers)[:6]
  if None in uc:
    return []
  import Crystal
  u2r = Crystal.unit_cell_to_xyz_matrix(*uc)
  import Matrix as M
  tflist = M.coordinate_transform_list(ftflist, M.invert_matrix(u2r))
  
  return tflist

# -----------------------------------------------------------------------------
#
def cif_ncs_matrices(cif_headers):

  return []     # TODO: Find out if and how CIF files support NCS symmetry
