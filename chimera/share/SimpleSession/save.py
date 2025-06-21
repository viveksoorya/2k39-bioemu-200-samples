# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: save.py 41991 2019-01-16 21:23:46Z pett $

import chimera
from chimera import replyobj, selection, SessionPDBio, version
import os
from versions.v65 import sessionID, setSessionIDparams, \
					noAutoRestore, autoRestorable
from tempfile import mktemp

SAVE_SESSION = "save session"
chimera.triggers.addTrigger(SAVE_SESSION)
BEGIN_RESTORE_SESSION = "begin restore session"
chimera.triggers.addTrigger(BEGIN_RESTORE_SESSION)
END_RESTORE_SESSION = "end restore session"
chimera.triggers.addTrigger(END_RESTORE_SESSION)

optionalAttributes = {
	chimera.Molecule: {'openedAs': (True, False)},
	chimera.Residue: {},
	chimera.Bond: {},
	chimera.Atom: {'bfactor': (True, False), 'occupancy': (True, False),
		'charge': (True, False), 'anisoU': (False, False),
		'serialNumber': (True, True), 'pdbSegment': (True, False)},
	chimera.PseudoBondGroup: {},
}

def registerAttribute(level, attrName, hashable=True, sequentialValues=False):
	optionalAttributes[level][attrName] = (hashable, sequentialValues)

def isRegisteredAttribute(classObject, attrName):
	return classObject in optionalAttributes and attrName in optionalAttributes[classObject]

def sesRepr(obj, floatPrecision=6):
        fp = floatPrecision
	if type(obj) == dict:
		lines = []
		accum = []
		totLen = 0
		for k, v in obj.items():
			kvStr = "%s: %s" % (sesRepr(k, fp), sesRepr(v, fp))
			lastNewline = kvStr.rfind("\n")
			if lastNewline == -1:
				totLen += len(kvStr)
			else:
				totLen = len(kvStr) - lastNewline
			accum.append(kvStr)
			if totLen > 1024:
				lines.append(", ".join(accum))
				accum = []
				totLen = 0
		if accum:
			lines.append(", ".join(accum))
		return "{" + ",\n".join(lines) + "}"
	elif type(obj) in (list, tuple):
		lines = []
		accum = []
		totLen = 0
		for item in obj:
			itemStr = sesRepr(item, fp)
			lastNewline = itemStr.rfind("\n")
			if lastNewline == -1:
				totLen += len(itemStr)
			else:
				totLen = len(itemStr) - lastNewline
			accum.append(itemStr)
			if totLen > 1024:
				lines.append(", ".join(accum))
				accum = []
				totLen = 0
		if accum:
			lines.append(", ".join(accum))
		if type(obj) == list:
			startChar = "["
			endChar = "]"
		else:
			startChar = "("
			if len(obj) == 1:
				endChar = ",)"
			else:
				endChar = ")"
		return startChar + ",\n".join(lines) + endChar
	elif type(obj) == set:
		return "set(" + sesRepr(list(obj), fp) + ")"
	elif type(obj) == float:
                format = '%%.%dg' % fp
		return format % obj
	return repr(obj)

def saveSession(filename, temporary=False, **kw):
	from chimera import UserError
	saveDir = os.path.dirname(filename)
	if not saveDir:
		saveDir = os.getcwd()
		filename = os.path.join(saveDir, filename)
	if not os.path.exists(saveDir):
		raise UserError("Session directory (%s) does not exist!" % saveDir)
	elif not os.access(saveDir, os.W_OK):
		raise UserError("Session directory (%s) is not writable!" % saveDir)

	import SimpleSession
	SimpleSession.temporarySession = temporary
	try:
		_saveSession(filename, **kw)
	finally:
		delattr(SimpleSession, "temporarySession")

	if not temporary:
		from chimera import triggers
		triggers.activateTrigger('file save', (filename, 'Python'))

