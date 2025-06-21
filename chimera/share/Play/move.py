# -----------------------------------------------------------------------------
# Command "play move" animates motion of multiscale chains.  It can move
# individual chains.  It can parse multiscale chain names even though the
# standard Chimera atom spec parser cannot handle these.  It can move
# chains relative to a minimum RMSD aligned copy of target chains to achieve
# the proper relative positions with minimum total motion.  It can move
# all multiscale copies of a chain.
#
# Example using dengue virus 3c6d (#2), 3c6r (#3):
#
#   play move #2:1.A #3:1.C also #2:1.C #3:1.B also #2:1.B #3:1.A
#          relative true copies true frames 50
#
# Want to use this to make an animation that reconfigures asymmetric units
# of dengue virus capsid then moves those asymmetric units to their correct
# packing.  This will be an example pathway from immature to mature form.
#
def move(g1, g2, also = [], relative = False, copies = False, frames = 25):

  gpairs = parse_group_pairs([(g1,g2)] + list(also))

  # Compute chain group motions.
  import wave
  gxfc = dict((g1,wave.chain_group_transform(g1, g2)) for g1,g2 in gpairs)

  if relative:
    g1list, g2list = zip(*gpairs)
    g1all, g2all = sum(g1list, ()), sum(g2list, ())
    xfr, center = wave.chain_group_transform(g1all, g2all)
    xfrinv = xfr.inverse()
    for xf, c in gxfc.values():
      xf.premultiply(xfrinv)

  if copies:
    gpcxf = group_pair_copies(gpairs)
    gpc = []
    from chimera import Point
    for gcpairs, xf in gpcxf:
      for (gc1,gc2),(g1,g2) in zip(gcpairs,gpairs):
        xf1, center = gxfc[g1]
        xfc = xf.inverse()
        xfc.premultiply(xf1)
        xfc.premultiply(xf)
        gxfc[gc1] = xfc, xf.apply(Point(*center)).data()
      gpc.extend(gcpairs)
    gpairs.extend(gpc)
    
  # Find chain motion for each frame.
  glayers = [[g1 for g1,g2 in gpairs]]
  fcp = wave.chain_motion_frames(glayers, gxfc, frames)

  # Register motion update handler.
  args = [(cpxflist,) for cpxflist in fcp]
  import Play
  Play.call_for_n_frames(wave.set_chain_piece_transforms, frames, args)
    
# -----------------------------------------------------------------------------
#
def parse_group_pairs(pairs):

  from Commands import CommandError
  from MultiScale import multiscale_manager as mm
  cpt = dict((cp.surface_piece.oslIdent(), cp) for cp in mm().chain_pieces())
  gpairs = []
  for f, t in pairs:
    fc, tc = f.split(','), t.split(',')
    if len(fc) != len(tc):
      raise CommandError('Different number of chains, %s and %s' % (f, t))
    try:
      gf, gt = (tuple(cpt[cp] for cp in fc), tuple(cpt[cp] for cp in tc))
    except KeyError, k:
      raise CommandError('No chain piece "%s"' % str(k))
    gpairs.append((gf,gt))

  for g1, g2 in gpairs:
    for cp1, cp2 in zip(g1,g2):
      n1 = len(cp1.lan_chain.source_atom_xyz())
      n2 = len(cp2.lan_chain.source_atom_xyz())
      if n1 != n2:
        raise CommandError('Chain %s (%d) and %s (%d) '
                           'must have same number of atoms.' %
                           (cp1.surface_piece.oslIdent(), n1,
                            cp2.surface_piece.oslIdent(), n2))
  return gpairs

# -----------------------------------------------------------------------------
#
def group_pair_copies(gpairs):

  gcpxf = []
  cpt = {}
  g1, g2 = gpairs[0]
  cp1, cp2 = g1[0], g2[0]
  cp1all = chains_in_model(cp1)
  cp2all = chains_in_model(cp2)
  xforms = relative_chain_xforms(cp1)
  from wave import group_id
  for xf in xforms:
    gcpairs = []
    for g1, g2 in gpairs:
      gc1 = tuple(chain_copy(cp,xf,cp1all) for cp in g1)
      gc2 = tuple(chain_copy(cp,xf,cp2all) for cp in g2)
      if None in gc1 or None in gc2:
        break
      gcpairs.append((gc1,gc2))
    if len(gcpairs) == len(gpairs):
      gcpxf.append((gcpairs, xf))
  return gcpxf

# -----------------------------------------------------------------------------
#
def relative_chain_xforms(cp):

  xflist = []
  cplist = chains_in_model(cp)
  cid = cp.lan_chain.chain_id
  for cp2 in cplist:
    if cp2.lan_chain.chain_id == cid and not cp2 is cp:
      xf = cp.xform.inverse()
      xf.premultiply(cp2.xform)
      xflist.append(xf)
  return xflist

# -----------------------------------------------------------------------------
#
def chains_in_model(cp):

  import MultiScale as MS
  cplist = MS.find_pieces([cp.root()], MS.Chain_Piece)
  return cplist

# -----------------------------------------------------------------------------
#
def chain_copy(cp, xf, cpall, angle_tolerance = .1, shift_tolerance = 1,
               shift_point = (0,0,0)):

  from chimera import Xform
  xfc = Xform(xf)
  xfc.multiply(cp.xform)
  cid = cp.lan_chain.chain_id
  from Matrix import same_xform
  for cpc in cpall:
    if (cpc.lan_chain.chain_id == cid and
        same_xform(cpc.xform, xfc, angle_tolerance, shift_tolerance,
                   shift_point)):
      return cpc
  return None
