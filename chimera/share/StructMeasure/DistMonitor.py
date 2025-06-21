# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: DistMonitor.py 41503 2017-05-03 20:06:45Z pett $

import chimera
from chimera.misc import getPseudoBondGroup

monitoredGroups = set()
def addMonitoredGroup(grpInfo, color="yellow", lineType=chimera.Dash,
		lineWidth=1.0):
	if isinstance(grpInfo, chimera.PseudoBondGroup):
		g = grpInfo
		if g in monitoredGroups:
			return g
	else:
		g = getPseudoBondGroup(grpInfo, create=False)
		if g:
			if g in monitoredGroups:
				return g
		else:
			g = getPseudoBondGroup(grpInfo, modelID=chimera.OpenModels.Default,
				hidden=True)
			def _setAttrs(color=color, lt=lineType, lw=lineWidth, g=g):
				from chimera.colorTable import getColorByName
				if type(color) in [tuple, list]:
					g.color = chimera.MaterialColor(*color[:3])
				else:
					g.color = getColorByName(color)
				g.lineType = lt
				g.lineWidth = lw
			# delay setting the color until colors are set up
			chimera.registerPostGraphicsFunc(_setAttrs)
	g.fixedLabels = False
	g.dmUpdateCallbacks = []
	monitoredGroups.add(g)
	if g.pseudoBonds:
		updateDistance()
	return g

def removeMonitoredGroup(g):
	if g in monitoredGroups:
		monitoredGroups.remove(g)
		delattr(g, 'fixedLabels')
		delattr(g, 'dmUpdateCallbacks')

def _pbgDeletionCB(_1, _2, info):
	if info.deleted:
		global monitoredGroups
		monitoredGroups -= info.deleted
chimera.triggers.addHandler('PseudoBondGroup', _pbgDeletionCB, None)

def _pbAdditionCB(_1, _2, info):
	if info.created:
		relPBs = [pb for pb in info.created
			# chain-trace pseudobonds can get deleted during trigger processing,
			# so check __destroyed__
			if not pb.__destroyed__ and pb.pseudoBondGroup in monitoredGroups]
		updateDistance(pbs=relPBs)
chimera.triggers.addHandler('PseudoBond', _pbAdditionCB, None)

from prefs import prefs, DIST_COLOR, DIST_LINE_TYPE, DIST_LINE_WIDTH
distanceMonitor = addMonitoredGroup('distance monitor',
	color=prefs[DIST_COLOR], lineType=prefs[DIST_LINE_TYPE],
	lineWidth=prefs[DIST_LINE_WIDTH])
distanceHandlers = {}
from SimpleSession import registerAttribute
registerAttribute(chimera.PseudoBondGroup, "fixedLabels")

def updateDistance(pbs=None, *args):
	if distanceHandlers:
		for mg in monitoredGroups:
			if len(mg.pseudoBonds) > 0:
				break
		else:
			_clearHandlers()
			return
	else:
		for mg in monitoredGroups:
			if len(mg.pseudoBonds) > 0:
				_startHandlers()
				break
	if pbs is None:
		pbs = [pb for mg in monitoredGroups for pb in mg.pseudoBonds]
	usedGroups = set()
	for b in pbs:
		grp = b.pseudoBondGroup
		usedGroups.add(grp)
		format = '%%.%df' % _pref['precision']
		if _pref['show units']:
			format += u'\u00C5'
		b.distance = format % b.length()
		if not grp.fixedLabels:
			b.label = b.distance
	for mg in usedGroups:
		for cb in mg.dmUpdateCallbacks:
			cb()

def addDistance(atom1, atom2):
	b = _findDistance(atom1, atom2)
	if b is not None:
		from chimera import UserError
		raise UserError('Distance monitor already exists')
	if atom1 == atom2:
		from chimera import UserError
		raise UserError("Can't make a distance monitor from an atom to itself!")
	b = distanceMonitor.newPseudoBond(atom1, atom2)
	from chimera import replyobj
	replyobj.info("Distance between %s and %s: %.*f\n" % (atom1, atom2,
					_pref['precision'], b.length()))
	b.drawMode = chimera.Bond.Wire
	return b

def removeDistance(*args):
	if len(args) == 1:
		b = args[0]
	elif len(args) == 2:
		b = _findDistance(args[0], args[1])
		if b is None:
			raise ValueError, 'distance monitor does not exist'
	else:
		raise ValueError, 'wrong number of arguments to removeDistance'
	distanceMonitor.deletePseudoBond(b)

def _clearHandlers():
	for trigName, handler in distanceHandlers.items():
		chimera.triggers.deleteHandler(trigName, handler)
	distanceHandlers.clear()

def _findDistance(atom1, atom2):
	for b in distanceMonitor.pseudoBonds:
		atoms = b.atoms
		if atoms[0] == atom1 and atoms[1] == atom2:
			return b
		if atoms[0] == atom2 and atoms[1] == atom1:
			return b
	return None

def _startHandlers():
	def justCSMods(trigName, myData, changes):
		if changes.modified:
			updateDistance()
	distanceHandlers['CoordSet'] = chimera.triggers.addHandler(
					'CoordSet', justCSMods, None)
	def justCoordSets(trigName, myData, changes):
		if 'activeCoordSet changed' in changes.reasons:
			updateDistance()
	distanceHandlers['Molecule'] = chimera.triggers.addHandler(
					'Molecule', justCoordSets, None)
	def openStateCB(trigName, myData, changes):
		if 'some transformations change' in changes.reasons:
			# some models moved realtive to others...
			updateDistance()
	distanceHandlers['OpenState'] = chimera.triggers.addHandler(
					'OpenState', openStateCB, None)

