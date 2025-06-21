# -----------------------------------------------------------------------------
#
def surface_models():

  from chimera import openModels as om
  from _surface import SurfaceModel
  mlist = om.list(modelTypes = [SurfaceModel])
  return mlist

# -----------------------------------------------------------------------------
#
def selected_surface_pieces(sel = None, include_outline_boxes = True):

  if sel is None:
    from chimera import selection
    sel = selection._currentSelection

  from _surface import SurfacePiece, SurfaceModel
  ps = set()
  for p in sel.vertices():
    if isinstance(p, SurfacePiece):
      ps.add(p)
  for s in sel.barrenGraphs():
    if isinstance(s, SurfaceModel):
      for p in s.surfacePieces:
        ps.add(p)
  plist = list(ps)

  if not include_outline_boxes:
    plist = [p for p in plist if not hasattr(p, 'outline_box')]

  return plist

# -----------------------------------------------------------------------------
#
def surface_pieces(slist, include_outline_boxes = False,
                   include_surface_caps = False):

  plist = []
  from SurfaceCap import is_surface_cap
  for s in slist:
    plist.extend(filter_surface_pieces(s.surfacePieces,
                                       include_outline_boxes,
                                       include_surface_caps))
  return plist

# -----------------------------------------------------------------------------
#
def filter_surface_pieces(plist, include_outline_boxes = False,
                          include_surface_caps = False):

  from SurfaceCap import is_surface_cap
  fplist = [p for p in plist
            if ((include_surface_caps or not is_surface_cap(p)) and
                (include_outline_boxes or not hasattr(p, 'outline_box')))]
  return fplist

# -----------------------------------------------------------------------------
#
def all_surface_pieces(include_outline_boxes = True):

  from _surface import SurfacePiece, SurfaceModel
  from chimera import openModels as om
  slist = om.list(modelTypes = [SurfaceModel])
  plist = []
  if include_outline_boxes:
    for s in slist:
      plist.extend(s.surfacePieces)
  else:
    for s in slist:
      plist.extend([p for p in s.surfacePieces
                    if not hasattr(p, 'outline_box')])
  return plist

# -----------------------------------------------------------------------------
# Toggle whether volume and multiscale surfaces are selectable with the mouse.
#
def toggle_surface_selectability():
  from _surface import SurfaceModel
  from chimera import openModels as om
  for m in om.list(modelTypes = [SurfaceModel]):
    m.piecesAreSelectable = not m.piecesAreSelectable

# -----------------------------------------------------------------------------
#
def color_surfaces(plist):
  'Show color dialog to color selected items'
  if plist:
    cw = color_surface_color_well()
    cw.plist = plist
    cw.deactivate()
    cw.showColor(plist[0].color)
    cw.activate()

# -----------------------------------------------------------------------------
#
cscw = None
def color_surface_color_well():
  global cscw
  if cscw == None:
    from CGLtk.color.ColorWell import ColorWell
    from chimera.tkgui import app
    cscw = ColorWell(app, callback = color_surface_cb)
  return cscw

# -----------------------------------------------------------------------------
#
def color_surface_cb(rgba):
  if len(rgba) == 4:
    cw = color_surface_color_well()
    for p in cw.plist:
      p.color = rgba
      p.vertexColors = None        # Turn off per-vertex coloring

# -----------------------------------------------------------------------------
#
def show_surfaces_as_mesh(plist):
  for p in plist:
    p.displayStyle = p.Mesh

# -----------------------------------------------------------------------------
#
def show_surfaces_filled(plist):
  for p in plist:
    p.displayStyle = p.Solid

# -----------------------------------------------------------------------------
#
def show_surfaces(plist):
  for p in plist:
    p.display = True

# -----------------------------------------------------------------------------
#
def hide_surfaces(plist):
  for p in plist:
    p.display = False

# -----------------------------------------------------------------------------
#
def delete_surfaces(plist):
  for p in plist:
    p.model.removePiece(p)
