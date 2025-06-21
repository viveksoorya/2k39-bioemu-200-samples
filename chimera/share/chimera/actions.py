# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: actions.py 37635 2012-10-29 19:01:13Z pett $

import chimera
from chimera import selection

def selAtoms(noneReturnsAll=True, implied=False, create=False):
	atoms = selection.currentAtoms()
	extendSelection(atoms, 'atoms', noneReturnsAll, implied, create)
	return atoms
			
def selBonds(noneReturnsAll=True, implied=False, create=False):
	bonds = selection.currentBonds()
	extendSelection(bonds, 'bonds', noneReturnsAll, implied, create)
	return bonds
			
def selResidues(noneReturnsAll=True, implied=False, create=False):
	residues = selection.currentResidues()
	extendSelection(residues, 'residues', noneReturnsAll, implied, create)
	return residues

def selMolecules(noneReturnsAll=True, implied=False, create=False):
	mol = selection.currentMolecules()
	extendSelection(mol, 'molecules', noneReturnsAll, implied, create)
	return mol

def selModels(noneReturnsAll=True, hidden=False, types=[]):
	models = selection.currentGraphs()
	if types:
		models = [m for m in models if isinstance(m, tuple(types))]
	if not models and noneReturnsAll and selection.currentEmpty():
		return chimera.openModels.list(all=hidden, modelTypes=types)
	return models

# Object name can be "atoms", "bonds", "residues", or "molecules"
def extendSelection(objects, objectName, noneReturnsAll=True,
		    implied=False, create=False):
	if not objects and noneReturnsAll and selection.currentEmpty():
		objects.extend(allObjects(objectName))
	elif implied:
		addImpliedSelection(objects, objectName, create, noneReturnsAll)

# Object name can be "atoms", "bonds", "residues", or "molecules"
def allObjects(objectName):
	mols = molecules()
	if objectName == 'molecules':
		return mols
	olist = []
	for m in mols:
		olist.extend(getattr(m, objectName))
	return olist

# Object name can be "atoms", "bonds", "residues", or "molecules"
def addImpliedSelection(objects, objectName, create=False, noneReturnsAll=True):
	plist = selectedSurfacePieces(excludeMSMS = True,
				      noneReturnsAll = noneReturnsAll)
	atoms, bonds = surfacePieceAtomsAndBonds(plist, create)
	if objectName == 'atoms':
		objects.extend(atoms)
	elif objectName == 'bonds':
		objects.extend(bonds)
	elif objectName == 'residues':
		objects.extend(set([a.residue for a in atoms]))
	elif objectName == 'molecules':
		objects.extend(set([a.molecule for a in atoms]))

def setDisplay(val):
	for a in selAtoms(implied = True, create = val):
		a.display = val

def showOnly():
	shownAtoms = set(selAtoms(implied = True, create = True))
	for m in molecules():
		for a in m.atoms:
			a.display = a in shownAtoms

_firstRibbonDraw = True
def setResidueDisplay(val):
	mset = set()
	for r in selResidues(implied = True, create = val):
		r.ribbonDisplay = val
		mset.add(r.molecule)
	anyRibbon = False
	for m in mset:
		if m.updateRibbonData():
			anyRibbon = True
	if not anyRibbon:
		from chimera import replyobj
		replyobj.warning("no residues with ribbons found")
	global _firstRibbonDraw
	if _firstRibbonDraw and val:
		from chimera import replyobj
		_firstRibbonDraw = False
		replyobj.status("Ribbon appearance can be fine-tuned with Tools/Depiction/Ribbon Style Editor")

def displayResPart(side=0, backbone=0, other=0, trace=0, add=0):
	from misc import displayResPart
	displayResPart(selResidues(implied = True),
		       side=side, backbone=backbone,
		       other=other, trace=trace, add=add)

def setAtomBondDraw(aMode, bMode):
	for a in selAtoms(implied = True):
		a.drawMode = aMode
	for b in selBonds(implied = True):
		b.drawMode = bMode

# Set linewidth of molecule bonds
def setLineWidth(lw):
	for m in selMolecules(implied = True):
		m.lineWidth = lw

