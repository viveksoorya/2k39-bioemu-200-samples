# -----------------------------------------------------------------------------
# coordset command to play frames of a trajectory.
#
# Syntax: coordset <molecule-id>
#                  <start>[,<end>][,<step>]     # frame range
#                  [holdSteady <atomSpec>]
#
# Unspecified start or end defaults to current frame, last frame.
# Unspecified step is 1 or -1 depending on if end > start.
# Can use -1 for last frame.  Frame numbers start at 1.
#
def coordset(cmdname, args):

  from Midas.midas_text import doExtensionFunc
  doExtensionFunc(show_coordinates, args,
                  specInfo = [('moleculeSpec','molecules','models'),
                              ('holdSteadySpec','holdSteady','atoms')])

# -----------------------------------------------------------------------------
#
def show_coordinates(molecules, indexRange, holdSteady = None, loop = 1, load = True):

  from Midas import MidasError

  from chimera import Molecule
  mlist = [m for m in molecules if isinstance(m, Molecule)]
  if len(mlist) == 0:
    raise MidasError('No molecules specified')

  for m in mlist:
    if load:
      m.loadAllFrames()
    s,e,step = parse_index_range(indexRange, m)
    print "coordset range", s, e, step
    Coordinate_Set_Player(m, s, e, step, holdSteady, loop).start()

# -----------------------------------------------------------------------------
#
def parse_index_range(index_range, mol):

  from Midas import MidasError

  if isinstance(index_range, int):
    index_range = '%d' % index_range

  ilist = index_range.split(',')
  if len(ilist) > 3:
    raise MidasError, 'Bad index range "%s", use start[,end][,step]' % index_range

  i0 = mol.activeCoordSet.id
  keys = mol.coordSets.keys()
  imin = min(keys)
  imax = max(keys)
  irange = [i0,imax,1]
  for p,i in enumerate(ilist):
    if i:
      try:
        irange[p] = int(i)
      except ValueError:
        raise MidasError, 'Bad index range "%s", use start[,end][,step]' % index_range
  if len(ilist) == 1:
    irange[1] = irange[0]

  for p,i in enumerate(irange[:2]):
    if i < 0:
      i = imax + 1 + i                  # negative indices count from end
    irange[p] = min(max(i, imin), imax)    # clamp to [imin,imax]

  if len(ilist) < 3 and irange[1] < irange[0]:
    irange[2] = -1

  return irange

# -----------------------------------------------------------------------------
#
class Coordinate_Set_Player:

  def __init__(self, molecule, istart, iend, istep, steady_atoms = None,
               loop = 1):

    self.molecule = molecule
    self.istart = istart
    self.iend = iend
    self.istep = istep
    self.inext = None
    self.steady_atoms = steady_atoms
    self.loop = loop
    self.steady_cset = None
    self.xform_cache = {}
    self.handler = None

  def start(self):

    self.inext = self.istart
    from chimera import triggers as t
    self.handler = t.addHandler('new frame', self.frame_cb, None)

  def stop(self):

    if self.handler is None:
      return
    from chimera import triggers as t
    t.deleteHandler('new frame', self.handler)
    self.handler = None
    self.inext = None

  def frame_cb(self, tname, tdata, cdata):

    m = self.molecule
    if m.__destroyed__:
      self.stop()
      return
    i = self.inext
    if i in m.coordSets:
      last_cs = m.activeCoordSet
      m.activeCoordSet = m.coordSets[i]
      if self.steady_atoms:
        self.hold_steady(last_cs)
    self.inext += self.istep
    if ((self.istep > 0 and self.inext > self.iend) or
        (self.istep < 0 and self.inext < self.iend)):
      if self.loop <= 1:
        self.stop()
      else:
        self.inext = self.istart
        self.loop -= 1

  def hold_steady(self, last_cs):

    m = self.molecule
    xf = m.openState.xform
    xf.multiply(self.steady_xform(last_cs).inverse())
    xf.multiply(self.steady_xform(m.activeCoordSet))
    m.openState.xform = xf
    
  def steady_xform(self, cset):

    xfc = self.xform_cache
    if cset in xfc:
      return xfc[cset]
    if self.steady_cset is None:
      self.steady_cset = cset
    atoms = self.steady_atoms
    from chimera.match import matchAtoms
    xf = matchAtoms(atoms, atoms, self.steady_cset, cset)[0]
    xfc[cset] = xf
    return xf