def _saveSession(filename, thumbnailSize=None, description=None):
	replyobj.status("Saving session...", blankAfter=0)
	replyobj.status("Initializing session save...",
		blankAfter=0, secondary=True)
	sesKw = {}
	if thumbnailSize is not None:
		sesKw['thumbnailSize'] = thumbnailSize
	if description is not None:
		sesKw['description'] = description
	from OpenSave import osOpen
	from CGLutil.SafeSave import SafeSave
	with SafeSave(filename, open_func=osOpen) as outf:
		try:
			from cStringIO import StringIO
		except ImportError:
			from StringIO import StringIO
		class SessionIO:
			def __init__(self, stringIO, fileName):
				self.fileName = fileName
				self.stringIO = stringIO()
			def __getattr__(self, attrName):
				return getattr(self.stringIO, attrName)
		buf = SessionIO(StringIO, filename)

		viewer = chimera.viewer
		if thumbnailSize or description:
			if thumbnailSize and not isinstance(viewer, chimera.NoGuiViewer):
				if isinstance(thumbnailSize, int):
					thumbnailSize = (thumbnailSize, thumbnailSize)
				try:
					tbImg = viewer.pilImages(*thumbnailSize, supersample=2)[0]
				except IOError:
					replyobj.warning("Cannot create thumbnail image for session")
					thumbInfo = None
				else:
					import zlib
					thumbInfo = (tbImg.mode, tbImg.size, zlib.compress(tbImg.tostring()))
			else:
				thumbInfo = None
			print>>outf, sesRepr((1, thumbInfo, description))
		print>> outf, "import cPickle, base64"
		print>> outf, "try:"
		print>> outf, "\tfrom SimpleSession.versions.v65 import beginRestore,\\"
		print>> outf, "\t    registerAfterModelsCB, reportRestoreError, checkVersion"
		print>> outf, "except ImportError:"
		print>> outf, "\tfrom chimera import UserError"
		print>> outf, "\traise UserError('Cannot open session that was saved in a'"
		print>> outf, "\t    ' newer version of Chimera; update your version')"
		print>> outf, "checkVersion(%s)" % repr(version.releaseNum)
		print>> outf, "import chimera"
		print>> outf, "from chimera import replyobj"
		print>> outf, "replyobj.status('Restoring session...', \\"
		print>> outf, "    blankAfter=0)"
		print>> outf, "replyobj.status('Beginning session restore...', \\"
		print>> outf, "    blankAfter=0, secondary=True)"
		print>> outf, "beginRestore()"
		print>> outf, """
def restoreCoreModels():
\tfrom SimpleSession.versions.v65 import init, restoreViewer, \\
\t     restoreMolecules, restoreColors, restoreSurfaces, \\
\t     restoreVRML, restorePseudoBondGroups, restoreModelAssociations"""
		global _colorInfo, _color2id
		_colorInfo = []
		_color2id = {}

		molecules = [m for m in
			chimera.openModels.list(modelTypes=[chimera.Molecule], all=True)
			if autoRestorable(m)]
		allSurfaces = chimera.openModels.list(modelTypes=[chimera.MSMSModel])
		allVrmls = [m for m in
			chimera.openModels.list(modelTypes=[chimera.VRMLModel])
			if autoRestorable(m)]

		surfaces = [s for s in allSurfaces if s.molecule in molecules]
		if surfaces != allSurfaces:
			replyobj.warning("Cannot save surfaces without associated structure.\nSurface will not be saved.\n")
		vrmls = []
		for v in allVrmls:
			if hasattr(v, 'openedAs'):
				source = v.openedAs[0]
			elif hasattr(v, 'vrmlString'):
				source = v.vrmlString
			else:
				source = None
			if source is None:
				replyobj.warning("VRML model '%s' does not come from"
					" a file\nand will not be saved in"
					" the session.\n" % v.name)
			elif not source.startswith('#VRML')\
			and not os.path.exists(source):
				replyobj.warning("Source file for VRML model '%s' no"
					" longer exists.\nThe model will not be"
					" saved.\n" % v.name)
			else:
				vrmls.append(v)

		atoms = []
		bonds = []
		residues = []
		for m in molecules:
			atoms.extend(m.atoms)
			bonds.extend(m.bonds)
			residues.extend(m.residues)

		mgr = chimera.PseudoBondMgr.mgr()
		pbGroups = []
		chainTraces = []
		for g in mgr.pseudoBondGroups:
			if g.category.startswith("internal-chain-"):
				noAutoRestore(g)
				chainTraces.append(g)
			else:
				pbGroups.append(g)
		pseudobonds = []
		pbMap = {}
		for pbg in pbGroups:
			pbs = [pb for pb in pbg.pseudoBonds
					if autoRestorable(pb.atoms[0].molecule)
					and autoRestorable(pb.atoms[1].molecule)]
			pseudobonds.extend(pbs)
			pbMap[pbg] = pbs

		setSessionIDparams(molecules, residues, atoms, bonds, surfaces, vrmls,
								pseudobonds, pbGroups)

		replyobj.status("Gathering molecule information...",
			blankAfter=0, secondary=True)
		molInfo = {}
		molInfo['ids'] = summarizeVals([(m.id, m.subid) for m in molecules])
		molInfo['name'] = summarizeVals([m.name for m in molecules])
		molInfo['color'] = summarizeVals([colorID(m.color) for m in molecules])
		molInfo['display'] = summarizeVals([m.display for m in molecules])
		molInfo['lineWidth'] = summarizeVals([m.lineWidth for m in molecules])
		molInfo['pointSize'] = summarizeVals([m.pointSize for m in molecules])
		molInfo['stickScale'] = summarizeVals([m.stickScale for m in molecules])
		molInfo['pdbHeaders'] = [m.pdbHeaders for m in molecules]
		molInfo['mmCIFHeaders'] = [m.mmCIFHeaders if hasattr(m, 'mmCIFHeaders') else None
			for m in molecules]
		molInfo['pdbVersion'] = summarizeVals([m.pdbVersion for m in molecules])
		molInfo['surfaceOpacity'] = summarizeVals([m.surfaceOpacity
								for m in molecules])
		molInfo['ballScale'] = summarizeVals([m.ballScale for m in molecules])
		molInfo['vdwDensity'] = summarizeVals([m.vdwDensity for m in molecules])
		molInfo['autochain'] = summarizeVals([m.autochain for m in molecules])
		molInfo['ribbonHidesMainchain'] = summarizeVals([m.ribbonHidesMainchain
								for m in molecules])
		molInfo['ribbonInsideColor'] = summarizeVals([colorID(m.ribbonInsideColor)
								for m in molecules])
		molInfo['ribbonType'] = summarizeVals([m.ribbonType for m in molecules])
		molInfo['ribbonStiffness'] = summarizeVals([m.ribbonStiffness
								for m in molecules])
		molInfo['ribbonSmoothing'] = summarizeVals([m.ribbonSmoothing
								for m in molecules])
		molInfo['aromaticColor'] = summarizeVals([colorID(m.aromaticColor)
								for m in molecules])
		molInfo['aromaticDisplay'] = summarizeVals([m.aromaticDisplay
								for m in molecules])
		molInfo['aromaticLineType'] = summarizeVals([m.aromaticLineType
								for m in molecules])
		molInfo['aromaticMode'] = summarizeVals([m.aromaticMode
								for m in molecules])
		molInfo['hidden'] = summarizeVals([m in m.openState.hidden
								for m in molecules])
		molInfo['residueLabelPos'] = summarizeVals([m.residueLabelPos
								for m in molecules])
		molInfo['lowerCaseChains'] = summarizeVals([m.lowerCaseChains
								for m in molecules])
		molInfo['optional'] = saveOptionalAttrs(chimera.Molecule, molecules)
		print>> outf, "\tmolInfo =", pickled(molInfo)

		replyobj.status("Gathering residue information...",
			blankAfter=0, secondary=True)
		resInfo = {}
		resInfo['molecule'] = summarizeVals([sessionID(r.molecule)
					for r in residues], consecutiveExceptions=True)
		resInfo['name'] = summarizeVals([r.type for r in residues])
		resInfo['chain'] = summarizeVals([r.id.chainId for r in residues],
							consecutiveExceptions=True)
		resInfo['insert'] = summarizeVals([r.id.insertionCode
								for r in residues])
		resInfo['position'] = summarizeSequentialVals(
						[r.id.position for r in residues])
		resInfo['ribbonColor'] = summarizeVals([colorID(r.ribbonColor)
					for r in residues], consecutiveExceptions=True)
		resInfo['labelColor'] = summarizeVals([colorID(r.labelColor)
					for r in residues], consecutiveExceptions=True)
		resInfo['ss'] = summarizeVals([(r.isHelix, r.isStrand)
					for r in residues], consecutiveExceptions=True)
		resInfo['ssId'] = summarizeVals([r.ssId for r in residues],
					consecutiveExceptions=True)
		resInfo['ribbonDrawMode'] = summarizeVals([r.ribbonDrawMode
					for r in residues], consecutiveExceptions=True)
		resInfo['ribbonDisplay'] = summarizeVals([r.ribbonDisplay
					for r in residues], consecutiveExceptions=True)
		resInfo['label'] = summarizeVals([r.label for r in residues])
		resInfo['labelOffset'] = summarizeVals([r.labelOffset for r in residues])
		resInfo['isHet'] = summarizeVals([r.isHet for r in residues],
							consecutiveExceptions=True)
		resInfo['fillDisplay'] = summarizeVals([r.fillDisplay for r in residues],
							consecutiveExceptions=True)
		resInfo['fillMode'] = summarizeVals([r.fillMode for r in residues],
							consecutiveExceptions=True)
		resInfo['optional'] = saveOptionalAttrs(chimera.Residue, residues)
		print>> outf, "\tresInfo =", pickled(resInfo)

		replyobj.status("Gathering atom information...",
			blankAfter=0, secondary=True)
		atomInfo = {}
		atomInfo['altLoc'] = summarizeVals([a.altLoc for a in atoms])
		atomInfo['color'] = summarizeVals([colorID(a.color) for a in atoms])
		atomInfo['surfaceColor'] = summarizeVals([colorID(a.surfaceColor)
								for a in atoms])
		atomInfo['coordIndex'] = summarizeSequentialVals([a.coordIndex
								for a in atoms])
		atomInfo['drawMode'] = summarizeVals([a.drawMode for a in atoms],
							consecutiveExceptions=True)
		atomInfo['display'] = summarizeVals([a.display for a in atoms],
							consecutiveExceptions=True)
		atomInfo['element'] = summarizeVals([a.element.number for a in atoms])
		atomInfo['label'] = summarizeVals([a.label for a in atoms])
		atomInfo['labelColor'] = summarizeVals([colorID(a.labelColor)
								for a in atoms])
		atomInfo['labelOffset'] = summarizeVals([a.labelOffset for a in atoms])
		atomInfo['minimumLabelRadius'] = summarizeVals([a.minimumLabelRadius
												for a in atoms])
		atomInfo['name'] = summarizeVals([a.name for a in atoms])
		atomInfo['radius'] = summarizeVals([a.radius for a in atoms])
		atomInfo['residue'] = summarizeVals([sessionID(a.residue)
					for a in atoms], consecutiveExceptions=True)
		atomInfo['surfaceDisplay'] = summarizeVals([a.surfaceDisplay
					for a in atoms], consecutiveExceptions=True)
		atomInfo['surfaceCategory'] = summarizeVals([a.surfaceCategory
					for a in atoms], consecutiveExceptions=True)
		atomInfo['surfaceOpacity'] = summarizeVals([a.surfaceOpacity
					for a in atoms], consecutiveExceptions=True)
		atomInfo['vdw'] = summarizeVals([a.vdw for a in atoms],
							consecutiveExceptions=True)
		atomInfo['vdwColor'] = summarizeVals([colorID(a.vdwColor)
								for a in atoms])
		atomInfo['optional'] = saveOptionalAttrs(chimera.Atom, atoms)

		# only restore explicitly-set IDATM types...
		atomInfo['idatmType'] = summarizeVals([(a.idatmIsExplicit and
							a.idatmType) for a in atoms])
		print>> outf, "\tatomInfo =", pickled(atomInfo)

		replyobj.status("Gathering bond information...",
			blankAfter=0, secondary=True)
		bondInfo = {}
		bondInfo['atoms'] = [[sessionID(a) for a in b.atoms] for b in bonds]
		bondInfo['color'] = summarizeVals([colorID(b.color) for b in bonds])
		bondInfo['drawMode'] = summarizeVals([b.drawMode for b in bonds],
							consecutiveExceptions=True)
		bondInfo['display'] = summarizeVals([b.display for b in bonds])
		bondInfo['halfbond'] = summarizeVals([b.halfbond for b in bonds])
		bondInfo['label'] = summarizeVals([b.label for b in bonds])
		bondInfo['labelOffset'] = summarizeVals([b.labelOffset for b in bonds])
		bondInfo['radius'] = summarizeVals([b.radius for b in bonds])
		bondInfo['optional'] = saveOptionalAttrs(chimera.Bond, bonds)

		print>> outf, "\tbondInfo =", pickled(bondInfo)

		replyobj.status("Gathering coordinates...", blankAfter=0, secondary=True)
		crdInfo = {}
		for m in molecules:
			crdSets = {}
			crdInfo[sessionID(m)] = crdSets
			for key, coordSet in m.coordSets.items():
				crdSets[key] = [crd.data() for crd in coordSet.coords()]
				if coordSet == m.activeCoordSet:
					crdSets['active'] = key
		print>> outf, "\tcrdInfo =", pickled(crdInfo)

		replyobj.status("Gathering surface information...",
			blankAfter=0, secondary=True)
		surfInfo = {}
		surfInfo['molecule'] = [sessionID(s.molecule) for s in surfaces]
		surfInfo['name'] = [s.name for s in surfaces]
		surfInfo['customColors'] = surfColors = []
		surfInfo['customVisibility'] = surfVis = []
		for attrname in ('category', 'colorMode', 'density', 'drawMode',
				 'display', 'probeRadius', 'allComponents',
				 'lineWidth', 'pointSize', 'useLighting',
				 'twoSidedLighting', 'smoothLines',
				 'transparencyBlendMode'):
			values = [getattr(s, attrname) for s in surfaces]
			surfInfo[attrname] = summarizeVals(values)
		for s in surfaces:
			if (s.colorMode == chimera.MSMSModel.Custom and
				not s.customColors is None):
				surfColors.append(summarizeVals([colorID(c)
							for c in s.customColors]))
			else:
				surfColors.append(summarizeVals([]))
		import Surface
		for s in surfaces:
			if (s.visibilityMode == chimera.MSMSModel.Custom and
				not Surface.visibility_updating(s)):
				mask = s.surface_piece.triangleAndEdgeMask
				import SessionUtil
				from numpy import uint8
				surfVis.append(SessionUtil.array_to_string(mask, uint8))
			else:
				surfVis.append(None)
		print>> outf, "\tsurfInfo =", sesRepr(surfInfo)

		replyobj.status("Gathering VRML information...",
			blankAfter=0, secondary=True)
		vrmlInfo = {}
		vrmlInfo['id'] = summarizeVals([v.id for v in vrmls])
		vrmlInfo['subid'] = summarizeVals([v.subid for v in vrmls])
		vrmlInfo['name'] = summarizeVals([v.name for v in vrmls])
		vrmlInfo['display'] = summarizeVals([v.display for v in vrmls])
		vrmlInfo['vrmlString'] = vrmlStrings = []
		for v in vrmls:
			source = v.openedAs[0] if hasattr(v, 'openedAs') else v.vrmlString
			if source.startswith('#VRML'):
				vrmlStrings.append(source)
			else:
				# source is file name
				vrmlFile = open(source, 'r')
				vrmlStrings.append(vrmlFile.read())
				vrmlFile.close()
		print>> outf, "\tvrmlInfo =", sesRepr(vrmlInfo)

		replyobj.status("Gathering color information...",
			blankAfter=0, secondary=True)
		# remember all saved colors/materials...
		knownColors = {}
		knownMaterials = {}
		from chimera import _savedColors, _savedMaterials
		for material in _savedMaterials:
			knownMaterials[material.name()] = (
				material.specular,
				material.shininess
			)
		for color in _savedColors:
			if not isinstance(color, chimera.MaterialColor):
				continue
			matName = color.material.name()
			if matName is None: # unnamed material
				matName = "mat" + str(id(color.material))
			knownColors[color.name()] = (
				color.ambientDiffuse,
				color.opacity,
				matName
			)
			if matName not in knownMaterials:
				mat = color.material
				knownMaterials[matName] = (
					mat.specular,
					mat.shininess
				)
		print>> outf, "\tcolors =", sesRepr(knownColors)
		print>> outf, "\tmaterials =", sesRepr(knownMaterials)

		replyobj.status("Gathering pseudobond information...",
			blankAfter=0, secondary=True)
		pbInfo = {}
		pbInfo['category'] = [g.category for g in pbGroups]
		pbInfo['id'] = [g.id for g in pbGroups]
		pbInfo['color'] = summarizeVals([colorID(g.color) for g in pbGroups])
		pbInfo['display'] = summarizeVals([g.display for g in pbGroups])
		pbInfo['showStubBonds'] = summarizeVals([g.showStubBonds
								for g in pbGroups])
		pbInfo['lineWidth'] = summarizeVals([g.lineWidth for g in pbGroups])
		pbInfo['stickScale'] = summarizeVals([g.stickScale for g in pbGroups])
		pbInfo['lineType'] = summarizeVals([g.lineType for g in pbGroups])
		pbInfo['bondInfo'] = pbBondInfos = []
		pbInfo['optional'] = saveOptionalAttrs(chimera.PseudoBondGroup, pbGroups)
		for g in pbGroups:
			pbs = pbMap[g]
			info = {}
			pbBondInfos.append(info)
			info['atoms'] = [[sessionID(a) for a in pb.atoms] for pb in pbs]
			info['drawMode'] = summarizeVals([pb.drawMode for pb in pbs])
			info['display'] = summarizeVals([pb.display for pb in pbs])
			info['halfbond'] = summarizeVals([pb.halfbond for pb in pbs])
			info['label'] = summarizeVals([pb.label for pb in pbs])
			info['color'] = summarizeVals([colorID(pb.color) for pb in pbs])
			info['labelColor'] = summarizeVals([colorID(pb.labelColor)
									for pb in pbs])
			info['labelOffset'] = summarizeVals([pb.labelOffset for pb in pbs])
		print>> outf, "\tpbInfo =", sesRepr(pbInfo)

		associations = {}
		for m in molecules + surfaces + vrmls + pbGroups:
			ams = []
			for am in m.associatedModels():
				if autoRestorable(am):
					ams.append(sessionID(am))
			if ams:
				associations[sessionID(m)] = ams
		print>> outf, "\tmodelAssociations =", sesRepr(associations)

		replyobj.status("Gathering font information...",
			blankAfter=0, secondary=True)
		from chimera.initprefs import PREF_LABEL, LABEL_FONT
		from chimera import preferences
		fontInfo = {
			'face': preferences.getOption(PREF_LABEL, LABEL_FONT).get()
		}

		replyobj.status("Gathering clip plane information...",
			blankAfter=0, secondary=True)
		clipPlaneInfo = {}
		for m in molecules + surfaces:
			if m.useClipPlane:
				pl = m.clipPlane
				clipPlaneInfo[sessionID(m)] = (
					pl.origin.data(),
					pl.normal.data(),
					m.useClipThickness,
					m.clipThickness
				)

		replyobj.status("Gathering per-model silhouette information...",
			blankAfter=0, secondary=True)
		silhouettes = {}
		for m in molecules + surfaces + vrmls + pbGroups:
			silhouettes[sessionID(m)] = m.silhouette

		replyobj.status("Gathering selection information...",
			blankAfter=0, secondary=True)
		curSelIds = []
		curSel = selection.copyCurrent()
		selMols = curSel.molecules()
		badMols = filter(lambda m: not autoRestorable(m), selMols)
		if badMols:
			curSel.remove(badMols)
		for a in curSel.atoms():
			curSelIds.append(sessionID(a))
		for b in curSel.bonds():
			curSelIds.append(sessionID(b))
		for pb in curSel.pseudobonds():
			if pb.pseudoBondGroup in chainTraces:
				curSelIds.append([sessionID(a) for a in pb.atoms])
			else:
				curSelIds.append(sessionID(pb))
		vrmlSet = set(allVrmls)
		surfSet = set(surfaces)
		for bg in curSel.barrenGraphs():
			if isinstance(bg, chimera.VRMLModel) and bg in vrmlSet:
				curSelIds.append(sessionID(bg))
		# MSMSModel not "barren"; has surface-piece children
		for g in curSel.graphs():
			if isinstance(g, chimera.MSMSModel) and g in surfSet:
				curSelIds.append([sessionID(g.molecule)])

		savedSels = []
		from copy import copy
		for selName, sel in selection.savedSels.items():
			badMols = [m for m in sel.molecules() if not autoRestorable(m)]
			filtSel = copy(sel)
			if badMols:
				filtSel.remove(badMols)
			ids = []
			for a in filtSel.atoms():
				ids.append(sessionID(a))
			for b in filtSel.bonds():
				ids.append(sessionID(b))
			for pb in filtSel.pseudobonds():
				ids.append(sessionID(pb))
			savedSels.append((selName, ids))

		replyobj.status("Gathering transformation information...",
			blankAfter=0, secondary=True)
		xfDict = {}
		for m in (molecules + vrmls):
			xf = m.openState.xform
			rotV, angle = xf.getRotation()
			rot = rotV.data()
			trans = xf.getTranslation().data()
			xfDict[sessionID(m)] = ((rot, angle), trans, m.openState.active)

		replyobj.status("Gathering view information...",
			blankAfter=0, secondary=True)
		camera = viewer.camera

		viewerAttrs = {}
		for va in ("viewSize", "scaleFactor", "clipping", "highlight",
			   "depthCue", "depthCueRange", "showSilhouette",
			   "silhouetteColor", "silhouetteWidth", "labelsOnTop",
			   "backgroundMethod", "singleLayerTransparency",
			   "showShadows", "shadowTextureSize",
			   "angleDependentTransparency"):
			try:
				if va.endswith("Color"):
					viewerAttrs[va] = colorID(getattr(viewer, va))
				else:
					viewerAttrs[va] = getattr(viewer, va)
			except AttributeError:
				pass
		if hasattr(viewer, 'backgroundGradient'):
			from chimera.paletteoptions import gradientToPref
			bgg = list(viewer.backgroundGradient)
			if bgg[0]:
				bgg[0:2] = gradientToPref(bgg[0:2])
			viewerAttrs['backgroundGradient'] = bgg
		if hasattr(viewer, 'backgroundImage'):
			bgi = list(viewer.backgroundImage)
			if bgi[0]:
				image = bgi[0]
				bgi[0] = (image.mode, image.size, image.tostring())
			viewerAttrs['backgroundImage'] = bgi
		cameraAttrs = {}
		for ca in ("ortho", "nearFar", "focal", "center", "fieldOfView",
								"eyeSeparation"):
			cameraAttrs[ca] = getattr(camera, ca)

		if hasattr(viewer, 'depthCueColor'):
			viewerFog = viewer.depthCueColor
		else:
			viewerFog = None
		viewerInfo = {
			"detail": chimera.LODControl.get().quality,
			"viewerFog": colorID(viewerFog),
			"viewerBG": colorID(viewer.background),
			"viewerHL": colorID(viewer.highlightColor),
			"viewerAttrs": viewerAttrs,
			"cameraAttrs": cameraAttrs,
			"cameraMode": camera.mode(),
			}
		if not chimera.nogui:
			from chimera import tkgui
			if not tkgui.usingDefaultScreenWidth():
				viewerInfo['screenWidthMM'] = tkgui.getScreenMMWidth()
			
		# start printing into buffer so that color map can be inserted here
		replyobj.status("Writing preliminary session info...",
			blankAfter=0, secondary=True)
		print>> buf, "\tviewerInfo =", sesRepr(viewerInfo, floatPrecision=14)
		print>> buf, """
\treplyobj.status("Initializing session restore...", blankAfter=0,
\t\tsecondary=True)
\tfrom SimpleSession.versions.v65 import expandSummary
\tinit(dict(enumerate(expandSummary(colorInfo))))
\treplyobj.status("Restoring colors...", blankAfter=0,
\t\tsecondary=True)
\trestoreColors(colors, materials)
\treplyobj.status("Restoring molecules...", blankAfter=0,
\t\tsecondary=True)
\trestoreMolecules(molInfo, resInfo, atomInfo, bondInfo, crdInfo)
\treplyobj.status("Restoring surfaces...", blankAfter=0,
\t\tsecondary=True)
\trestoreSurfaces(surfInfo)
\treplyobj.status("Restoring VRML models...", blankAfter=0,
\t\tsecondary=True)
\trestoreVRML(vrmlInfo)
\treplyobj.status("Restoring pseudobond groups...", blankAfter=0,
\t\tsecondary=True)
\trestorePseudoBondGroups(pbInfo)
\treplyobj.status("Restoring model associations...", blankAfter=0,
\t\tsecondary=True)
\trestoreModelAssociations(modelAssociations)
\treplyobj.status("Restoring camera...", blankAfter=0,
\t\tsecondary=True)
\trestoreViewer(viewerInfo)

try:
	restoreCoreModels()
except:
	reportRestoreError("Error restoring core models")

\treplyobj.status("Restoring extension info...", blankAfter=0,
\t\tsecondary=True)
"""
		replyobj.status("Writing extension session info...", blankAfter=0,
			secondary=True)
		chimera.triggers.activateTrigger(SAVE_SESSION, buf, raiseError=True)
		replyobj.status("Writing remaining session info...", blankAfter=0,
			secondary=True)
		print>> buf, """
def restoreRemainder():
\tfrom SimpleSession.versions.v65 import restoreWindowSize, \\
\t     restoreOpenStates, restoreSelections, restoreFontInfo, \\
\t     restoreOpenModelsAttrs, restoreModelClip, restoreSilhouettes
"""
		# any use of colors below have to have those colors also run through
		# colorID() before init() gets printed, so that the color map contains
		# those colors
		print>> buf, "\tcurSelIds = ", sesRepr(curSelIds)
		print>> buf, "\tsavedSels =", sesRepr(savedSels)
		print>> buf, "\topenModelsAttrs = { 'cofrMethod': %d }" % (
						chimera.openModels.cofrMethod)
		if chimera.openModels.cofrMethod == chimera.openModels.Fixed:
			cofr = chimera.openModels.cofr
			print>> buf, "\tfrom chimera import Point"
			print>> buf, "\topenModelsAttrs['cofr'] = Point(%g, %g, %g)" \
							% (cofr.x, cofr.y, cofr.z)
		print>> buf, "\twindowSize =", sesRepr(chimera.viewer.windowSize)
		print>> buf, "\txformMap =", sesRepr(xfDict, floatPrecision=14)
		print>> buf, "\tfontInfo =", sesRepr(fontInfo)
		print>> buf, "\tclipPlaneInfo =", sesRepr(clipPlaneInfo)
		print>> buf, "\tsilhouettes =", sesRepr(silhouettes)
		print>> buf, """
\treplyobj.status("Restoring window...", blankAfter=0,
\t\tsecondary=True)
\trestoreWindowSize(windowSize)
\treplyobj.status("Restoring open states...", blankAfter=0,
\t\tsecondary=True)
\trestoreOpenStates(xformMap)
\treplyobj.status("Restoring font info...", blankAfter=0,
\t\tsecondary=True)
\trestoreFontInfo(fontInfo)
\treplyobj.status("Restoring selections...", blankAfter=0,
\t\tsecondary=True)
\trestoreSelections(curSelIds, savedSels)
\treplyobj.status("Restoring openModel attributes...", blankAfter=0,
\t\tsecondary=True)
\trestoreOpenModelsAttrs(openModelsAttrs)
\treplyobj.status("Restoring model clipping...", blankAfter=0,
\t\tsecondary=True)
\trestoreModelClip(clipPlaneInfo)
\treplyobj.status("Restoring per-model silhouettes...", blankAfter=0,
\t\tsecondary=True)
\trestoreSilhouettes(silhouettes)

\treplyobj.status("Restoring remaining extension info...", blankAfter=0,
\t\tsecondary=True)
try:
	restoreRemainder()
except:
	reportRestoreError("Error restoring post-model state")
from SimpleSession.versions.v65 import makeAfterModelsCBs
makeAfterModelsCBs()
"""
		print>> buf, "from SimpleSession.versions.v65 import endRestore"
		print>> buf, "replyobj.status('Finishing restore...', blankAfter=0, secondary=True)"
		print>> buf, "endRestore(%s)" % sesRepr(sesKw)

		print>> buf, "replyobj.status('', secondary=True)"
		print>> buf, "replyobj.status('Restore finished.')"

		# insert color map
		print>> outf, "\tcolorInfo =", sesRepr(summarizeVals(_colorInfo))

		# print buffered output
		print>> outf, buf.getvalue()
		buf.close()
	from versions import globals
	del globals.sessionMap
	_colorInfo = _color2id = None
	replyobj.status("", secondary=True)
	replyobj.status("Session written")

