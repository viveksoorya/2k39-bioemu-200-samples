#
# Add bonds between atoms of a molecule to strengthen it for 3-d printing.
#
# Algorithm is to consider every pair of CA atoms within straight line distance D of each other
# and connect them if there is currently no path between them through bonds shorter than P.
#
def brace(atoms, max_length, max_loop_length, model, task = None):

    # Find all atom pairs within distance d of each other.
    apairs = []
    for i1, a1 in enumerate(atoms):
        if task and i1 > 0 and i1 % 100 == 0:
            task.updateStatus('Struts %d of %d atoms' % (i1, len(atoms)))
        for a2 in atoms[i1+1:]:
            d12 = position(a1).distance(position(a2))
            if d12 <= max_length:
                apairs.append((d12,a1,a2))
    apairs.sort()

    from chimera import Bond
    for c, (d12, a1, a2) in enumerate(apairs):
        if task and c > 0 and c % 500 == 0:
            task.updateStatus('Evaluating struts %d of %d' % (c, len(apairs)))
        if not short_connection(a1, a2, max_loop_length):
            b = model.newPseudoBond(a1, a2)
            b.drawMode = Bond.Stick

def position(a):
    # Use Atom labelCoord() which gives position projected onto ribbon.
    return a.molecule.openState.xform.apply(a.labelCoord())

def short_connection(a1, a2, dmax,
                     pb_categories = ['struts', 'hydrogen bonds', 'distance monitor']):

    adist = {a1:0}
    bndry = set((a1,))
    while bndry:
        a = bndry.pop()
        d = adist[a]
        acon = set([(b.otherAtom(a), b.length()) for b in a.bonds if b.shown()] +
                   [(pb.otherAtom(a), pb.length()) for cat in pb_categories for pb in a.associations(cat) if pb.shown()])
        for an,blen in acon:
            dn = d + blen
            if dn <= dmax:
                if an is a2:
                    return True
                if not an in adist or adist[an] > dn:
                    adist[an] = dn
                    bndry.add(an)
    return False

def fatten_ribbon(mset):
    tw,th = .75,.75
    hw,hh = 1.5,.75
    sw,sh = 1.5,.75
    abw,abh,atw,ath = 2.5,.75,.75,.75
    nw,nh = 2.5,1.5
    dw,dh = .75,.75
    from chimera import Residue, RibbonStyleFixed, RibbonStyleTapered
    for m in mset:
        for r in m.residues:
            st = r.ribbonFindStyleType()
            if st == Residue.RS_TURN:           s = RibbonStyleFixed((tw,th))
            elif st == Residue.RS_HELIX:	s = RibbonStyleFixed((hw,hh))
            elif st == Residue.RS_SHEET:	s = RibbonStyleFixed((sw,sh))
	    elif st == Residue.RS_ARROW:	s = RibbonStyleTapered((atw,ath,abw,abh))
            elif st == Residue.RS_NUCLEIC:	s = RibbonStyleFixed((nw,nh))
	    else:			        s = RibbonStyleFixed((dw,dh))
            r.ribbonStyle = s

def fatten_bonds(mset):
    for m in mset:
        for b in m.bonds:
            b.radius = 0.5
        m.ballScale = 0.4

def struts_command(cmdname, args):

    from Commands import parse_arguments
    from Commands import atoms_arg, float_arg, color_arg, bool_arg, string_arg, model_id_arg

    req_args = ()
    opt_args = (('atoms', atoms_arg),)
    kw_args = (('length', float_arg),
               ('loop', float_arg),
               ('radius', float_arg),
               ('color', color_arg),
               ('fattenRibbon', bool_arg),
               ('replace', bool_arg),
               ('name', string_arg),
               ('modelId', model_id_arg),
               )
    kw = parse_arguments(cmdname, args, req_args, opt_args, kw_args)
    make_struts(**kw)

def unstruts_command(cmdname, args):

    from Commands import parse_arguments, atoms_arg

    req_args = ()
    opt_args = (('atoms', atoms_arg),)
    kw_args = ()
    kw = parse_arguments(cmdname, args, req_args, opt_args, kw_args)
    remove_struts(**kw)

def remove_struts(atoms = None):

    from chimera import openModels, PseudoBondGroup
    pbglist = openModels.list(modelTypes = [PseudoBondGroup])
    slist = [s for s in pbglist if s.category == 'struts']
    if atoms is None:
        openModels.close(slist)
    else:
        aset = set(atoms)
        for s in slist:
            remove = set()
            blist = s.pseudoBonds
            for b in blist:
                for a in b.atoms:
                    if a in aset:
                        remove.add(b)
                        break
            if len(remove) == len(blist):
                s.deleteAll()
            else:
                for b in remove:
                    s.deletePseudoBond(b)
        openModels.close([s for s in slist if len(s.pseudoBonds) == 0])

def strut_model(atoms, replace, name, modelId):

    pbg = None
    import hashlib, numpy
    h = hashlib.md5(numpy.array([id(a) for a in atoms])).hexdigest()
    if replace:
        from chimera import openModels, PseudoBondGroup
        bid, sid = modelId
        pbglist = openModels.list(id = bid, subid = sid,
                                  modelTypes = [PseudoBondGroup])
        mlist = [m for m in pbglist
                 if hasattr(m, 'struts_id') and m.struts_id == h]
        if mlist:
            pbg = mlist[0]
            pbg.deleteAll()

    if pbg is None:
        import chimera
        pbm = chimera.PseudoBondMgr.mgr()
        pbg = pbm.newPseudoBondGroup('struts')
        pbg.struts_id = h
        bid, sid = modelId
        chimera.openModels.add([pbg], baseId = bid, subid = sid)

    if name is None:
        name = ('%s struts' % atoms[0].molecule.name) if atoms else 'struts'
    pbg.name = name

    return pbg

from chimera import OpenModels
def make_struts(atoms, length = 7.0, loop = 30.0, radius = 0.75, color = (.7,.7,.7,1),
                fattenRibbon = True, replace = True, name = None,
                modelId = (OpenModels.Default, OpenModels.Default)):

    if len(atoms) == 0:
        from Commands import CommandError
        raise CommandError('No atoms specified')

    pbg = strut_model(atoms, replace, name, modelId)
    from chimera import CancelOperation, tasks
    task = tasks.Task('Computing struts, %d atoms' % (len(atoms),), modal = True)
    try:
        brace(atoms, length, loop, pbg, task)
    except CancelOperation:
        return None
    finally:
        task.finished()

    from chimera import MaterialColor, openModels, replyobj
    c = MaterialColor(*tuple(color))
    for b in pbg.pseudoBonds:
        b.radius = radius
        b.color = c

    msg = 'Created %d struts for %s, max length %.3g, max loop length %.3g' % (
        len(pbg.pseudoBonds), name, length, loop)
    from chimera import replyobj
    replyobj.status(msg)
    replyobj.info(msg + '\n')

    if fattenRibbon:
        mset = set(a.molecule for a in atoms)
        fatten_ribbon(mset)

    return pbg