from chimera import preferences
_pref = preferences.addCategory("Distance Monitors",
				preferences.HiddenCategory,
				optDict={
					'precision': 3,
					'show units': True
				})

def precision():
	return _pref['precision']

def setPrecision(p, fromGui=False):
	if not isinstance(p, int):
		raise TypeError, "precision must be integer"
	if p < 0:
		raise ValueError, "precision must be non-negative"
	_pref['precision'] = p
	updateDistance()
	if not fromGui and not chimera.nogui:
		from gui import StructMeasure
		dlg = chimera.dialogs.find(StructMeasure.name, create=False)
		if dlg:
			dlg.distPrecisionChoice.insert(0, str(precision()))

def showUnits(val=None, fromGui=False):
	if val is None:
		return _pref['show units']
	_pref['show units'] = val
	updateDistance()
	if not fromGui and not chimera.nogui:
		from gui import StructMeasure
		dlg = chimera.dialogs.find(StructMeasure.name, create=False)
		if dlg:
			dlg.showUnitsVar.set(val)

##### saving/restoring scenes:
from chimera import SCENE_TOOL_SAVE, SCENE_TOOL_RESTORE
def _saveScene(trigName, myData, scene):
	distInfo = scene.tool_settings["distances"] = {}
	distInfo['version'] = 1
	distInfo['precision'] = precision()
	distInfo['show units'] = showUnits()
	groupInfo = distInfo['group info'] = []
	for mg in monitoredGroups:
		info = {}
		groupInfo.append((mg.category, info))
		info['fixed labels'] = mg.fixedLabels
		from Animate.Tools import pbAttrNames, sceneID, colorID
		for pb in mg.pseudoBonds:
			attrInfo = info[tuple([sceneID(a) for a in pb.atoms])] = {}
			for attrName in pbAttrNames:
				if attrName.lower().endswith('color'):
					attrInfo[attrName] = colorID(getattr(pb, attrName))
				else:
					attrInfo[attrName] = getattr(pb, attrName)
chimera.triggers.addHandler(SCENE_TOOL_SAVE, _saveScene, None)

def _restoreScene(trigName, myData, scene):
	distInfo = scene.tool_settings.get("distances")
	if not distInfo:
		return
	if precision() != distInfo['precision']:
		setPrecision(distInfo['precision'])
	if showUnits() != distInfo['show units']:
		showUnits(distInfo['show units'])
	for category, info in distInfo['group info']:
		for mg in monitoredGroups:
			if mg.category == category:
				break
		else:
			continue
		if mg == distanceMonitor and info['fixed labels'] != mg.fixedLabels \
		and not chimera.nogui:
			fixedChanged = True
			if info['fixed labels']:
				labelType = None
			else:
				labelType = "Distance"
		else:
			fixedChanged = False
		mg.fixedLabels = info['fixed labels']
		from Animate.Tools import pbAttrNames, idLookup, getColor
		pbInfoLookup = {}
		sceneDists = set()
		for atomIDs, pbInfo in info.items():
			if isinstance(atomIDs, basestring):
				continue
			atoms = tuple([idLookup(atomID) for atomID in atomIDs])
			pbInfoLookup[atoms] = pbInfo
			sceneDists.add(atoms)
		prevDists = set([pb.atoms for pb in mg.pseudoBonds])
		for delDist in prevDists - sceneDists:
			removeDistance(*delDist)
		for addDist in sceneDists - prevDists:
			addDistance(*addDist)
		for pb in mg.pseudoBonds:
			pbInfo = pbInfoLookup[tuple(pb.atoms)]
			for attrName in pbAttrNames:
				if attrName == "label":
					if mg.fixedLabels and fixedChanged and labelType == None:
						if pbInfo[attrName]:
							labelType = "None"
						else:
							labelType = "ID"
				if attrName.lower().endswith('color'):
					setattr(pb, attrName, getColor(pbInfo[attrName]))
				else:
					setattr(pb, attrName, pbInfo[attrName])
		if fixedChanged and labelType != None:
			from gui import StructMeasure
			dlg = chimera.dialogs.find(StructMeasure.name, create=False)
			if dlg:
				dlg.distLabelChoice.setvalue(labelType)
chimera.triggers.addHandler(SCENE_TOOL_RESTORE, _restoreScene, None)

##### saving into sessions:
def restoreDistances(version=1):
	import StructMeasure
	from StructMeasure.DistMonitor import distanceMonitor
	if len(distanceMonitor.pseudoBonds) > 0 and not distanceHandlers:
		_startHandlers()

def _sessionSave(trigName, myData, sessionFile):
	print>>sessionFile, """
try:
	import StructMeasure
	from StructMeasure.DistMonitor import restoreDistances
	registerAfterModelsCB(restoreDistances, 1)
except:
	reportRestoreError("Error restoring distances in session")
"""


from SimpleSession import SAVE_SESSION
chimera.triggers.addHandler(SAVE_SESSION, _sessionSave, None)
