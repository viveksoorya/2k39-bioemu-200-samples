# -----------------------------------------------------------------------------
#
from Midas import MidasError as CommandError

# -----------------------------------------------------------------------------
#
def parse_arguments(cmd_name, arg_string,
                    required_args = (), optional_args = (), keyword_args = ()):

    fields = split_fields(arg_string)
    n = len(fields)
    akw = {}
    a = 0
    spec = None

    # Parse required arguments.
    for spec in required_args:
        if a >= n:
            raise CommandError, ('%s: Missing required argument "%s"'
                                 % (cmd_name, arg_specifier_name(spec)))
        a += parse_arg(fields[a:], spec, cmd_name, akw)

    # Make keyword abbreviation table.
    kw_args = tuple(optional_args) + tuple(keyword_args)
    kwnames = [arg_specifier_name(s) for s in kw_args]
    kwt = abbreviation_table(kwnames)

    # Parse optional arguments.
    for spec in optional_args:
        if a >= n or fields[a].lower() in kwt:
            break
        a += parse_arg(fields[a:], spec, cmd_name, akw)

    # Allow last positional argument to have multiple values.
    if spec:
        multiple = arg_spec(spec)[3]
        if multiple:
            while a < n and not fields[a].lower() in kwt:
                a += parse_arg(fields[a:], spec, cmd_name, akw)

    # Parse keyword arguments.
    keyword_spec = dict([(arg_specifier_name(s),s) for s in kw_args])
    while a < n:
        f = fields[a]
        fl = f.lower()
        if not fl in kwt:
            raise CommandError, '%s: Unknown keyword "%s"' % (cmd_name, f)
        spec = keyword_spec[kwt[fl]]
        a += 1 + parse_arg(fields[a+1:], spec, cmd_name, akw)
        
    return akw

# -----------------------------------------------------------------------------
#
def parse_arg(fields, spec, cmd_name, akw):

    name, parse, pkw, multiple = arg_spec(spec)

    n = len(parse) if isinstance(parse, tuple) else 1
    if len(fields) < n:
        raise CommandError('%s: Missing argument for keyword "%s"'
                           % (cmd_name, name))
    
    try:
        if isinstance(parse, tuple):
            value = True if n == 0 else tuple(p(a, **pkw)
                                              for p,a in zip(parse,fields[:n]))
        else:
            value = parse(fields[0], **pkw)
    except CommandError, e:
        args = ' '.join(f for f in fields[:n])
        raise CommandError('%s invalid %s argument "%s": %s'
                           % (cmd_name, name, args, str(e)))
    except:
        args = ' '.join(f for f in fields[:n])
        raise CommandError('%s invalid %s argument "%s"'
                           % (cmd_name, name, args))
    if multiple:
        if name in akw:
            akw[name].append(value)
        else:
            akw[name] = [value]
    else:
        akw[name] = value

    return n

# -----------------------------------------------------------------------------
# Return argument name, parsing function, parsing function keyword dictionary.
# Original specifiers can be just a name or tuple of name and parse func.
#
def arg_spec(s):

    if isinstance(s, basestring):
        s = [s]
    arg_name = s[0]
    multiple = (len(s) > 1 and s[-1] == 'multiple')
    if multiple:
        s = s[:-1]
    parse = s[1] if len(s) >= 2 else string_arg
    kw = s[2] if len(s) >= 3 else {}
    return (arg_name, parse, kw, multiple)

# -----------------------------------------------------------------------------
#
def arg_specifier_name(s):

    if isinstance(s, basestring):
        return s
    return s[0]

# -----------------------------------------------------------------------------
#
def string_arg(s):

    return s

# -----------------------------------------------------------------------------
#
def bool_arg(s):

    return s.lower() not in ('false', 'f', '0', 'no', 'n', 'off')

# -----------------------------------------------------------------------------
#
def bool3_arg(s):

    b = [bool_arg(x) for x in s.split(',')]
    if len(b) != 3:
        raise CommandError('Require 3 comma-separated values, got %d' % len(b))
    return b

