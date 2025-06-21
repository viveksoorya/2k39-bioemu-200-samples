# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: upDown.py 39973 2014-07-08 00:40:21Z pett $

import chimera
from chimera import selection

SELNONE, SELATOM, SELRES, SELSSE, SELFRAG, SELCHAIN, SELSUBMODEL, SELMODEL, \
	SELALL = range(9)

selLevel = SELATOM

def selUp():
	global _selChangeHandler, _atomChangeHandler
	needHandlers = False
	if not _selInfos[SELATOM:]:
		needHandlers = True
		_selInfos.append(_infoFromSel(selection.copyCurrent()))
	# go up levels until the selection changes
	global _IchangedSel, selLevel
	_IchangedSel = False
	while selLevel < SELALL:
		selLevel += 1
		try:
			nextSel = _selInfos[selLevel][0]
			if selLevel == SELALL \
			and not _topValid:
				raise IndexError, "new models present"
		except IndexError:
			nextSel = _nextSel()
			_selInfos.append(_infoFromSel(nextSel))
		if len(nextSel) != len(_selInfos[selLevel-1][0]):
			if not needHandlers:
				_IchangedSel = True
			selection.setCurrent(nextSel)
			break
	# delay the handlers until here in case setting the selection
	# causes other things to get selected (e.g. axes/planes)
	if needHandlers:
		# also, 'selection changed' now fires off of
		# 'monitor changes', so wait for that...
		from chimera.update import checkForChanges
		checkForChanges()
		_atomChangeHandler = chimera.triggers.addHandler(
			"Atom", _atomChangeCB, None)
		_selChangeHandler = chimera.triggers.addHandler(
			"selection changed", _selChangeCB, None)

def selDown():
	if not _selInfos[SELATOM:]:
		return
	# keep lowering level until selection changes
	global _IchangedSel, selLevel
	_IchangedSel = False
	while selLevel > SELNONE:
		selLevel -= 1
		if len(_selInfos[selLevel][0]) != len(_selInfos[selLevel+1][0]):
			_IchangedSel = True
			selection.setCurrent(_selInfos[selLevel][0])
			break