def delAtomsBonds():
	from Midas import deleteAtomsBonds
	deleteAtomsBonds(selAtoms(implied = True), selBonds(implied = True))

def setRibbonDraw(rMode):
	for r in selResidues(implied = True):
		r.ribbonDrawMode = rMode

def setRibbonCustom(xs):
	for r in selResidues(implied = True):
		r.ribbonDrawMode = r.Ribbon_Custom
		r.ribbonXSection = xs

def setColor(color, appliesToVar = None):
	if appliesToVar is None:
		at = 'all'
	else:
		at = appliesToVar.get()
	if at == "all":
		alist = selAtoms()
		for a in alist:
			a.color = color
			a.surfaceColor = color
			a.labelColor = color
		for b in selBonds():
			b.color = color
			b.labelColor = color
		for r in selResidues():
			r.ribbonColor = color
			r.labelColor = color
		mlist = set(a.molecule for a in alist)
		changeSurfsFromCustom(mlist)
		colorSelectedSurfaces(color)
		for vrml in selModels(types=[chimera.VRMLModel], hidden=True):
			vrml.color = color
	elif at == "ribbons":
		for r in selResidues():
			r.ribbonColor = color
	elif at == "ribbon inside":
		for m in selMolecules():
			m.ribbonInsideColor = color
	elif at == "atoms/bonds":
		for a in selAtoms():
			a.color = color
		for b in selBonds():
			b.color = color
	elif at == "bg":
		import Midas
		Midas.background(color=color)
	elif at == "dc":
		from tkgui import app
		app.viewer.depthCueColor = color
	elif at == "residue labels":
		for r in selResidues():
			r.labelColor = color
	elif at == "atom labels":
		for a in selAtoms():
			a.labelColor = color
	elif at == "bond labels":
		for b in selBonds():
			b.labelColor = color
	elif at == "surfaces":
		alist = selAtoms()
		for a in alist:
			a.surfaceColor = color
		mlist = set(a.molecule for a in alist)
		changeSurfsFromCustom(mlist)
		colorSelectedSurfaces(color)

def colorSelectedSurfaces(color):
	plist = selectedSurfacePieces()

	# Stop current auto-coloring
	from chimera import MSMSModel
	from Surface import set_coloring_method
	for s in set([p.model for p in plist]):
		if not isinstance(s, MSMSModel):
			set_coloring_method('single', s)

	if color is None: rgba = None
	else:             rgba = tuple(color.rgba())

	for p in plist:
		m = p.model
		if isinstance(m, MSMSModel) and p == m.surface_piece:
			colorMSMSSurface(m, color)
		else:
			p.vertexColors = None
			if rgba:
				p.color = rgba

def colorMSMSSurface(s, color):
	if s.colorMode == s.Custom or s.molecule is None:
		if not color is None:
			import Surface
			Surface.set_coloring_method('static', s, None)
			s.customColors = s.vertexCount * [color]
	elif s.colorMode == s.ByMolecule:
		s.molecule.surfaceColor = color
	elif s.colorMode == s.ByAtom:
		for a in s.atoms:
			a.surfaceColor = color

def colorByElement(attr=None, appliesToVar=None, hetero=False):
	if attr:
		attrs = [attr]
	elif appliesToVar:
		appliesTo = appliesToVar.get()
		if appliesTo == "atoms/bonds":
			attrs=["color"]
		elif appliesTo == "surfaces":
			attrs = ["surfaceColor"]
		elif appliesTo in ["labels", "atom labels"]:
			attrs = ["labelColor"]
		elif appliesTo == "all":
			attrs = ["color", "surfaceColor", "labelColor"]
		else:
			from chimera import UserError
			raise UserError(
				"Nothing applicable to color by element")
		if "surfaceColor" in attrs:
			changeSurfsFromCustom()
	else:
		attrs = ["color", "surfaceColor", "labelColor"]
	for a in selAtoms():
		colorAtomByElement(a, attrs=attrs, hetero=hetero)
	
def changeSurfsFromCustom(mlist=None):
	"""turn off custom coloring for selected surfaces"""
	if mlist is None:
		mlist = selMolecules()
	mset = set(mlist)
	from chimera import MSMSModel
	for surf in chimera.openModels.list(modelTypes=[MSMSModel]):
		if surf.colorMode == MSMSModel.Custom and surf.molecule in mset:
			surf.colorMode = MSMSModel.ByAtom

