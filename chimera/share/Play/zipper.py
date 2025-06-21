# -----------------------------------------------------------------------------
# Linearly interpolate atom coordinates between two conformations starting
# at one end of the chain and progressing to the other end.  If f represents
# the fraction for interpolating residue atoms with f = 0 being the initial
# state and f = 1 being the final state then f varies with residue number
# as a piecewise linear function, f = 1 for initial residues, then a linear
# ramp down to 0, then f = 0 for final residues in the chain.  The linear
# ramp is progressively moved from start to end of the chain, animating the
# change.  The width of the linear ramp is proportional to the distance between
# residue centers at the start of the ramp in the two states.
#
# Two new coordinate sets for the morphing molecule are made corresponding
# to the final state and the displayed intermediate state.
#
# This was originally used in an HIV RNA movie to show RNA being
# synthesized from a DNA template.
#
class Zip_Morph:

  def __init__(self, m1, rlist1, m2, rlist2, spacing, step):

    csi = max(m1.coordSets.keys()) + 1
    self.initial_coordset = ics = m1.newCoordSet(csi)
    for a in m1.atoms:
      a.setCoord(a.coord(), ics)
    self.final_coordset = fcs = m1.newCoordSet(csi+1)
    for a in m1.atoms:
      a.setCoord(a.coord(), fcs)
    self.copy_atom_positions(m2, rlist2, m1, rlist1, fcs)

    self.molecule = m1
    self.residues = rlist1
    self.spacing = spacing
    self.step = step
    self.position = 0 if step > 0 else len(rlist1)-1

  def play(self):

    from chimera import triggers
    self.handler = triggers.addHandler('new frame', self.frame_cb, None)

  def copy_atom_positions(self, m2, rlist2, m1, rlist1, fcs):

    xf = m2.openState.xform
    xf.premultiply(m1.openState.xform.inverse())
    for r1, r2 in zip(rlist1, rlist2):
      for a1 in r1.atoms:
        a2 = r2.findAtom(a1.name)
        if a2:
          a1.setCoord(xf.apply(a2.coord()), fcs)
    
  def frame_cb(self, tname, unused, fnum):

    ics, fcs = self.initial_coordset, self.final_coordset
    pos = self.position
    rlist = self.residues
    n = len(rlist)
    rp = max(0,min(n-1, pos))
    if rp == int(rp):
      d = distance(rlist[int(rp)].atoms, ics, fcs)
    else:
      d1 = distance(rlist[int(rp)].atoms, ics, fcs)
      d2 = distance(rlist[max(0,min(n-1,int(rp+1)))].atoms, ics, fcs)
      f = rp - int(rp)
      d = (1-f)*d1 + f*d2
    w = max(1, int(d/self.spacing))
    s = 1 if self.step > 0 else -1
    from chimera import lerp
    for p,r in enumerate(rlist):
        f = max(0, min(1, float(pos-p)/(w*s)))
        for a in r.atoms:
          a.setCoord(lerp(a.coord(ics),a.coord(fcs),f))
    if pos >= n + w or pos <= -w:
      self.finish_morph()
    else:
      self.position += self.step

  def finish_morph(self):

    from chimera import triggers
    triggers.deleteHandler('new frame', self.handler)
    m = self.molecule
    m.deleteCoordSet(self.initial_coordset)
    self.initial_coordset = None
    m.deleteCoordSet(self.final_coordset)
    self.final_coordset = None

# -----------------------------------------------------------------------------
#
def distance(atoms, cs1, cs2):

  from numpy import array
  c1 = array(tuple(a.coord(cs1).data() for a in atoms)).mean(axis=0)
  c2 = array(tuple(a.coord(cs2).data() for a in atoms)).mean(axis=0)
  dxyz = c1 - c2
  import math
  d = math.sqrt((dxyz*dxyz).sum())
  return d

# -----------------------------------------------------------------------------
# Preserve order.
#
def atom_residues(atoms):

  rlist = []
  rset = set()
  for a in atoms:
    r = a.residue
    if not r in rset:
      rlist.append(r)
      rset.add(r)
  return rlist
      
# -----------------------------------------------------------------------------
#
def zipper(residueList1, residueList2, spacing = 3, step = 1):

  rlist1 = atom_residues(residueList1.atoms())
  rlist2 = atom_residues(residueList2.atoms())
  if len(rlist1) == 0 or len(rlist2) == 0:
    from Commands import CommandError
    raise CommandError('play zipper: no residues specified %d, %d' %
                       (len(rlist1), len(rlist2)))
  if len(rlist1) != len(rlist2):
    from Commands import CommandError
    raise CommandError('play zipper: residues lists of different size %d, %d' %
                       (len(rlist1), len(rlist2)))
  m1 = set(r.molecule for r in rlist1)
  m2 = set(r.molecule for r in rlist2)
  if len(m1) != 1 or len(m2) != 1:
    from Commands import CommandError
    raise CommandError('play zipper: residues for each state must '
                       'belong to one molecule')
  m1, m2 = m1.pop(), m2.pop()

  zm = Zip_Morph(m1, rlist1, m2, rlist2, spacing, step)
  zm.play()