def _nextSel():
	sel = selection.ItemizedSelection()
	sel.add(selection.currentBarrenGraphs())
	if selLevel == SELRES:
		items = []
		addResidues = {}
		for r in selection.currentResidues():
			addResidues[r] = 1
		selPseudoBonds = filter(lambda e,
			PB=chimera.PseudoBond:
			isinstance(e, PB), selection.currentEdges())
		# for currently selected chain-trace pseudobonds
		# act as if they select their residues
		for ct in filter(lambda e: isinstance(e.pseudoBondGroup,
				chimera.ChainTrace), selPseudoBonds):
			addResidues[ct.atoms[0].residue] = 1
			addResidues[ct.atoms[1].residue] = 1
		for r in addResidues.keys():
			items.extend(r.atoms)
		sel.add(items)
		sel.addImplied(vertices=False)
		sel.add(selPseudoBonds)
		# add chain trace pseudobonds that should be selected
		sel.add(selChainTrace(sel))

	elif selLevel == SELSSE:
		res2sse = {}
		sse2res = {}
		from chimera import openModels, Molecule
		from chimera.resCode import protein3to1
		for mol in openModels.list(modelTypes=[Molecule]):
			if not getattr(mol, 'isRealMolecule', True):
				continue
			for seq in mol.sequences():
				isProtein = False
				for res in seq.residues:
					if not res or res.isHet:
						continue
					if res.type in protein3to1:
						isProtein = True
						break
					else:
						atomsMap = res.atomsMap
						if 'CA' in atomsMap and (len(atomsMap) == 1 or (
						'C' in atomsMap and 'N' in atomsMap)):
							isProtein = True
						break
				if not isProtein:
					continue
				prevId = None
				run = 0
				for res in seq.residues:
					if res:
						curId = (res.isHelix + 2 * res.isStrand, res.ssId)
						if curId != prevId:
							run += 1
							prevId = curId
						key = (seq, run)
						res2sse[res] = key
						sse2res.setdefault(key, []).append(res)
		sses = set()
		for res in selection.currentResidues():
			if res in res2sse:
				sses.add(res2sse[res])
		residues = []
		for sse in sses:
			residues.extend(sse2res[sse])
		sel.add(residues)
		sel.addImplied(vertices=False)
		sel.add(selection.currentVertices())
		sel.add(selection.currentEdges())

	elif selLevel == SELFRAG:
		curAtoms = set(selection.currentAtoms())
		selPseudoBonds = filter(lambda e,
			PB=chimera.PseudoBond:
			isinstance(e, PB), selection.currentEdges())
		# for currently selected chain-trace pseudobonds
		# act as if they select their residues
		for ct in filter(lambda e: isinstance(e.pseudoBondGroup,
				chimera.ChainTrace), selPseudoBonds):
			curAtoms.update(ct.atoms[0].residue.atoms)
			curAtoms.update(ct.atoms[1].residue.atoms)
		roots = set([a.molecule.rootForAtom(a, True) for a in curAtoms])
		# don't cross into new chains...
		chainIDs = {}
		for a in curAtoms:
			chainID = a.residue.id.chainId
			try:
				chainIDs[a.molecule][chainID] = 1
			except KeyError:
				chainIDs[a.molecule] = {chainID: 1}
		atoms = []
		for root in roots:
			atoms.extend([a for a in root.atom.molecule.traverseAtoms(root)
				if a.residue.id.chainId in chainIDs[a.molecule]])
		sel.add(atoms)
		sel.addImplied(vertices=False)
		sel.add(selPseudoBonds)

	elif selLevel == SELCHAIN:
		chainIDs = {}
		for a in selection.currentAtoms():
			chainID = a.residue.id.chainId
			try:
				chainIDs[a.molecule][chainID] = 1
			except KeyError:
				chainIDs[a.molecule] = {chainID: 1}
		items = []
		for m, ids in chainIDs.items():
			for a in m.atoms:
				if not ids.has_key(
						a.residue.id.chainId):
					continue
				items.append(a)
				items.extend([b for b in a.bonds
					if b.otherAtom(a).residue.id.chainId == a.residue.id.chainId])
		pbgs = {}
		for pb in filter(lambda b, PB=chimera.PseudoBond:
					isinstance(b, PB),
					selection.currentEdges()):
			pbgs[pb.pseudoBondGroup] = 1
		for pbg in pbgs.keys():
			if isinstance(pbg, chimera.ChainTrace):
				continue
			items.extend(pbg.pseudoBonds)
		sel.add(items)
		sel.add(selChainTrace(sel))

	elif selLevel == SELSUBMODEL:
		items = []
		for m in selection.currentMolecules():
			items.extend(m.atoms)
			items.extend(m.bonds)
		items.extend(filter(lambda e, PB=chimera.PseudoBond:
			isinstance(e, PB), selection.currentEdges()))
		sel.add(items)
		sel.add(selChainTrace(sel))
	elif selLevel == SELMODEL:
		molDict = {}
		for m in selection.currentMolecules():
			osl = m.oslIdent()
			if '.' in osl:
				molDict[osl[:osl.index('.')]] = 1
			else:
				molDict[m] = 1
		items = []
		for mosl in molDict.keys():
			if isinstance(mosl, basestring):
				for m in selection.OSLSelection(
						mosl).molecules():
					items.extend(m.atoms)
					items.extend(m.bonds)
			else:
				items.extend(mosl.atoms)
				items.extend(mosl.bonds)
		items.extend(filter(lambda e, PB=chimera.PseudoBond:
			isinstance(e, PB), selection.currentEdges()))
		sel.add(items)
		sel.add(selChainTrace(sel))
	elif selLevel == SELALL:
		global _topValid
		_topValid = True
		items = []
		if selection.currentMolecules():
			for m in chimera.openModels.list():
				if hasattr(m, 'atoms'):
					items.extend(m.atoms)
					items.extend(m.bonds)
		for e in selection.currentEdges():
			if isinstance(e, chimera.PseudoBond):
				pbsSelected = True
				break
		else:
			pbsSelected = False
		if pbsSelected:
			mgr = chimera.PseudoBondMgr.mgr()
			for grp in mgr.pseudoBondGroups:
				items.extend(grp.pseudoBonds)
		sel.add(items)
		sel.add(selChainTrace(sel))
		global _selAllHandler
		if _selAllHandler is not None:
			_selAllHandler = \
				chimera.openModels.addAddHandler(
						_addModelHandler, None)
	else:
		raise ValueError, "Bad selection level"

	# Handle selected surface pieces
	from Surface import selected_surface_pieces
	plist = selected_surface_pieces()
	mlist = set([p.model for p in plist])
	if selLevel == SELALL and len(mlist) > 0:
		from _surface import SurfaceModel
		mlist = chimera.openModels.list(modelTypes = [SurfaceModel])
	sel.add(mlist)

	return sel

def selChainTrace(sel):
	mgr = chimera.PseudoBondMgr.mgr()
	ct = []
	for pbGroup in mgr.pseudoBondGroups:
		if not isinstance(pbGroup, chimera.ChainTrace):
			continue
		for pb in pbGroup.pseudoBonds:
			if sel.contains(pb.atoms[0]) \
			and sel.contains(pb.atoms[1]):
				ct.append(pb)
	return ct

def _selChangeCB(*args):
	global _IchangedSel
	if _IchangedSel:
		_IchangedSel = False
		return
	chimera.triggers.deleteHandler("selection changed", _selChangeHandler)
	chimera.triggers.deleteHandler("Atom", _atomChangeHandler)
	global _selInfos, selLevel
	_selInfos = _selInfos[:SELATOM]
	selLevel = SELATOM

def _atomChangeCB(trigName, myData, trigData):
	if not trigData.created:
		return
	global _selInfos, selLevel
	sel, info = _selInfos[selLevel]
	if _countsFromSel(sel) == info:
		return
	chimera.triggers.deleteHandler("selection changed", _selChangeHandler)
	chimera.triggers.deleteHandler("Atom", _atomChangeHandler)
	_selInfos = _selInfos[:SELATOM]
	selLevel = SELATOM

def _addModelHandler(*args):
	# adding a model invalidates the 'all' selection
	global _topValid
	_topValid = False

def _infoFromSel(sel):
	return (sel, _countsFromSel(sel))

def _countsFromSel(sel):
	mols = sel.molecules()
	sortable = [(m.oslIdent(), m) for m in mols]
	from chimera.misc import oslModelCmp
	sortable.sort(oslModelCmp)
	return [len(s[1].atoms) for s in sortable]

_selInfos = [_infoFromSel(selection.ItemizedSelection())]
_selAllHandler = None