def colorAtomByElement(a, attrs=["color"], hetero=False):
	import Midas
	if hetero and a.element.number == chimera.elements.C.number:
		return
	c = Midas.elementColor(a.element)
	for attr in attrs:
		setattr(a, attr, c)

def setLabel(attr, fixed=0, warnLarge=True):
	if warnLarge and attr is not None:
		labeled = [a for a in selAtoms() if a.display]
		numLabeled = len(labeled)
		if numLabeled > 100:
			# also more than one per residue?
			# (use 1.5 per residue to allow for 
			# alternate atom locations in some residues)
			residues = selResidues()
			if numLabeled > 1.5 * len(residues):
				import tkgui
				tkgui.LabelWarningDialog(numLabeled,
					lambda : setLabel(
					attr, fixed, warnLarge=False))
				return
				
	def labelAtomBond(ab, fixed=fixed, attr=attr):
		if fixed:
			label = attr
		elif attr is None:
			label = ""
		elif callable(attr):
			label = attr(ab)
		else:
			try:
				obj = ab
				for curattr in attr.split('.'):
					obj = getattr(obj, curattr)
				if callable(obj):
					label = obj()
				else:
					label = obj
				if not isinstance(label, basestring):
					try:
						label = "%g" % label
					except:
						label = str(label)
			except AttributeError:
				label = ""
		ab.label = label
	for a in selAtoms():
		labelAtomBond(a)
	for b in selBonds():
		labelAtomBond(b)

def setResLabel(labelFmt, selection=selection):
	from Midas import ResAttrDict
	from chimera import UserError
	for r in selResidues():
		try:
			r.label = labelFmt % ResAttrDict(r, UserError)
		except (TypeError, ValueError):
			raise UserError("Bad label format\n"
				"Use label dialog's Help button for explanation of formatting")

def focus():
	from chimera import openModels as om
	if selection.currentEmpty():
		sel = '#'
		from chimera import viewing, viewer
		if om.cofrMethod != om.Independent:
			om.cofrMethod = viewing.defaultCofrMethod
		viewer.clipping = False
	else:
		disped = [x for x in selAtoms() + selBonds() if x.shown()]
		for p in selectedSurfacePieces():
			if p.display and p.model.display and p.triangleCount > 0:
				if isinstance(p.model, chimera.MSMSModel):
					disped.extend([a for a in p.model.atoms if a.surfaceDisplay])
				else:
					disped.append(p)
		if not disped:
			from chimera import replyobj
			replyobj.error(
				"No target atoms/bonds/ribbons/surfaces currently shown\n")
			return
		sel = selection.ItemizedSelection()
		sel.add(disped)
		sel.addImplied(edges=False)
		if om.cofrMethod != om.Independent:
			om.cofrMethod = om.CenterOfView
	from Midas import window
	window(sel)

def setPivot():
	atoms = selAtoms(noneReturnsAll = False)
	plist = selectedSurfacePieces(noneReturnsAll = False)
	sel = selection.ItemizedSelection()
	sel.add(atoms)
	sel.add(plist)
	from Midas import cofr, uncofr
	if len(sel) > 0:
		cofr(sel)
	else:
		uncofr()

def setSurfaceRepr(srMode):
	cats = set()
	for a in selAtoms():
		cats.add((a.molecule, a.surfaceCategory))
	for s in chimera.openModels.list(modelTypes=[chimera.MSMSModel]):
		if (s.molecule, s.category) in cats:
			s.drawMode = srMode
	plist = selectedSurfacePieces(implied = True)
	if plist:
		from chimera import MSMSModel
		p = plist[0]
		style = {MSMSModel.Filled: p.Solid,
			 MSMSModel.Mesh: p.Mesh,
			 MSMSModel.Dot: p.Dot}[srMode]
		for p in plist:
			p.displayStyle = style
			