# -----------------------------------------------------------------------------
#
def enum_arg(s, values, multiple = False):

    if multiple:
        e = s.split(',')
        for v in e:
            if not v in values:
                raise CommandError('Values must be in %s, got "%s"'
                                   % (', '.join(values), s))
    elif s in values:
        e = s
    else:
        raise CommandError('Value must be one of %s, got "%s"'
                           % (', '.join(values), s))
    return e

# -----------------------------------------------------------------------------
#
def float_arg(s, min = None, max = None):

    x = float(s)
    if not min is None and x < min:
        raise CommandError('Value must be >= %g, got %g' % (min, x))
    if not max is None and x > max:
        raise CommandError('Value must be <= %g, got %g' % (max, x))
    return x

# -----------------------------------------------------------------------------
#
def float3_arg(s):

    fl = [float(x) for x in s.split(',')]
    if len(fl) != 3:
        raise CommandError('Require 3 comma-separated values, got %d' % len(fl))
    return fl

# -----------------------------------------------------------------------------
#
def floats_arg(s, allowed_counts = None):

    fl = [float(x) for x in s.split(',')]
    if not allowed_counts is None and not len(fl) in allowed_counts:
        allowed = ','.join('%d' % c for c in allowed_counts)
        raise CommandError('Wrong number of values, require %s, got %d'
                           % (allowed, len(fl)))
    return fl

# -----------------------------------------------------------------------------
#
def int_arg(s):

    return int(s)

# -----------------------------------------------------------------------------
#
def int3_arg(s):

    il = [int(x) for x in s.split(',')]
    if len(il) != 3:
        raise CommandError('Require 3 comma-separated values, got %d' % len(il))
    return il

# -----------------------------------------------------------------------------
#
def ints_arg(s, allowed_counts = None):

    il = [int(x) for x in s.split(',')]
    if not allowed_counts is None and not len(il) in allowed_counts:
        allowed = ','.join('%d' % c for c in allowed_counts)
        raise CommandError('Wrong number of values, require %s, got %d'
                           % (allowed, len(il)))
    return il

# -----------------------------------------------------------------------------
#
def molecule_arg(s):

    from chimera.specifier import evalSpec
    sel = evalSpec(s)
    mlist = sel.molecules()
    if len(mlist) == 0:
        raise CommandError, 'No molecule specified'
    elif len(mlist) > 1:
        raise CommandError, 'Multiple molecules specified'
    return mlist[0]

# -----------------------------------------------------------------------------
#
def molecules_arg(s, min = 0):

    from chimera.specifier import evalSpec
    sel = evalSpec(s)
    mlist = sel.molecules()
    if len(mlist) < min:
        if len(mlist) == 0:
            raise CommandError('No molecule specified, require %d' % min)
        else:
            raise CommandError('%d molecules specified, require at least %d' % (len(mlist), min))
    return mlist

# -----------------------------------------------------------------------------
#
def atoms_arg(s):

    from chimera.specifier import evalSpec
    sel = evalSpec(s)
    alist = sel.atoms()
    return alist

# -----------------------------------------------------------------------------
#
def model_arg(s):

    from chimera.specifier import evalSpec
    sel = evalSpec(s)
    mlist = sel.models()
    if len(mlist) == 0:
        raise CommandError, 'No models specified'
    elif len(mlist) > 1:
        raise CommandError, 'Multiple models specified'
    return mlist[0]

# -----------------------------------------------------------------------------
#
def models_arg(s):

    from chimera.specifier import evalSpec
    sel = evalSpec(s)
    mlist = sel.models()
    return mlist

# -----------------------------------------------------------------------------
#
def model_id_arg(s):

    return parse_model_id(s)

# -----------------------------------------------------------------------------
#
def specifier_arg(s):

    from chimera.specifier import evalSpec
    sel = evalSpec(s)
    return sel

