# -----------------------------------------------------------------------------
# Command to create a molecule model from a surface mesh.
#
# Syntax: mesh_to_molecule <surface-model-id>
#
def mesh_to_molecule(cmdname, args):
    
  fields = args.split()

  if len(fields) != 2:
    from Midas.midas_text import error
    error('%s requires 2 argument: %s <surface-model-id> <stick-radius>' %
          (cmdname, cmdname))
    return

  sid, rad = fields

  s = parse_surface_id(sid, cmdname)
  if s == None:
    return
  
  # Parse stick radius
  try:
    radius = float(rad)
  except ValueError:
    from Midas.midas_text import error
    error('%s: Invalid radius value %s' % (cmdname, rad))
    return

  molecule_from_mesh(s, radius)

# -----------------------------------------------------------------------------
#
def molecule_from_mesh(s, stick_radius):

  from VolumePath import Marker_Set, Link
  from SurfaceCap import is_surface_cap
  m = Marker_Set('Mesh ' + s.name)
  radius = stick_radius
  for p in s.surfacePieces:
    if is_surface_cap(p):
      continue
    varray, earray = p.maskedGeometry(p.Mesh)
    vcolors = p.vertexColors
    markers = {}
    for edge in earray:
      for v in edge:
        if not v in markers:
          xyz = varray[v]
          color = p.color if vcolors is None else vcolors[v]
          markers[v] = m.place_marker(xyz, color, radius)
    for v1,v2 in earray:
      m1 = markers[v1]
      m2 = markers[v2]
      color = tuple(.5*(a+b) for a,b in zip(m1.rgba(), m2.rgba()))
      Link(m1, m2, color, radius)
  return m
    
# -----------------------------------------------------------------------------
#
def parse_surface_id(sid, cmdname):

  if sid[:1] == '#':
    sid = sid[1:]

  fields = sid.split('.')
  if len(fields) == 1:
    fields.append('0')

  try:
    id, subid = int(fields[0]), int(fields[1])
  except ValueError:
    from Midas.midas_text import error
    error('%s: Bad model specifier %s' % (cmdname, sid))
    return None

  from chimera import openModels
  from _surface import SurfaceModel
  mlist = openModels.list(id = id, subid = subid, modelTypes = [SurfaceModel])
  if len(mlist) == 0:
    from Midas.midas_text import error
    error('%s: No surface with id %d.%d' % (cmdname, id, subid))
    return None

  return mlist[0]
