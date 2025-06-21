# -----------------------------------------------------------------------------
#
def split_selected_surfaces(in_place = True):

  import Surface
  plist = Surface.selected_surface_pieces()
  if plist:
    pplist = split_surfaces(plist, in_place)
    from chimera.replyobj import status
    status('%d surface pieces' % len(pplist))

# -----------------------------------------------------------------------------
#
def split_surfaces(plist, in_place = False, model_id = None):

  surf = None
  if not in_place:
    import Surface
    surf = Surface.surface_models_with_id(model_id, at_most_one = True)
    if surf is None:
      import _surface
      surf = _surface.SurfaceModel()
      surf.name = '%s split' % plist[0].model.name if plist else 'split surface'
      from chimera import openModels as om
      if model_id is None:
        model_id = (om.Default, om.Default)
      om.add([surf], baseId = model_id[0], subid = model_id[1])

  pplist = []
  for p in plist:
    if p.__destroyed__:
      # Removing pieces in the loop can cause geometry change
      # callbacks that remove other pieces (like surface caps with clipping).
      continue
    pieces = split_surface_piece(p, surf or p.model)
    pplist.extend(pieces)
    if pieces:
      # Select pieces if original surface selected.
      from chimera import selection as sel
      if sel.containedInCurrent(p):
        sel.removeCurrent(p)
        sel.addCurrent(pieces)
      if in_place:
        p.model.removePiece(p)
      else:
        p.display = False

  return pplist

# -----------------------------------------------------------------------------
#
def split_surface_piece(p, into_surf):

  varray, tarray = p.geometry
  from _surface import connected_pieces
  cplist = connected_pieces(tarray)
  if len(cplist) <= 1 and p.model == into_surf:
    return []
  pplist = copy_surface_piece_blobs(p, varray, tarray, cplist, into_surf)
  return pplist

# -----------------------------------------------------------------------------
#
def copy_surface_piece_blobs(p, varray, tarray, cplist, into_surf):

  from numpy import zeros, int32
  vmap = zeros(len(varray), int32)

  pplist = []
  m = p.model
  narray = p.normals
  color = p.color
  vrgba = p.vertexColors
  temask = p.triangleAndEdgeMask
  for pi, (vi,ti) in enumerate(cplist):
    pp = copy_piece_blob(into_surf, varray, tarray, narray, color, vrgba, temask,
                         vi, ti, vmap)
    copy_piece_attributes(p, pp)
    pp.oslName = p.oslName + (' %d' % (pi+1))
    pplist.append(pp)

  return pplist

# -----------------------------------------------------------------------------
#
def copy_piece_blob(m, varray, tarray, narray, color, vrgba, temask,
                     vi, ti, vmap):

  va = varray.take(vi, axis = 0)
  ta = tarray.take(ti, axis = 0)

  # Remap triangle vertex indices for shorter vertex list.
  from numpy import arange
  vmap[vi] = arange(len(vi), dtype = vmap.dtype)
  ta = vmap.take(ta.ravel()).reshape((len(ti),3))

  gp = m.addPiece(va, ta, color)
  gp.save_in_session = True

  na = narray.take(vi, axis = 0)
  gp.normals = na

  if not vrgba is None:
    gp.vertexColors = vrgba.take(vi, axis = 0)
  if not temask is None:
    gp.triangleAndEdgeMask = temask.take(ti, axis = 0)

  return gp

# -----------------------------------------------------------------------------
#
def copy_piece_attributes(g, gp):

  gp.display = g.display
  gp.displayStyle = g.displayStyle
  gp.useLighting = g.useLighting
  gp.twoSidedLighting = g.twoSidedLighting
  gp.lineThickness = g.lineThickness
  gp.smoothLines = g.smoothLines
  gp.transparencyBlendMode = g.transparencyBlendMode
  gp.oslName = g.oslName