# -----------------------------------------------------------------------------
#
def openstate_arg(s):

    from chimera.specifier import evalSpec
    sel = evalSpec(s)
    oslist = set([m.openState for m in sel.models()])
    if len(oslist) == 0:
        raise CommandError, 'No models specified'
    elif len(oslist) > 1:
        raise CommandError, 'Multiple coordinate systems specified'
    return oslist.pop()

# -----------------------------------------------------------------------------
#
def volumes_from_specifier(spec):

    from chimera import specifier
    try:
        sel = specifier.evalSpec(spec)
    except:
        return []

    from VolumeViewer import Volume, volume_list
    vlist = [m for m in sel.models() if isinstance(m, Volume)]

    # Translate solid volume models to volume models.
    from _volume import Volume_Model
    svlist = [m for m in sel.models() if isinstance(m, Volume_Model)]
    for s in svlist:
        for v in volume_list():
            if s in v.models():
                if not v in vlist:
                    vlist.append(v)
                break

    return vlist

# -----------------------------------------------------------------------------
#
def volume_arg(v):

    vlist =  volumes_arg(v)
    if len(vlist) > 1:
        raise CommandError, 'Multiple volumes specified'
    return vlist[0]

# -----------------------------------------------------------------------------
#
def volumes_arg(v):

    from chimera.specifier import evalSpec
    sel = evalSpec(v)
    from VolumeViewer import Volume
    vlist = [m for m in sel.graphs() if isinstance(m,Volume)]
    if len(vlist) == 0:
        raise CommandError, 'No volumes specified'
    return vlist

# -----------------------------------------------------------------------------
#
def filter_volumes(models, keyword = ''):

    if keyword:
        keyword += ' '
        
    if isinstance(models, str):
        raise CommandError, 'No %svolumes specified by "%s"' % (keyword, models)
    
    from VolumeViewer import Volume
    from _volume import Volume_Model
    vids = set([v.id for v in models if isinstance(v, (Volume, Volume_Model))])
    for v in models:
        if not isinstance(v, (Volume, Volume_Model)) and not v.id in vids:
            raise CommandError, 'Model %s is not a volume' % v.name
    volumes = [v for v in models if isinstance(v, Volume)]
    if len(volumes) == 0:
        raise CommandError, 'No %svolumes specified' % keyword
    return volumes

# -----------------------------------------------------------------------------
#
def parse_floats(value, name, count, default = None):

    return parse_values(value, float, name, count, default)

# -----------------------------------------------------------------------------
#
def parse_ints(value, name, count, default = None):

    return parse_values(value, int, name, count, default)

# -----------------------------------------------------------------------------
#
def parse_values(value, vtype, name, count, default = None):

    if isinstance(value, (tuple, list)):
        vlist = value
    elif isinstance(value, basestring):
        vlist = value.split(',')
    elif value is None:
        return default
    else:
        vlist = []
    try:
        v = [vtype(c) for c in vlist]
    except:
        v = []
    if not len(v) == count:
        raise CommandError, ('%s value must be %d comma-separated numbers, got %s'
                           % (name, count, str(value)))
    return v

# -----------------------------------------------------------------------------
# Case insenstive and converts unique prefix to full string.
#
def parse_enumeration(string, strings, default = None):

    ast = abbreviation_table(strings)
    s = ast.get(string.lower(), default)
    return s

# -----------------------------------------------------------------------------
# Return table mapping unique abbreviations for names to the full name.
#
def abbreviation_table(names, lowercase = True):

    a = {}
    for name in names:
        for i in range(1,len(name)+1):
            aname = name[:i]
            if lowercase:
                aname = aname.lower()
            if aname in a:
                a[aname].append(name)
            else:
                a[aname] = [name]
    # Delete non-unique abbreviations except in case where shortest name
    # is a prefix of all names that have that abbreviation.
    for n,v in tuple(a.items()):
        shortest = min(v, key = lambda s: len(s))
        for fn in v:
            if not fn.startswith(shortest):
                del a[n]
                break
        if n in a:
            a[n] = shortest
    return a