def showSurface(warnLarge=True):
	if warnLarge:
		numSurfaces = len(selMolecules())
		if numSurfaces > 20:
			import tkgui
			tkgui.SurfaceWarningDialog(numSurfaces,
				lambda : showSurface(warnLarge=False))
			return
	empty = selection.currentEmpty()
	atoms = selAtoms()
	plist = selectedSurfacePieces(implied = True)
	if plist:
		pa, pb = surfacePieceAtomsAndBonds(plist)
		if pa:
			# Don't surface atoms that have non-MSMS surface.
			paset = set(pa)
			atoms = [a for a in atoms if a not in paset]
	for p in plist:
		p.display = True
		p.model.display = True
	from Midas import surfaceNew
	molcat = list(set([(a.molecule, a.surfaceCategory) for a in atoms]))
	if empty:
		# Only surface main category if nothing selected.
		molcat = [mc for mc in molcat if mc[1] == 'main']
		atoms = [a for a in atoms if a.surfaceCategory == 'main']
	# turn on display this late to avoid re-showing hidden surfaces in
	# wrong categories
	for a in atoms:
		a.surfaceDisplay = True
	import Midas
	Midas.surfaceVisibilityByAtom(atoms)
	molcat.sort(lambda mc1,mc2: cmp(mc1[0].id, mc2[0].id))
	for mol, cat in molcat:
		surfaceNew(cat, models=[mol])
		
def hideSurface():
	atoms = selAtoms()
	for a in atoms:
		a.surfaceDisplay = False
	import Midas
	Midas.surfaceVisibilityByAtom(atoms)
	plist = selectedSurfacePieces(excludeMSMS = True, implied = True)
	for p in plist:
		p.display = False
	# Undisplay models that have all pieces undisplayed.
	for s in set([p.model for p in plist]):
		if not [p for p in s.surfacePieces if p.display]:
			s.display = False

def transpSurf(amount):
	notrans = (amount == -1)
	opacity = 1 if notrans else min(1.0, 1 - amount)
	atoms = selAtoms()
	import Midas
	surfatoms = Midas.atomMSMSModels(atoms)
	for s,atoms in surfatoms.items():
		adjustMSMSTransparency(s, atoms, opacity, notrans)

	splist = selectedSurfacePieces(implied = True)
	from chimera import MSMSModel
	from SurfaceCap import is_surface_cap
	for p in splist:
		s = p.model
		if (isinstance(s, MSMSModel) and s.molecule and
		    not is_surface_cap(p)):
			adjustMSMSTransparency(s, s.atoms, opacity, notrans)
		else:
			adjustSurfacePieceTransparency(p, opacity)

	if (len(atoms) > 0 and not selection.currentEmpty()
	    and len(surfatoms) == 0 and len(splist) == 0):
		from replyobj import warning
		warning('No surfaces shown for selected atoms.\n')

def adjustMSMSTransparency(s, atoms, opacity, notrans = False, frac = 1):

	if s.colorMode == s.Custom:
		# Change transparency of just the atom vertices.
		vrgba = s.customRGBA
		if vrgba is None:
			return
		if s.atomMap is None:
			if frac == 1:
				vrgba[:,3] = opacity
			else:
				vrgba[:,3] *= 1-frac
				vrgba[:,3] += frac*opacity
		else:
			aset = set(atoms)
			av = [i for i,a in enumerate(s.atomMap) if a in aset]
			if frac == 1:
				vrgba[av,3] = opacity
			else:
				vrgba[av,3] *= 1-frac
				vrgba[av,3] += frac*opacity
		import Surface
		Surface.set_coloring_method('static', s, None)
		s.customRGBA = vrgba
        elif s.colorMode == s.ByMolecule:
		m = s.molecule
		if notrans and frac == 1:
			m.surfaceOpacity = -1
		else:
			mopac = m.surfaceOpacity
			if mopac < 0:
				mopac = m.color.rgba()[3]
			m.surfaceOpacity = frac*opacity + (1-frac)*mopac
	elif s.colorMode == s.ByAtom:
		opac = -1 if notrans else opacity
		for a in atoms:
			aop = a.surfaceOpacity
			if aop < 0:
				aop = 1
			a.surfaceOpacity = frac*opac + (1-frac)*aop

