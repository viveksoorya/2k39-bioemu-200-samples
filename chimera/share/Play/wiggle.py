# -----------------------------------------------------------------------------
# Wave branches of a molecule at frequencies corresponding to branch size.
# A branch is an interval of residues defined by minimum and maximum residue
# number.
#

# -----------------------------------------------------------------------------
#
class branch_wiggler:

    def __init__(self, branches, angle, speed, frames):

        self.angle = angle
        self.speed = float(speed)
        self.frames = frames
        self.start_frame = None

        self.atom_indices = ai = {}
        i = 0
        for a1, a2, alist in branches:
            for a in alist:
                if not a in ai:
                    ai[a] = i
                    i += 1

        self.ibranches = [(ai[a1],ai[a2],tuple(ai[a] for a in alist))
                          for a1, a2, alist in branches]

        from numpy import empty, float32
        self.coords = c = empty((i,3), float32)
        for a,i in ai.items():
            c[i,:] = a.coord().data()

        from chimera import triggers
        self.handler = triggers.addHandler('new frame', self.frame_cb, frames)

    def frame_cb(self, tname, unused, f):

        s = self.start_frame
        if s is None:
            self.start_frame = s = f
        t = f - s
        if t >= self.frames:
            from chimera import triggers
            triggers.deleteHandler('new frame', self.handler)
            self.handler = None
        else:
            self.rotate_branches(t)

    def rotate_branches(self, frame):

        s = self.speed
        ar = self.angle
        xyz = self.coords
        frames = self.frames
        from math import sin, pi
        for i1,i2,ilist in self.ibranches:
            r = pi * int(0.5 + frames*2*s/len(ilist))/frames
            da = (sin(r*(frame+1)) - sin(r*frame)) * ar
            rotate_branch(xyz, i1, i2, ilist, da)
        self.set_atom_coordinates(xyz)

    def set_atom_coordinates(self, xyz):

        from chimera import Point
        for a,i in self.atom_indices.items():
            a.setCoord(Point(*xyz[i]))

# -----------------------------------------------------------------------------
#
def rotate_branch(coords, pivot1, pivot2, indices, angle):

    p1, p2 = coords[pivot1], coords[pivot2]
    import Matrix as M
    tf = M.rotation_transform(p2-p1, angle, p1)
    xyz = coords[indices,:]
    M.transform_points(xyz, tf)
    coords[indices,:] = xyz
    
# -----------------------------------------------------------------------------
#
def wiggle(atoms, branches = None, angle = 10, speed = 25, frames = 25):

    resranges = parse_branches(branches)
    branch_atoms = residue_range_branches(atoms, resranges)

    if branch_atoms:
        branch_wiggler(branch_atoms, angle, speed, frames)

# -----------------------------------------------------------------------------
#
def parse_branches(branches):

    from Commands import CommandError
    if branches is None:
        raise CommandError('No branches specified')
    try:
        resranges = [tuple(int(r) for r in b.split('-'))
                     for b in branches.split(',')]
    except ValueError:
        raise CommandError('Invalid branch format, require comma-separated ranges, e.g. 12-34,51-39, got "%s"' % branches)

    for rr in resranges:
        if len(rr) != 2 or rr[0] >= rr[1]:
            raise CommandError('Invalid branch format, require comma-separated ranges, e.g. 12-34,51-39, got "%s"' % branches)

    return resranges

# -----------------------------------------------------------------------------
#
def residue_range_branches(atoms, resranges):

    ratoms = [(r1,r2,[]) for r1,r2 in resranges]
    
    # Find atoms in each residue range.
    for a in atoms:
        p = a.residue.id.position
        for r1, r2, alist in ratoms:
            if p >= r1 and p <= r2:
                alist.append(a)

    branches = []
    for r1, r2, alist in ratoms:
        a1 = a2 = None
        for a in alist:
            p = a.residue.id.position
            if p == r1:
                for b in a.bonds:
                    if b.otherAtom(a).residue.id.position == r1-1:
                        a1 = a
            if p == r2:
                for b in a.bonds:
                    if b.otherAtom(a).residue.id.position == r2+1:
                        a2 = a
        if a1 is None or a2 is None or a1 == a2:
            continue
        branches.append((a1, a2, alist))

    if len(branches) < len(ratoms):
        from chimera import replyobj
        msg = ('play wiggle: %d of %d branches have no pivot atoms '
               'due to no bond to neighboring residue.' %
               (len(ratoms) - len(branches), len(ratoms)))
        replyobj.status(msg)
        replyobj.info(msg + '\n')

    return branches