# -----------------------------------------------------------------------------
#
def parse_model_id(modelId):

    from chimera import openModels as om
    if modelId is None:
        return (om.Default, om.Default)
    mid = None
    if isinstance(modelId, basestring):
        if modelId and modelId[0] == '#':
            modelId = modelId[1:]
        try:
            mid = tuple([int(i) for i in modelId.split('.')])
        except ValueError:
            mid = None
        if len(mid) == 1:
            mid = (mid[0], om.Default)
        elif len(mid) != 2:
            mid = None
    elif isinstance(modelId, int):
        mid = (modelId, om.Default)
    if mid is None:
        raise CommandError, 'modelId must be integer, got "%s"' % str(modelId)
    return mid

# -----------------------------------------------------------------------------
#
def parse_step(value, name = 'step', require_3_tuple = False):

    if isinstance(value, int):
        step = value
    else:
        try:
            step = parse_values(value, int, name, 3, None)
        except CommandError:
            step = parse_values(value, int, name, 1, None)[0]
    if require_3_tuple and isinstance(step, int):
        step = (step, step, step)
    return step

# -----------------------------------------------------------------------------
#
def parse_subregion(value, name = 'subregion'):

    if value.count(',') == 0:
        r = value       # Named region.
    else:
        s6 = parse_values(value, int, name, 6, None)
        r = (s6[:3], s6[3:])
    return r

volume_region_arg = parse_subregion

# -----------------------------------------------------------------------------
#
def parse_rgba(color):

    from chimera import MaterialColor
    if isinstance(color, MaterialColor):
        rgba = color.rgba()
    elif isinstance(color, (tuple,list)):
        rgba = color
    else:
        raise CommandError, 'Unknown color "%s"' % str(color)
    return rgba

# -----------------------------------------------------------------------------
#
def check_number(value, name, type = (float,int), allow_none = False,
                 positive = False, nonnegative = False):

    if allow_none and value is None:
        return
    if not isinstance(value, type):
        raise CommandError, '%s must be number, got "%s"' % (name, str(value))
    if positive and value <= 0:
        raise CommandError, '%s must be > 0' % name
    if nonnegative and value < 0:
        raise CommandError, '%s must be >= 0' % name

# -----------------------------------------------------------------------------
#
def check_in_place(inPlace, volumes):

    if not inPlace:
        return
    nwv = [v for v in volumes if not v.data.writable]
    if nwv:
        names = ', '.join([v.name for v in nwv])
        raise CommandError, "Can't modify volume in place: %s" % names

# -----------------------------------------------------------------------------
#
def check_matching_sizes(v1, v2, step, subregion, operation):

    if v1.data.size != v2.data.size:
        raise CommandError, 'Cannot %s grids of different size' % operation
    if step or subregion:
        from VolumeViewer import volume
        if not volume.same_region(v1.region, v2.region):
            raise CommandError, 'Cannot %s grids with different subregions' % operation

# -----------------------------------------------------------------------------
#
def surfaces_arg(s):

    from chimera.specifier import evalSpec
    sel = evalSpec(s)
    surfs = filter_surfaces(sel.models())
    return surfs

# -----------------------------------------------------------------------------
#
def filter_surfaces(surfaces):
    
    from _surface import SurfaceModel
    surfs = set([s for s in surfaces if isinstance(s, SurfaceModel)])
    if len(surfs) == 0:
        raise CommandError, 'No surfaces specified'
    return surfs

# -----------------------------------------------------------------------------
#
def surface_pieces_arg(spec):

    from chimera.specifier import evalSpec
    sel = evalSpec(spec)
    import Surface
    plist = Surface.selected_surface_pieces(sel)
    return plist

# -----------------------------------------------------------------------------
#
def single_volume(mlist):

    if mlist is None:
        return mlist
    vlist = filter_volumes(mlist)
    if len(vlist) != 1:
        raise CommandError, 'Must specify only one volume'
    return vlist[0]

