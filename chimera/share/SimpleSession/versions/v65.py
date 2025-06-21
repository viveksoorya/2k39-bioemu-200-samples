# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: v38.py,v 1.1 2008-11-11 01:04:35 goddard Exp $

from v64 import *

import globals # so that various version files can easily access same variables
import chimera

def restoreMolecules(molInfo, resInfo, atomInfo, bondInfo, crdInfo):
	from SimpleSession import registerAttribute
	items = []
	sm = globals.sessionMap

	res2mol = []
	atom2mol = []
	openModelsInfo = []
	for ids, name, cid, display, lineWidth, pointSize, stickScale, \
	pdbHeaders, mmCIFHeaders, pdbVersion, surfaceOpacity, ballScale, vdwDensity, autochain, \
	ribbonHidesMainchain, riCID, ribbonType, ribbonStiffness, \
	ribbonSmoothing, aromaticCID, aromaticDisplay, \
	aromaticLineType, aromaticMode, hidden, residueLabelPos, \
	lowerCaseChains in zip(
				expandSummary(molInfo['ids']),
				expandSummary(molInfo['name']),
				expandSummary(molInfo['color']),
				expandSummary(molInfo['display']),
				expandSummary(molInfo['lineWidth']),
				expandSummary(molInfo['pointSize']),
				expandSummary(molInfo['stickScale']),
				molInfo['pdbHeaders'],
				molInfo['mmCIFHeaders'],
				expandSummary(molInfo['pdbVersion']),
				expandSummary(molInfo['surfaceOpacity']),
				expandSummary(molInfo['ballScale']),
				expandSummary(molInfo['vdwDensity']),
				expandSummary(molInfo['autochain']),
				expandSummary(molInfo['ribbonHidesMainchain']),
				expandSummary(molInfo['ribbonInsideColor']),
				expandSummary(molInfo['ribbonType']),
				expandSummary(molInfo['ribbonStiffness']),
				expandSummary(molInfo['ribbonSmoothing']),
				expandSummary(molInfo['aromaticColor']),
				expandSummary(molInfo['aromaticDisplay']),
				expandSummary(molInfo['aromaticLineType']),
				expandSummary(molInfo['aromaticMode']),
				expandSummary(molInfo['hidden']),
				expandSummary(molInfo['residueLabelPos']),
				expandSummary(molInfo['lowerCaseChains'])
				):
		m = chimera.Molecule()
		sm[len(items)] = m
		items.append(m)
		m.name = name
		m.setAllPDBHeaders(pdbHeaders)
		if mmCIFHeaders is not None:
			m.mmCIFHeaders = mmCIFHeaders
		m.pdbVersion = pdbVersion
		openModelsInfo.append((m, ids, hidden))
		m.color = getColor(cid)
		m.display = display
		m.lineWidth = lineWidth
		m.pointSize = pointSize
		m.stickScale = stickScale
		m.surfaceOpacity = surfaceOpacity
		m.ballScale = ballScale
		m.vdwDensity = vdwDensity
		m.autochain = autochain
		m.ribbonHidesMainchain = ribbonHidesMainchain
		m.ribbonInsideColor = getColor(riCID)
		m.ribbonType = ribbonType
		m.ribbonStiffness = ribbonStiffness
		m.ribbonSmoothing = ribbonSmoothing
		m.aromaticColor = getColor(aromaticCID)
		m.aromaticDisplay = aromaticDisplay
		m.aromaticLineType = aromaticLineType
		m.aromaticMode = aromaticMode
		m.residueLabelPos = residueLabelPos
		m.lowerCaseChains = lowerCaseChains
	if molInfo['optional']:
		for attrName, info in molInfo['optional'].items():
			hashable, sequential, sv = info
			registerAttribute(chimera.Molecule, attrName,
							hashable=hashable)
			if sequential:
				vals = expandSequentialSummary(sv)
			else:
				vals = expandSummary(sv, hashable=hashable)
			for m, val in zip(items, vals):
				if val is not None:
					setattr(m, attrName, val)

	resStart = len(items)
	for mid, name, chain, pos, insert, rcid, lcid, ss, ssId, ribbonDrawMode, \
	ribbonDisplay, label, labelOffset, isHet, fillDisplay, fillMode in zip(
				expandSummary(resInfo['molecule']),
				expandSummary(resInfo['name']),
				expandSummary(resInfo['chain']),
				expandSequentialSummary(resInfo['position']),
				expandSummary(resInfo['insert']),
				expandSummary(resInfo['ribbonColor']),
				expandSummary(resInfo['labelColor']),
				expandSummary(resInfo['ss']),
				expandSummary(resInfo['ssId']),
				expandSummary(resInfo['ribbonDrawMode']),
				expandSummary(resInfo['ribbonDisplay']),
				expandSummary(resInfo['label']),
				expandSummary(resInfo['labelOffset']),
				expandSummary(resInfo['isHet']),
				expandSummary(resInfo['fillDisplay']),
				expandSummary(resInfo['fillMode']),
				):
		m = idLookup(mid)
		r = m.newResidue(name, chain, pos, insert)
		sm[len(items)] = r
		items.append(r)
		r.ribbonColor = getColor(rcid)
		r.labelColor = getColor(lcid)
		r.isHelix, r.isStrand = ss
		r.ssId = ssId
		r.ribbonDrawMode = ribbonDrawMode
		r.ribbonDisplay = ribbonDisplay
		r.label = label
		if labelOffset is not None:
			r.labelOffset = labelOffset
		r.isHet = isHet
		r.fillDisplay = fillDisplay
		r.fillMode = fillMode
	if resInfo['optional']:
		residues = items[resStart:]
		for attrName, info in resInfo['optional'].items():
			hashable, sequential, sv = info
			registerAttribute(chimera.Residue, attrName,
							hashable=hashable)
			if sequential:
				vals = expandSequentialSummary(sv)
			else:
				vals = expandSummary(sv, hashable=hashable)
			for r, val in zip(residues, vals):
				if val is not None:
					setattr(r, attrName, val)

	atomStart = len(items)
	for rid, name, element, cid, vcid, lcid, scid, drawMode, display, \
	label, labelOffet, minimumLabelRadius, surfaceDisplay, surfaceCategory, \
	surfaceOpacity, radius, vdw, idatmType, altLoc, coordIndex in zip(
				expandSummary(atomInfo['residue']),
				expandSummary(atomInfo['name']),
				expandSummary(atomInfo['element']),
				expandSummary(atomInfo['color']),
				expandSummary(atomInfo['vdwColor']),
				expandSummary(atomInfo['labelColor']),
				expandSummary(atomInfo['surfaceColor']),
				expandSummary(atomInfo['drawMode']),
				expandSummary(atomInfo['display']),
				expandSummary(atomInfo['label']),
				expandSummary(atomInfo['labelOffset']),
				expandSummary(atomInfo['minimumLabelRadius']),
				expandSummary(atomInfo['surfaceDisplay']),
				expandSummary(atomInfo['surfaceCategory']),
				expandSummary(atomInfo['surfaceOpacity']),
				expandSummary(atomInfo['radius']),
				expandSummary(atomInfo['vdw']),
				expandSummary(atomInfo['idatmType']),
				expandSummary(atomInfo['altLoc']),
				expandSequentialSummary(atomInfo['coordIndex'])
				):
		r = idLookup(rid)
		a = r.molecule.newAtom(name, chimera.Element(element), coordIndex=coordIndex)
		sm[len(items)] = a
		items.append(a)
		r.addAtom(a)
		a.color = getColor(cid)
		a.vdwColor = getColor(vcid)
		a.labelColor = getColor(lcid)
		a.surfaceColor = getColor(scid)
		a.drawMode = drawMode
		a.display = display
		a.label = label
		if labelOffset is not None:
			a.labelOffset = labelOffset
		a.minimumLabelRadius = minimumLabelRadius
		a.surfaceDisplay = surfaceDisplay
		a.surfaceCategory = surfaceCategory
		a.surfaceOpacity = surfaceOpacity
		a.radius = radius
		a.vdw = vdw
		if idatmType:
			a.idatmType = idatmType
		a.altLoc = altLoc
	if atomInfo['optional']:
		atoms = items[atomStart:]
		for attrName, info in atomInfo['optional'].items():
			hashable, sequential, sv = info
			registerAttribute(chimera.Atom, attrName,
							hashable=hashable)
			if sequential:
				vals = expandSequentialSummary(sv)
			else:
				vals = expandSummary(sv, hashable=hashable)
			for a, val in zip(atoms, vals):
				if val is not None:
					setattr(a, attrName, val)

	bondStart = len(items)
	for atoms, cid, drawMode, display, halfbond, label, labelOffset, radius \
	in zip(
					bondInfo['atoms'],
					expandSummary(bondInfo['color']),
					expandSummary(bondInfo['drawMode']),
					expandSummary(bondInfo['display']),
					expandSummary(bondInfo['halfbond']),
					expandSummary(bondInfo['label']),
					expandSummary(bondInfo['labelOffset']),
					expandSummary(bondInfo['radius'])
					):
		a1, a2 = [idLookup(a) for a in atoms]
		b = a1.molecule.newBond(a1, a2)
		sm[len(items)] = b
		items.append(b)
		b.color = getColor(cid)
		b.drawMode = drawMode
		b.display = display
		b.halfbond = halfbond
		b.label = label
		if labelOffset is not None:
			b.labelOffset = labelOffset
		b.radius = radius
	if bondInfo.get('optional', {}):
		bonds = items[bondStart:]
		for attrName, info in bondInfo['optional'].items():
			hashable, sequential, sv = info
			registerAttribute(chimera.Bond, attrName,
							hashable=hashable)
			if sequential:
				vals = expandSequentialSummary(sv)
			else:
				vals = expandSummary(sv, hashable=hashable)
			for b, val in zip(bonds, vals):
				if val is not None:
					setattr(b, attrName, val)

	from chimera import Point
	for mid, crdSets in crdInfo.items():
		m = idLookup(mid)
		active = crdSets.pop('active', None)
		for key, crds in crdSets.items():
			coordSet = m.newCoordSet(key, len(crds))
			coordSet.load(crds)
			if key == active:
				m.activeCoordSet = coordSet
	# delay opening of model until it is fully restored so that
	# the openModels 'add' trigger doesn't hand off an empty
	# molecule to its handlers
	from SimpleSession import modelMap, modelOffset
	for m, ids, hidden in openModelsInfo:
		chimera.openModels.add([m], baseId=ids[0]+modelOffset,
					subid=ids[1], hidden=hidden, fromSession=True)
		modelMap.setdefault(ids, []).append(m)

def restoreSilhouettes(silhouettes):
	for modelID, s in silhouettes.items():
		model = idLookup(modelID)
		model.silhouette = s