def adjustAtomsSurfaceOpacity(atoms, opac, frac):

	if opac is None:
		if frac == 1:
			for a in atoms:
				a.surfaceOpacity = -1.0
		else:
			for a in atoms:
				asop, aop = _atomSurfaceOpacity(a)
				a.surfaceOpacity = frac*aop + (1-frac)*asop
	elif frac == 1:
		for a in atoms:
			a.surfaceOpacity = opac
	else:
		for a in atoms:
			asop, aop = _atomSurfaceOpacity(a)
			a.surfaceOpacity = frac*opac + (1-frac)*asop

def _atomSurfaceOpacity(atom):

	c = atom.surfaceColor
	if c is None:
		c = atom.molecule.color
	aop = c.opacity
	asop = atom.surfaceOpacity
	if asop < 0:
		asop = aop
	return asop, aop

def adjustSurfacePieceTransparency(p, opacity, frac = 1):

	vrgba = p.vertexColors
	if vrgba is None:
		rgba = list(p.color)
		rgba[3] = frac*opacity + (1-frac)*rgba[3]
		p.color = tuple(rgba)
	else:
		import Surface
		Surface.set_coloring_method('static', p.model, None)
		vrgba[:,3] *= 1-frac
		vrgba[:,3] += frac*opacity
		p.vertexColors = vrgba

def molecules():
	return chimera.openModels.list(modelTypes=[chimera.Molecule])

def selectedSurfacePieces(excludeMSMS = False, noneReturnsAll = True,
			  implied = False):
	import Surface
	if noneReturnsAll and selection.currentEmpty():
		plist = Surface.all_surface_pieces()
	else:
		plist = Surface.selected_surface_pieces()
		if implied and surfacesWithAtomsAndBonds():
			atoms = selAtoms(noneReturnsAll)
			bonds = selBonds(noneReturnsAll)
			pset = set(plist)
			pab = atomAndBondSurfacePieces(atoms, bonds)
			plist.extend([p for p in pab if p not in pset])
	if excludeMSMS:
		plist = [p for p in plist
			 if (not isinstance(p.model, chimera.MSMSModel)
			     or p.model.molecule is None)]
	return plist

def surfacePieceAtomsAndBonds(plist, create = False):
	surfs = {}
	for p in plist:
		s = p.model
		if s not in surfs:
			surfs[s] = set()
		surfs[s].add(p)
	atoms = []
	bonds = []
	for s, pieces in surfs.items():
		ab = getattr(s, 'surfacePieceAtomsAndBonds', None)
		if ab:
			a, b = ab(list(pieces), create = create)
			atoms.extend(a)
			bonds.extend(b)
	return atoms, bonds

def atomAndBondSurfacePieces(atoms, bonds):
	plist = []
	for s in surfacesWithAtomsAndBonds():
		plist.extend(s.atomAndBondSurfacePieces(atoms, bonds))
	return plist

def surfacesWithAtomsAndBonds():
	from _surface import SurfaceModel
	surfs = chimera.openModels.list(modelTypes=[SurfaceModel])
	asurfs = [s for s in surfs if hasattr(s, 'atomAndBondSurfacePieces')]
	return asurfs

def setRingFill(fill):
	residues = selResidues()
	if not fill:
		for r in residues:
			r.fillDisplay = False
		return
	if fill == "thin":
		mode = chimera.Residue.Thin
	elif fill == "thick":
		mode = chimera.Residue.Thick
	else:
		raise ValueError("Unknown ring fill mode: %s" % fill)
	for r in residues:
		r.fillDisplay = True
		r.fillMode = mode

def setRingAromatic(aro):
	molecules = selMolecules()
	if not aro:
		for m in molecules:
			m.aromaticDisplay = False
		return
	if aro == "disk":
		mode = chimera.Molecule.Disk
	elif aro == "circle":
		mode = chimera.Molecule.Circle
	else:
		raise ValueError("Unknown ring aromatic mode: %s" % aro)
	for m in molecules:
		m.aromaticDisplay = True
		m.aromaticMode = mode
	# ring-fill depiction "wins", so turn it off appropriately
	for r in selResidues():
		r.fillDisplay = False

def nucleicOff():
	from NucleicAcids.cmd import sidechain
	sidechain("atoms", sel=selResidues())