# -----------------------------------------------------------------------------
#
def surface_center_axis(surf, center, axis, csys):

    if center is None:
        have_box, box = surf.bbox()
        if have_box:
            c = box.center()
        else:
            from chimera import Point
            c = Point(0,0,0)
    elif csys:
        sixf = surf.openState.xform.inverse()
        c = sixf.apply(csys.xform.apply(center))
    else:
        c = center

    if axis is None:
        from chimera import Vector
        a = Vector(0,0,1)
    elif csys:
        sixf = surf.openState.xform.inverse()
        a = sixf.apply(csys.xform.apply(axis))
    else:
        a = axis

    return c.data(), a.data()

# -----------------------------------------------------------------------------
#
def parse_vector(varg, cmdname):

    from Commands import parse_axis
    v, axis_point, csys = parse_axis(varg, cmdname)
    if csys:
        v = csys.xform.apply(v)
    vc = v.data()
    return vc

# -----------------------------------------------------------------------------
# The returned center and axis are in csys coordinates.
#
def parse_center_axis(center, axis, csys, cmdname):

    from Commands import parseCenterArg, parse_axis

    if isinstance(center, (tuple, list)):
        from chimera import Point
        center = Point(*center)
        ccs = csys
    elif center:
        center, ccs = parseCenterArg(center, cmdname)
    else:
        ccs = None

    if isinstance(axis, (tuple, list)):
        from chimera import Vector
        axis = Vector(*axis)
        axis_point = None
        acs = csys
    elif axis:
        axis, axis_point, acs = parse_axis(axis, cmdname)
    else:
        axis_point = None
        acs = None

    if not center and axis_point:
        # Use axis point if no center specified.
        center = axis_point
        ccs = acs

    # If no coordinate system specified use axis or center coord system.
    cs = (ccs or acs)
    if csys is None and cs:
        csys = cs
        xf = cs.xform.inverse()
        if center and not ccs:
            center = xf.apply(center)
        if axis and not acs:
            axis = xf.apply(axis)

    # Convert axis and center to requested coordinate system.
    if csys:
        xf = csys.xform.inverse()
        if center and ccs:
            center = xf.apply(ccs.xform.apply(center))
        if axis and acs:
            axis = xf.apply(acs.xform.apply(axis))

    return center, axis, csys

# -----------------------------------------------------------------------------
#
def parse_colormap(cmap, cmapRange, reverseColors):

    if not isinstance(cmap, basestring):
        raise CommandError, 'Invalid colormap specification: "%s"' % repr(cmap)

    pname = {'redblue': 'red-white-blue',
             'rainbow': 'rainbow',
             'gray': 'grayscale',
             'cyanmaroon': 'cyan-white-maroon'}
    if cmap.lower() in pname:
        from SurfaceColor import standard_color_palettes as scp
        rgba = scp[pname[cmap.lower()]]
        n = len(rgba)
        cmap = [(c/float(n-1),rgba[c]) for c in range(n)]
        if not cmapRange:
            cmapRange = 'full'
    else:
        vclist = cmap.split(':')
        if len(vclist) < 2:
            raise CommandError, 'Invalid colormap specification: "%s"' % cmap
        cmap = [parse_value_color(vc) for vc in vclist]

    if cmapRange:
        cmrerr = 'cmapRange must be "full" or two numbers separated by a comma'
        if not isinstance(cmapRange, basestring):
            raise CommandError, cmrerr

        if cmapRange.lower() == 'full':
            cmapRange = cmapRange.lower()
        else:
            try:
                cmapRange = [float(x) for x in cmapRange.split(',')]
            except ValueError:
                raise CommandError, cmrerr
            if len(cmapRange) != 2:
                raise CommandError, cmrerr

    if reverseColors:
        n = len(cmap)
        cmap = [(cmap[c][0],cmap[n-1-c][1]) for c in range(n)]

    return cmap, cmapRange