def colorID(color):
	if color is None:
		return None
	try:
		return _color2id[color]
	except KeyError:
		pass
	index = len(_color2id)
	_color2id[color] = index
	_colorInfo.append((color.name(), eval(sesRepr(color.rgba()))))
	return index

def summarizeVals(vals, consecutiveExceptions=False, hashable=True):
	if not hashable:
		# numpy's handling of the '==' operator is bullshit, so the following is necessary...
		import numpy
		if vals and not isinstance(vals[0], numpy.ndarray) and vals.count(None) == len(vals):
			return len(vals), None, []
		return len(vals), None, [repr(v) for v in vals]
	sorted = {}
	for i, val in enumerate(vals):
		sorted.setdefault(val, []).append(i)
	mostCount = None
	for val, indices in sorted.items():
		if mostCount is None or len(indices) > mostCount:
			mostVal = val
			mostCount = len(indices)
	if mostCount is None:
		return len(vals), None, {}
	del sorted[mostVal]
	if consecutiveExceptions:
		for k, v in sorted.items():
			sorted[k] = (None, summarizeSequentialVals(v))
	return len(vals), mostVal, sorted

def summarizeSequentialVals(vals):
	summary = []
	first = True
	startVal = prevVal = None
	numNone = 0
	for v in vals:
		if first:
			startVal = prevVal = v
			first = False
			if v == None:
				numNone += 1
			continue
		if v == None:
			numNone += 1
			if startVal != None:
				summary.append((startVal, prevVal - startVal + 1))
			startVal = prevVal = None
		elif prevVal == None:
			summary.append((None, numNone))
			numNone = 0
			startVal = prevVal = v
		elif v == prevVal + 1:
			prevVal = v
		else:
			summary.append((startVal, prevVal - startVal + 1))
			startVal = prevVal = v
	if numNone > 0:
		summary.append((None, numNone))
	elif startVal != None:
		summary.append((startVal, prevVal - startVal + 1))
	return summary

def saveOptionalAttrs(level, items):
	saveDict = {}
	for optAttr, info in optionalAttributes[level].items():
		hashable, sequentialValues = info
		vals = [getattr(i, optAttr, None) for i in items]
		if sequentialValues:
			sv = summarizeSequentialVals(vals)
			if len(sv) == 1 and sv[0][0] == None:
				continue
		else:
			sv = summarizeVals(vals, hashable=hashable)
			if sv[1] is None and not sv[2]:
				continue
		saveDict[optAttr] = (hashable, sequentialValues, sv)
	return saveDict

def pickled(data):
	import cPickle, base64
	pData = cPickle.dumps(data, protocol=2)
	peData = base64.b64encode(pData)
	# Python can't parse 2GB+ strings, so break into ~1GB chunks
	chunkSize = 1000000000
	if len(peData) <= chunkSize:
		final_string = repr(peData)
	else:
		strings = []
		for index in range(0, len(peData), chunkSize):
			strings.append("%s" % repr(peData[index:index+chunkSize]))
		final_string = "".join(strings)

	return "cPickle.loads(base64.b64decode(%s))" % final_string
