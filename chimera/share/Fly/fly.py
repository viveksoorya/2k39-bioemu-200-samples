# -----------------------------------------------------------------------------
# Command to smoothly interpolate between saved model positions and
# orientations and camera settings.
#
#  Syntax: fly [frames] <posname1> [frames1] <posname2> [frames2] ... <posnameN>
#
# This is similar to the reset command but performs cubic
# interpolation instead of piecewise linear interpolation and provides
# a more convenient syntax for motion through several positions.
#
from Midas import MidasError
def fly_command(cmdname, args):

    fields = args.split()
    if len(fields) < 1:
        raise MidasError, 'Syntax: fly [frames] <posname1> [frames1] <posname2> [frames2] ... <posnameN>'

    framestep = 1
    pnames = []
    frames = []
    for f, arg in enumerate(fields):
        try:
            c = int(arg)
        except ValueError:
            pnames.append(arg)
            frames.append(framestep)
        else:
            if f == 0:
                framestep = c
            elif frames:
                frames[-1] = c
    frames = frames[:-1]

    if len(pnames) == 0:
        raise MidasError('fly: No positions specified')
    from Midas import positions, savepos
    if 'start' in pnames:
        savepos('start')
    for pname in pnames:
        if not pname in positions:
            raise MidasError, 'fly: Unknown position name "%s"' % pname

    params, open_states = view_parameters(pnames)
    from VolumePath import spline
    fparams = spline.natural_cubic_spline(params, frames)

    Fly_Playback(fparams, open_states)

# -----------------------------------------------------------------------------
#
def view_parameters(pnames):

    from Midas import positions, MidasError
    from chimera import openModels as om

    # Get list of open states.
    idos = {}
    for pname in pnames:
        for mid in positions[pname][5].keys():
            try:
                idos[mid] = om.openState(*mid)
            except ValueError:
                pass
    open_states = list(set(idos.values()))

    # Check if all positions contain the same set of open states.
    for pname in pnames:
        osp = set([idos[mid] for mid in positions[pname][5].keys()
                   if mid in idos])
        if len(osp) < len(open_states):
            id,subid = [mid for mid,os in idos.items() if not os in osp][0]
            raise MidasError, 'fly: position %s does not contain model #%d.%d' % (pname, id, subid)
        
    # Set initial position.
    for mid,xf in positions[pnames[0]][5].items():
        if mid in idos:
            idos[mid].xform = xf

    # Find center of rotation.  Same center used for all models.
    from chimera import openModels as om
    have_sphere, s = om.bsphere()
    if not have_sphere:
        raise MidasError, 'fly: Nothing displayed to calculate center of rotation'
    center = s.center

    # Create camera/position/orientation parameter array for interpolation
    from chimera import viewer
    fov = viewer.camera.fieldOfView
    from numpy import empty, float32, dot
    from math import log
    osxf = {}
    params = empty((len(pnames),9+10*len(open_states)), float32)
    for i,pname in enumerate(pnames):
        pp = positions[pname]
        vscale, vsize, ccenter, cnearfar, cfocal, xforms = pp[:6]
        fov = pp[10] if len(pp) >= 11 else fov
        p = params[i,:]
        p[0] = log(vscale)
        p[1] = log(vsize)
        p[2:5] = ccenter
        p[5:7] = cnearfar
        p[7] = cfocal
        p[8] = fov
        for mid, xf in xforms.items():
            if mid in idos:
                osxf[idos[mid]] = xf
        for oi, o in enumerate(open_states):
            pxf = p[9 + oi*10:]
            c = o.xform.inverse().apply(center)
            rotq, trans = xform_parameters(osxf[o], c)
            if i > 0:
                # Choose quaternion sign for shortest interpolation path.
                rotq_prev = params[i-1,9+oi*10:13+oi*10]
                if dot(rotq, rotq_prev) < 0:
                    rotq = [-q for q in rotq]
            pxf[0:4] = rotq
            pxf[4:7] = c
            pxf[7:10] = trans

    return params, open_states

# -----------------------------------------------------------------------------
#
fly_set = set()
class Fly_Playback:

    def __init__(self, frame_params, open_states):

        self.frame_count = 0
        self.frame_params = frame_params
        self.open_states = open_states
        from chimera import triggers as t
        self.handler = t.addHandler('new frame', self.new_frame_cb, None)
        global fly_set
        fly_set.add(self)

    def new_frame_cb(self, tname, cdata, tdata):

        fc = self.frame_count
        self.frame_count += 1
        fp = self.frame_params
        if fc >= len(fp):
            from chimera import triggers as t
            self.handler = t.deleteHandler('new frame', self.handler)
            global fly_set
            fly_set.remove(self)
            return

        # Camera parameters
        from chimera import Point, viewer as v
        from math import exp
        c = v.camera
        cp = fp[fc][:9]
        v.setViewSizeAndScaleFactor(exp(cp[1]), exp(cp[0]))
        c.center = tuple(cp[2:5])
        c.nearFar = tuple(cp[5:7])
        c.focal = cp[7]
        c.fieldOfView = max(0.01,min(cp[8],179.99))
                    
        # Model positions
        for i,os in enumerate(self.open_states):
            if os.__destroyed__:
                continue
            op = fp[fc][10*i+9:10*i+19]
            rotq = op[0:4]
            rotc = op[4:7]
            trans = op[7:10]
            os.xform = parameter_xform(rotq, rotc, trans)

# -----------------------------------------------------------------------------
# Used by wait command to determine how many frames to wait.
#
def frames_left():

    global fly_set
    fl = max([len(f.frame_params) - f.frame_count for f in fly_set] + [0])
    return fl
    
# -----------------------------------------------------------------------------
# Convert Xform to quaternion and translation.
#
def xform_parameters(xf, rotc):

    t = xf.getTranslation()
    from chimera import Vector
    c = Vector(*rotc)
    trans = t - c + xf.apply(c)
    axis, angle = xf.getRotation()
    from math import pi, sin, cos
    a = angle * pi/180
    sa2 = sin(a/2)
    ca2 = cos(a/2)
    rotq = (sa2*axis[0], sa2*axis[1], sa2*axis[2], ca2)
    return rotq, trans.data()

# -----------------------------------------------------------------------------
# Convert quaternion, rotation center and translation to an Xform.
#
def parameter_xform(rotq, rotc, trans):

    import Matrix as m
    ttf = m.translation_matrix(trans)
    sa2 = m.norm(rotq[:3])
    ca2 = rotq[3]
    from math import atan2, pi
    angle = 2*atan2(sa2,ca2) * 180.0/pi
    axis = m.normalize_vector(rotq[:3])
    rtf = m.rotation_transform(axis, angle, rotc)
    tf = m.multiply_matrices(ttf, rtf)
    xf = m.chimera_xform(tf)
    return xf