# -----------------------------------------------------------------------------
#
def parse_value_color(vc):

    err = 'Colormap entry must be value,color: got "%s"' % vc
    svc = vc.split(',',1)
    if len(svc) != 2:
        raise CommandError, err
    try:
        v = float(svc[0])
    except ValueError:
        raise CommandError, err
    from Commands import convertColor
    try:
        c = convertColor(svc[1]).rgba()
    except:
        raise CommandError, err
    return v, c

# -----------------------------------------------------------------------------
#
def parse_color(color):

    if isinstance(color, (tuple, list)):
        if len(color) == 4:
            return tuple(color)
        elif len(color) == 3:
            return tuple(color) + (1,)
    from Commands import convertColor
    try:
        c = convertColor(color).rgba()
    except:
        raise CommandError, 'Unrecognized color: "%s"' % repr(color)
    return c

color_arg = parse_color

# -----------------------------------------------------------------------------
#
def perform_operation(cmdname, args, ops):

    abbr = abbreviation_table(ops.keys())

    alist = args.split()
    a0 = alist[0].lower() if alist else None
    if not a0 in abbr:
        opnames = ops.keys()
        opnames.sort()
        raise CommandError('First argument must be one of %s'
                           % ', '.join(opnames))

    f, req_args, opt_args, kw_args = ops[abbr[a0]]
    kw = parse_arguments(cmdname, args[len(a0):], req_args, opt_args, kw_args)
    f(**kw)

# -----------------------------------------------------------------------------
#
def multiscale_surface_pieces_arg(spec):

    from Commands import CommandError

    mspec = spec[:spec.find(':')] if ':' in spec else spec
    from chimera.specifier import evalSpec
    from _surface import SurfaceModel
    slist = [m for m in evalSpec(mspec).models() if isinstance(m, SurfaceModel)]
    if len(slist) == 0:
        raise CommandError('No surface models specified by "%s"' % spec)

    plist = sum([list(s.surfacePieces) for s in slist], [])

    if len(mspec) < len(spec):
        pspec = spec[len(mspec)+1:]
        try:
            pspecs = piece_specs(pspec)
        except:
            raise
            raise CommandError('Invalid surface piece specifier "%s"' % pspec)
        plist = [p for p in plist if matching_piece_spec(p, pspecs)]

    return plist

# -----------------------------------------------------------------------------
#
def piece_specs(pspec):

    pspecs = pspec.split(',')
    prlist = []
    for s in pspecs:
        nc = s.split('.')
        if len(nc) == 1:
            nc.append('')
        n,c = nc
        if len(n) == 0:
            nr = (None, None)
        else:
            nr = [int(i) for i in n.split('-')]
            if len(nr) == 1:
                nr = nr*2
        if len(c) == 0:
            cr = (None, None)
        else:
            cr = c.split('-')
            if len(cr) == 1:
                cr = cr*2
        prlist.append((nr,cr))
    return prlist

# -----------------------------------------------------------------------------
#
def matching_piece_spec(p, pspecs):

    nc = p.oslName.split('.')
    if len(nc) != 2:
        return False
    n,c = nc
    try:
        n = int(n)
    except ValueError:
        return False
    for (nmin,nmax), (cmin,cmax) in pspecs:
        if ((nmin is None or n >= nmin) and (nmax is None or n <= nmax) and
            (cmin is None or c >= cmin) and (cmax is None or c <= cmax)):
            return True
    return False

# -----------------------------------------------------------------------------
# Handle quoted sub-strings.
#
def split_fields(s):

    if s.find('"') == -1 and s.find("'") == -1:
        fields = s.split()
    else:
        fields = []
        rest = s
        while rest:
            f, rest = split_first(rest)
            if f:
                fields.append(f)
    return fields

# -----------------------------------------------------------------------------
# Parse first white space delimited word handling quotes if present.
# Quotes are removed.
#
def split_first(s):

    t = s.lstrip()
    if t and t[0] in ('"', "'"):
        e = t[1:].find(t[0] + " ")
        if e >= 0:
            return t[1:e+1], t[e+2:]
        elif t[-1] == t[0]:
            return t[1:-1], ''
    return (t.split(None, 1) + ['', ''])[:2]
