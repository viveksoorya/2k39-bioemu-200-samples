# Copyright (c) 2000 by the Regents of the University of California.
# All rights reserved.  See http://www.cgl.ucsf.edu/chimera/ for
# license details.
#
# $Id: __init__.py 42544 2025-02-12 21:49:58Z goddard $

"""
Chimera module

exports all symbols from C++ _chimera module
"""

import sys, os, errno

# C++ Chimera environment classes
from _chimera import BBox, Camera, Color, ColorGroup, DirectionalLight, LODControl, Lens, LensViewer, Light, Material, MaterialColor, Model, NoGuiViewer, OGLFont, OSLAbbreviation, OpenModels, OpenState, PathFinder, PixelMap, Plane, Point, PositionalLight, Selectable, SharedState, SpotLight, Sphere, Texture, TextureColor, TrackChanges, Vector, Viewer, X3DScene, Xform

# C++ Chimera environment constants
from _chimera import CustomLine, Dash, DashDot, DashDotDot, DashDotDot_Stipple, DashDot_Stipple, Dash_Stipple, Dot, Dot_Stipple, SelDefault, SelEdge, SelGraph, SelSubgraph, SelVertex, SolidLine, Solid_Stipple

# C++ Chimera environment functions
from _chimera import angle, clearPickSelectable, combine, cross, dihedral, distance, error, find_bounding_sphere, find_minimum_bounding_sphere, initializeColors, intersects, lerp, memoryMap, opengl_getFloat, opengl_getInt, opengl_platform, pathFinder, setPickSelectable, sphere_pts, sqdistance, tweak_graphics, xml_quote

# C++ molecule classes
from _molecule import Atom, Bond, BondRot, ChainTrace, CoordSet, Element, GeometryVector, Mol2io, MolResId, Molecule, PDBio, PseudoBond, PseudoBondGroup, PseudoBondMgr, PyMol2ioHelper, ReadGaussianFCF, Residue, RibbonData, RibbonResidueClass, RibbonStyle, RibbonXSection, Ring, Root, SessionPDBio, Spline

# C++ molecule constants
from _molecule import RibbonStyleFixed, RibbonStyleTapered, RibbonStyleWorm, SelAtom, SelBond, SelMolecule, SelResidue

# C++ molecule functions
from _molecule import atomsBonds2Residues, bondsBetween, connectMolecule, eigenMatrix, fillCoordSet, numpyArrayFromAtoms, pdbOrder, restmplFindResidue, RMSD_fillMatrix, RMSD_matrix, pdbWrite, pdbrunNoMarks, metalAtoms, ionLikeAtoms, longBonds, isProtein, assignCategory, categorizeSolventAndIons, bondMolecules, setAtomDisplay, setAtomDrawMode, setBondDrawMode, upgradeAtomDrawMode, upgradeBondDrawMode, colorByElement

nested_timers = 0
class TimeIt:
	def __init__(self, message, min_time = 0.01, stack_trace = False):
		self.message = message
		self.min_time = min_time
		self.stack_trace = stack_trace
		import time
		self.start = time.time()
		self.reported = False
		global nested_timers
		nested_timers += 1
		self.level = nested_timers
	def __del__(self):
		if not self.reported:
			self.done()
	def done(self):
		return		# Disable timing output.
		self.reported = True
		global nested_timers
		nested_timers -= 1
		import time, sys
		t = time.time() - self.start
		if t >= self.min_time:
			indent = '  ' * (self.level-1)
			msg = '%s%s %.2f\n' % (indent, self.message, t)
			sys.__stderr__.write(msg)



#from _molecule import reportSizes
#reportSizes()

Coord = Point				# vestige for old code
Xform_translation = Xform.translation	# vestige for old session files
from _vrml import VRMLModel
from libgfxinfo import getVendor as opengl_vendor, getRenderer as opengl_renderer, getVersion as opengl_version, getOS as operating_system
from Sequence import getSequence, getSequences
Molecule.sequence = getSequence
Molecule.sequences = getSequences
Molecule.loadAllFrames = lambda self: None # trajectories will replace this
import palettes
def _labelFunc(item):
	from misc import chimeraLabel
	return chimeraLabel(item)
Atom.__str__ = _labelFunc
Bond.__str__ = _labelFunc
PseudoBond.__str__ = _labelFunc
Residue.__str__ = _labelFunc
Model.__str__ = _labelFunc
Point.__repr__ = lambda s: 'chimera.Point(%r, %r, %r)' % s.data()
Vector.__repr__ = lambda s: 'chimera.Vector(%r, %r, %r)' % s.data()
Xform.__repr__ = lambda s: 'chimera.Xform.coordFrame(%r, %r, %r, %r)' % s.getCoordFrame()
Plane.__repr__ = lambda s: 'chimera.Plane(%r, %r)' % (s.origin, s.normal)
from phipsi import getPhi, getPsi, setPhi, setPsi, \
	getChi1, getChi2, getChi3, getChi4, setChi1, setChi2, setChi3, setChi4
Residue.phi = property(getPhi, setPhi)
Residue.psi = property(getPsi, setPsi)
Residue.chi1 = property(getChi1, setChi1)
Residue.chi2 = property(getChi2, setChi2)
Residue.chi3 = property(getChi3, setChi3)
Residue.chi4 = property(getChi4, setChi4)
Residue.altLocs = property(lambda r: set([a.altLoc
							for a in r.atoms if a.altLoc.isalnum()]))
def _getMetalPbg(mol, **kw):
	if mol.id == OpenModels.Default:
		cat = "coordination complexes of %s" % (mol.name,)
		wantHint = False
	else:
		cat = "coordination complexes of %s (%s)" % (mol.name, mol)
		wantHint = True
	if 'issueHint' not in kw:
		kw['issueHint'] = wantHint
	# coordination complexes from restored sessions may not have
	# the category we expect, so use this method of looking for them
	for am in mol.associatedModels():
		if not isinstance(am, PseudoBondGroup):
			continue
		if am.category.startswith("coordination complexes"):
			break
	else:
		from misc import getPseudoBondGroup
		# don't open pbg if base Molecule not open
		try:
			x = mol.openState
			addModel = True
		except:
			addModel = False
		am = getPseudoBondGroup(cat, associateWith=[mol], addModel=addModel,
			**kw)
		if am:
			from initprefs import MOL_COMPLEX_LW, MOL_COMPLEX_COLOR, \
				MOL_COMPLEX_REPR, MOLECULE_DEFAULT
			am.lineWidth = preferences.get(MOLECULE_DEFAULT, MOL_COMPLEX_LW)
			am.color = preferences.get(MOLECULE_DEFAULT, MOL_COMPLEX_COLOR)
			depict = preferences.get(MOLECULE_DEFAULT, MOL_COMPLEX_REPR)
			if depict == "dashed lines":
				am.lineType = Dash
			if not addModel:
				# add the pbg when the Molecule gets added...
				_addMetalPbgHandlers(am, mol)
	if am and am.category != cat:
		# get PseudoBondGroup panel to show best name
		PseudoBondMgr.mgr().recategorize(am, cat)
	return am

Molecule.metalComplexGroup = _getMetalPbg

def _addMetalPbgHandlers(pbg, mol):
	def addHandler(trigName, myData, models):
		pbg, mol = myData
		if mol not in models:
			return
		openModels.add([pbg], hidden=True, sameAs=mol)
		_deleteMetalPbgHandlers(pbg)
	handlers = pbg._metalPbgHandlers = []
	handlers.append(openModels.addAddHandler(addHandler, (pbg, mol)))
	def molHandler(trigName, myData, trigData):
		pbg, mol = myData
		if mol in trigData.deleted:
			_deleteMetalPbgHandlers(pbg)
	handlers.append(triggers.addHandler('Molecule', molHandler, (pbg, mol)))

def _deleteMetalPbgHandlers(pbg):
	addHandler, molHandler = pbg._metalPbgHandlers
	openModels.deleteAddHandler(addHandler)
	triggers.deleteHandler('Molecule', molHandler)
	delattr(pbg, '_metalPbgHandlers')

# wrap labelOffset attribute to be more "pythonic"
def getLabelOffset(item):
	""" returns 3-tuple (or None if not set)
	accepts 3-tuple, Vector, or None
	"""
	rawLO = item._labelOffset
	if rawLO.x == Molecule.DefaultOffset:
		return None
	return rawLO.data()

def setLabelOffset(item, val):
	if isinstance(val, Vector):
		item._labelOffset = val
	elif val is None:
		item._labelOffset = Vector(Molecule.DefaultOffset, 0.0, 0.0)
	else:
		item._labelOffset = Vector(*val)

for offsetClass in (Atom, Bond, Residue):
	offsetClass._labelOffset = offsetClass.labelOffset
	offsetClass.labelOffset = property(getLabelOffset, setLabelOffset)

# make uniprotIndex attr available
def getUniprotIndex(res):
	if not hasattr(res, '_uniprotIndex'):
		for r in res.molecule.residues:
			r._uniprotIndex = None
		from SeqAnnotations import pdbUniprotCorrespondences, NoUniprotEntryError
		chains = res.molecule.sequences()
		for chain in chains:
			try:
				alignObjs, corrs = pdbUniprotCorrespondences(chain)
			except LimitationError:
				if hasattr(res.molecule, 'pdbHeaders') \
				and res.molecule.pdbHeaders:
					# doesn't have the _right_ headers
					raise
				# non-PDB / has no headers
				for r in chain.residues:
					if r:
						r._uniprotIndex = None
			except NoUniprotEntryError:
				for r in chain.residues:
					if r:
						r._uniprotIndex = None
			else:
				for uniprotID, uniCorrs in corrs.items():
					for pdbStart, uniprotStart, length in uniCorrs:
						for r, ui in zip(chain.residues[pdbStart:pdbStart + length],
										range(uniprotStart, uniprotStart + length)):
							if r:
								r._uniprotIndex = ui
	return res._uniprotIndex
Residue.uniprotIndex = property(getUniprotIndex)

# track session name (if any)
lastSession = None
def setLastSession(session):
	if session and not os.path.isabs(session):
		session = os.path.abspath(session)
	global lastSession
	lastSession = session
	if not nogui:
		import tkgui
		tkgui._setLastSession(session)
		if session is not None:
			from OpenSave import getRememberer
			from os.path import dirname
			getRememberer().rememberDir(dirname(session))

def _setFirstOpenSaveFolder():
	from chimera.tkgui import GENERAL, STARTUP_DIRECTORY
	import preferences
	if preferences.get(GENERAL, STARTUP_DIRECTORY):
		return
	if sys.platform == "darwin":
		# Mac icon launch starts in '/'
		ignoreDir = "/"
	elif sys.platform == "win32":
		return
	else:
		# Linux start in the user's home dir
		ignoreDir = os.path.expanduser("~")
	if os.getcwd() == ignoreDir:
		return
	from OpenSave import getRememberer
	getRememberer().rememberDir(os.getcwd())

# track description associated with session
# 'None' means an old session restored...
_lastSessionDescriptKw = {}
def setLastSessionDescriptKw(kw, saving=False):
	global _lastSessionDescriptKw
	_lastSessionDescriptKw = kw
	if not saving and not nogui:
		import dialogs
		from SimpleSession.gui import SaveSessionDialog
		dlg = dialogs.find(SaveSessionDialog.name)
		if dlg:
			dlg.updateDescriptionWidgets()
		else:
			# can do this in else clause since the Notepad
			# and SimpleSession text widgets are peers...
			from Notepad.gui import NotepadDialog
			dlg = dialogs.find(NotepadDialog.name)
			if dlg:
				if kw is None:
					descript = ""
				else:
					descript = kw.get('description', '')
				dlg.text.setvalue(descript)
				dlg.text.component('text').edit_modified(False)

def getLastSessionDescriptKw():
	global _lastSessionDescriptKw
	if _lastSessionDescriptKw is None:
		kw = {}
	else:
		kw = _lastSessionDescriptKw
	if not nogui:
		import dialogs
		from SimpleSession.gui import SaveSessionDialog
		dlg = dialogs.find(SaveSessionDialog.name)
		if dlg:
			descript = dlg.description.getvalue()
			if descript.strip():
				kw['description'] = descript
		else:
			# can do this in else clause since the Notepad
			# and SimpleSession text widgets are peers...
			from Notepad.gui import NotepadDialog
			dlg = dialogs.find(NotepadDialog.name)
			if dlg:
				descript = dlg.text.getvalue()
				if descript.strip():
					kw['description'] = descript
	return kw

# MSMSModel is implemented as a SurfaceModel
from MoleculeSurface import MSMSModel

# defaults for command line options
debug = False
multisample = False
nostatus = False	# True if no status output in nogui mode
silent = False		# True if no status/info/warning output in nogui mode
stereo = 'mono'		# stereo camera mode
bgopacity = False	# True if background opacity is requested
visual = None
screen = None
title = "UCSF Chimera"
geometry = None
preferencesFile = None
fullscreen = False

# stereo abbrebiations -- used for startup (shell) and chimera command lines
StereoKwMap = {
	'mono':			'mono',
	'off':			'mono',
	'seq':			'sequential stereo',
	'sequential':		'sequential stereo',
	'on':			'sequential stereo',
	'rev':			'reverse sequential stereo',
	'rev seq':		'reverse sequential stereo',
	'reverse':		'reverse sequential stereo',
	'reverse seq':		'reverse sequential stereo',
	'reverse sequential':	'reverse sequential stereo',
	'cross eye':		'cross-eye stereo',
	'cross-eye':		'cross-eye stereo',
	'crosseye':		'cross-eye stereo',
	'cross':		'cross-eye stereo',
	'wall eye':		'wall-eye stereo',
	'wall-eye':		'wall-eye stereo',
	'walleye':		'wall-eye stereo',
	'wall':			'wall-eye stereo',
	'left':			'stereo left eye',
	'left eye':		'stereo left eye',
	'left-eye':		'stereo left eye',
	'right':		'stereo right eye',
	'right eye':		'stereo right eye',
	'right-eye':		'stereo right eye',
	'row interleaved':	'row stereo, right eye even',
	'row':			'row stereo, right eye even',
	'row even':		'row stereo, right eye even',
	'row odd':		'row stereo, right eye odd',
	'red-cyan':		'red-cyan stereo',
	'anaglyph':		'red-cyan stereo',
	'green-magenta':	'green-magenta stereo',
	'trioscopic':   	'green-magenta stereo',
	'dti':			'DTI side-by-side stereo',
	'DTI':			'DTI side-by-side stereo',
	'dti side-by-side':	'DTI side-by-side stereo',
	'DTI side-by-side':	'DTI side-by-side stereo',
}

# default viewer
nogui = True
if opengl_platform() != 'OSMESA':
	viewer = NoGuiViewer()
else:
	viewer = LensViewer()

_postGraphicsFuncs = []
_postGraphics = False

def registerPostGraphicsFunc(func):
	"""Register a function to execute when the graphics state is ready"""

	if _postGraphics:
		# already ready
		func()
	else:
		_postGraphicsFuncs.append(func)

registerPostGraphicsFunc(_setFirstOpenSaveFolder)

class ChimeraExit(Exception):
	"""Use this exception for known exit error states
	where a backtrace isn't needed.
	"""
	pass

class CancelOperation(Exception):
	"""
	User requested cancelling a long running operation, such as reading
	a file.
	"""

class NotABug(Exception):
	"""
	Base-class for anticipated errors. When these errors
	are caught by top-level exception-handling machinery,
	the message will not include a traceback
	"""
	pass

class UserError(NotABug):
	"""
	An error that results from a wrongful action taken by a user;
	They did something they weren't supposed to.
	"""
	pass

class LimitationError(NotABug):
	"""
	An error that results from a limitation within Chimera;
	Chimera [knowingly] doesn't do what it should do.
	"""
	pass

class NonChimeraError(NotABug):
	"""
	An error that results from circumstances beyond our control,
	such as a temporary network error -- don't want a bug report.
	"""

class ChimeraSystemExit(SystemExit):
	"""Used to allow Chimera to exit faster"""
	pass

# wrap saving functions that derive from NameMap so that a reference is kept,
# otherwise the saved objects instantly disappear since nothing in Python
# references them
for className in ['Color', 'Texture', 'Material', 'PixelMap']:
	args = (className,) * 7
	exec """
_saved%ss = set()
def _%sSave(item, name):
	_saved%ss.add(item)
	item._realSave(name)
%s._realSave = %s.save
%s.save = _%sSave
""" % args
# SimpleSession uses these save dicts, so changes need to be coordinated...


import triggerSet
triggers = triggerSet.TriggerSet()

# add triggers for each class that we track changes to
for name in TrackChanges.get().enrolled():
	name = name.split('.')[-1]	# drop leading '_chimera.'
	triggers.addTrigger(name)
del name

# add trigger for application exit
APPQUIT = "Chimera exit"
triggers.addTrigger(APPQUIT)
CONFIRM_APPQUIT = "confirm exit"
triggers.addTrigger(CONFIRM_APPQUIT)

# add trigger for session close
CLOSE_SESSION = "close session"
triggers.addTrigger(CLOSE_SESSION)
CONFIRM_CLOSE_SESSION = "close session confirmation"
triggers.addTrigger(CONFIRM_CLOSE_SESSION)
def closeSession():
	import preferences
	if not nogui:
		from tkgui import GENERAL, CONFIRM_EXIT
		if preferences.get(GENERAL, CONFIRM_EXIT) != "never":
			msgs = []
			triggers.activateTrigger(CONFIRM_CLOSE_SESSION, msgs)
			for msg in msgs:
				if not msg:
					message = "Really close session?"
				else:
					message = msg + "\nReally close session?"
				from baseDialog import AskYesNoDialog
				import tkgui
				if AskYesNoDialog(message).run(tkgui.app) == "no":
					return
	triggers.activateTrigger(CLOSE_SESSION, None)
	from selection import delAllNamedSels
	delAllNamedSels()
	from Midas import removeAllSavedPositions
	removeAllSavedPositions()
	openModels.close(openModels.list())
	for hidden in openModels.list(all=1):
		if not hidden.__destroyed__ and hidden.id != -1:
			# "unclosable" groups or groups that will close
			# along with their non-hidden model counterpart
			continue
		openModels.close(hidden)
	# reset background
	from bgprefs import BACKGROUND, BG_METHOD, BG_COLOR, BG_GRADIENT, BG_IMAGE
	try:
		bgMethod = preferences.getOption(BACKGROUND, BG_METHOD).savedValue()
	except KeyError:
		# gui viewer in nogui mode
		bgMethod = None
	from Midas import background
	background(color=preferences.getOption(BACKGROUND, BG_COLOR).savedValue())
	if not isinstance(viewer, LensViewer):
		return
	camera_prefs = preferences.get("Viewing", "SideCam")
	if camera_prefs is None:
		viewer.camera.ortho = False
	else:
		viewer.camera.ortho = camera_prefs.get("projection", False)
	if bgMethod == viewer.Gradient:
		gradient, opacity = preferences.getOption(BACKGROUND,
					BG_GRADIENT).savedValue()
		background(gradient=gradient, opacity=opacity)
	elif bgMethod == viewer.Image:
		image, scale, tiling, opacity = preferences.getOption(
					BACKGROUND, BG_IMAGE).savedValue()
		background(image=image, scale=scale, tiling=tiling, opacity=opacity)

# add triggers for scene save/restore
SCENE_TOOL_SAVE = 'scene tool save'
SCENE_TOOL_RESTORE = 'scene tool restore'
triggers.addTrigger(SCENE_TOOL_SAVE)
triggers.addTrigger(SCENE_TOOL_RESTORE)

# add triggers for animation keyframe transitions
ANIMATION_TRANSITION_START = 'animation transition start'
ANIMATION_TRANSITION_STEP = 'animation transition step'
ANIMATION_TRANSITION_FINISH = 'animation transition finish'
triggers.addTrigger(ANIMATION_TRANSITION_START)
triggers.addTrigger(ANIMATION_TRANSITION_STEP)
triggers.addTrigger(ANIMATION_TRANSITION_FINISH)

# add trigger for movie preferences update
MOVIE_PREF_UPDATE = 'movie_pref_update'
triggers.addTrigger(MOVIE_PREF_UPDATE)

# for updates ala checkForChanges
triggers.addTrigger('new frame')
triggers.addTrigger('post-frame')
triggers.addTrigger('check for changes')
triggers.addTrigger('monitor changes')

# add triggers for file open and save
triggers.addTrigger('file open')
triggers.addTrigger('file save')

# add trigger for command error
COMMAND_ERROR = "command error"
triggers.addTrigger(COMMAND_ERROR)

# add trigger for script abort
SCRIPT_ABORT = "script abort"
triggers.addTrigger(SCRIPT_ABORT)

# add trigger for motion start/stop
MOTION_START = "motion start"
MOTION_STOP = "motion stop"
_checkForChangesHandlerID = _motionDelayID = None
def _cancelMotionDelayHandlers():
	global _checkForChangesHandlerID, _motionDelayID
	if _motionDelayID:
		from tkgui import app
		app.after_cancel(_motionDelayID)
		_motionDelayID = None
	if _checkForChangesHandlerID:
		triggers.deleteHandler('check for changes',
						_checkForChangesHandlerID)
		_checkForChangesHandlerID = None

def _afterCB():
	global _checkForChangesHandlerID, _motionDelayID
	_motionDelayID = None
	triggers.activateTrigger(MOTION_STOP, None)

def _redrawCB(trigName, myData, trigData):
	global _checkForChangesHandlerID, _motionDelayID
	triggers.deleteHandler('check for changes', _checkForChangesHandlerID)
	_checkForChangesHandlerID = None
	if nogui:
		triggers.activateTrigger(MOTION_STOP, None)
		return
	from tkgui import app
	_motionDelayID = app.after(1000, _afterCB)

def _motionCB(trigName, myData, trigData):
	global _checkForChangesHandlerID, _motionDelayID
	if 'transformation change' not in trigData.reasons:
		return
	if not _checkForChangesHandlerID and not _motionDelayID:
		triggers.activateTrigger(MOTION_START, None)
	_cancelMotionDelayHandlers()
	# schedule a motion stop after a certain amount of delay past the
	# first redraw
	_checkForChangesHandlerID = triggers.addHandler(
					'check for changes', _redrawCB, None)

def _startMotionTriggers():
	global _motionHandlerID
	_motionHandlerID = triggers.addHandler('OpenState', _motionCB, None)

def _stopMotionTriggers():
	global _motionHandlerID
	_cancelMotionDelayHandlers()
	triggers.deleteHandler('OpenState', _motionHandlerID)
	_motionHandlerID = None

_startHandlers = _stopHandlers = False
def _triggerActivityCB(trigName, onOff):
	global _startHandlers, _stopHandlers
	if onOff == 1:
		if not _startHandlers and not _stopHandlers:
			_startMotionTriggers()
	if trigName == MOTION_START:
		_startHandlers = onOff
	else:
		_stopHandlers = onOff
	if not _startHandlers and not _stopHandlers:
		_stopMotionTriggers()

triggers.addTrigger(MOTION_START, _triggerActivityCB)
triggers.addTrigger(MOTION_STOP, _triggerActivityCB)

def oslLevel(obj):
	"""Return OSL level of object or None.

	The OSL level is one of SelGraph, SelSubgraph, SelVertex, SelEdge.
	"""
	if hasattr(obj, 'oslLevel'):
		return obj.oslLevel()
	return None

def isModel(obj):
	"""Return if obj is a model."""
	return isinstance(obj, Model)

#import oslParser
#
# add color testing capability to OSL
#
def testColor(c, op, s):
	import oslParser
	if ',' in s:
		try:
			vals = [float(x) for x in s.split(',')]
		except ValueError:
			raise SyntaxError("RGBA values must be floating point")
		if len(vals) > 4:
			raise SyntaxError("RGBA can be at most 4 numbers")
	else:
		clr = Color.lookup(s)
		if clr is None:
			# color doesn't exist or hasn't been used/defined yet
			return False
		vals = clr.rgba()[:3]
	equal = True
	rgba = c.rgba()
	for i, v in enumerate(vals):
		if abs(rgba[i] - v) >= 0.001:
			equal = False
			break
	if op in [oslParser.OpEQ1, oslParser.OpEQ2]:
		return equal
	elif op == oslParser.OpNE:
		return not equal
	else:
		return False

#
# add element testing capability to OSL
#
def testElement(e, op, value):
	import oslParser
	if ',' in value:
		raise SyntaxError, 'comma not allowed in element name'
	if op == oslParser.OpMatch:
		return 0
	try:
		value = int(value)
	except ValueError:
		d = cmp(e.name.lower(), value.lower())
	else:
		d = cmp(e.number, value)
	if d < 0:
		if op in (oslParser.OpNE, oslParser.OpLE, oslParser.OpLT):
			return 1
	elif d == 0:
		if op in (oslParser.OpEQ1, oslParser.OpEQ2, oslParser.OpGE,
								oslParser.OpLE):
			return 1
	else:
		if op in (oslParser.OpNE, oslParser.OpGE, oslParser.OpGT):
			return 1
	return 0

#
# add draw mode testing capability to OSL
#
def testDrawMode(e, op, value):
	from chimera import Atom
	import oslParser
	wireNames = ("wire", "wireframe", "dot")
	stickNames = ("stick", "endcap")
	ballNames = ("ball", "bs", "ball-and-stick", "ball and stick", "b+s",
								"ball+stick")
	sphereNames = ("sphere", "cpk", "space-filling")

	nameMap = {}
	nameMap[Atom.Dot] = wireNames
	nameMap[Atom.EndCap] = stickNames
	nameMap[Atom.Ball] = ballNames
	nameMap[Atom.Sphere] = sphereNames

	if op in [oslParser.OpEQ1, oslParser.OpEQ2]:
		return value in nameMap[e.drawMode]
	elif op == oslParser.OpNE:
		return value not in nameMap[e.drawMode]
	else:
		return 0

def registerOSLTests():
	import oslParser
	oslParser.registerTest(MaterialColor, testColor)
	oslParser.registerTest(Element, testElement)
	oslParser.registerTest((Atom, 'drawMode'), testDrawMode)

#
# export findfile
#

def findfile(filename, category=""):
	if filename.startswith("http:"):
		return filename
	if os.path.isabs(filename):
		if os.path.exists(filename):
			return filename
		raise IOError(errno.ENOENT, os.strerror(errno.ENOENT), filename)
	from OpenSave import tildeExpand
	simple = tildeExpand(filename)
	if os.path.exists(simple):
		return simple
	file = pathFinder().firstExistingFile("chimera",
					os.path.join(category, filename))
	if not file:
		raise IOError(errno.ENOENT, os.strerror(errno.ENOENT), filename)
	return file

def selectionOperation(sel):
	if nogui:
		from selection import setCurrent
		return setCurrent(sel)
	else:
		import tkgui
		return tkgui.selectionOperation(sel)

def getSelMode():
	if nogui:
		return 'replace'
	from tkgui import selMode
	return selMode

def _pdbFetch(site, url, params, statusName, saveDir='', saveName='',
		ignore_cache=False, post=False):

	if saveName and not ignore_cache:
		import fetch
		path = fetch.fetch_local_file(saveDir, saveName)
		if path:
			return path
	import replyobj
	replyobj.status('Fetching %s from web site %s' %
					(statusName, site), blankAfter=0)

	import tasks
	cancelled = []
	def cancelCB():
		cancelled.append(True)
	task = tasks.Task("Fetch %s" % statusName, cancelCB, modal=True)

	def reportCB(barrived, bsize, fsize):
		if cancelled:
			raise IOError("cancelled at user request")
		if fsize > 0:
			percent = (100.0 * barrived * bsize) / fsize
			prog = '%.0f%% of %d bytes' % (percent, fsize)
		else:
			prog = '%.0f Kbytes received' % ((barrived * bsize) / 1024,)
		task.updateStatus(prog)
	import urllib
	params = urllib.urlencode(params)
	try:
		if post:
			tf, headers = urllib.urlretrieve("https://%s/%s" % (site, url),
				data=params, reporthook=reportCB)
		else:
			tf, headers = urllib.urlretrieve("https://%s/%s?%s"
				% (site, url, params), reporthook=reportCB)
	except (IOError, UnicodeError), v:
		replyobj.status("")
		raise NonChimeraError("Error during PDB fetch: " + str(v))
	finally:
		task.finished()
	task = None

	replyobj.status('Done fetching %s; verifying...' % statusName)
	fetched = open(tf, "r")
	numLines = 0
	for l in fetched:
		numLines += 1
		if numLines >= 20:
			break
	else:
		# too short; not a PDB file
		fetched.close()
		os.unlink(tf)
		replyobj.status("")
		raise UserError, "No such ID: %s" % statusName
	fetched.close()
	if saveName:
		import fetch
		spath = fetch.save_fetched_file(tf, saveDir, saveName)
		if spath:
			tf = spath
	replyobj.status("Opening %s..." % statusName, blankAfter=0)
	return tf

#
# export fileInfo
#

def _openPDBIDModel(IDcode, explodeNMR=True, identifyAs=None, guiErrors=True,
		ignore_cache=False, allow_mmcif=True):
	"""Locate a PDB ID code, read it, and add it to the list of open models.

	_openPDBIDModel(IDcode) => [model(s)]

	'explodeNMR' controls whether multi-MODEL files are split into
	multiple Molecules (if False, use coord sets instead)

	'guiErrors' controls whether PDB errors will be shown in a dialog
	in GUI mode.  Otherwise they will be on stderr.

	'allow_mmcif' controls whether to check for mmcif file if pdb format
	file is not found.
	"""
	if not identifyAs:
		identifyAs = IDcode

	import replyobj
	statusName = identifyAs or IDcode

	# try local system PDB directory
	IDcode = IDcode.lower()
	fileName = personalPDBFile(IDcode, ignore_cache=ignore_cache)
	if fileName is not None:
		replyobj.status("Opening %s..." % statusName, blankAfter=0)

	import preferences
	from initprefs import PREF_PDB, PREF_PDB_FETCH
	if fileName == None and preferences.get(PREF_PDB, PREF_PDB_FETCH):
		# not found locally; try web if allowed
		try:
			fetchFile = _pdbFetch('files.rcsb.org', 'download/%s.pdb'
					      % IDcode.upper(), {}, statusName,
					      'PDB', '%s.pdb' % IDcode.upper(),
					      ignore_cache=ignore_cache)
		except:
			if allow_mmcif:
				return _openCIFIDModel(IDcode, identifyAs=identifyAs,
                                                       ignore_cache=ignore_cache)
			raise
		else:
			fileName = fetchFile
	else:
		fetchFile = None

	if fileName == None:
                if allow_mmcif:
                        return _openCIFIDModel(IDcode, identifyAs=identifyAs,
                                               ignore_cache=ignore_cache)
		raise ValueError, (2, 'No such PDB ID: %s' % IDcode)
	import cStringIO
	errLog = cStringIO.StringIO()
	pdbio = PDBio()
	pdbio.explodeNMR = explodeNMR
	molList = pdbio.readPDBfile(fileName, errOut=errLog)
	if not pdbio.ok():
		replyobj.status("")
		raise UserError("Error reading PDB file: %s" % pdbio.error())
	err = errLog.getvalue()
	if err:
		replyobj.handlePdbErrs(identifyAs, err)
	for m in molList:
		m.name = identifyAs
	if not molList and not ignore_cache:
		return _openPDBIDModel(IDcode, explodeNMR, identifyAs, guiErrors, True, allow_mmcif)
	global _openedInfo, _isPdbID
	_openedInfo = "Opened %s" % statusName
	_isPdbID = True
	return molList

def _openCIFIDModel(IDcode, identifyAs=None, ignore_cache=False):
	"""Locate a CIF ID code, read it, and add it to the list of open models.

	_openCIFIDModel(IDcode) => [model(s)]

	'explodeNMR' controls whether multi-MODEL files are split into
	multiple Molecules (if False, use coord sets instead)
	"""
	if not identifyAs:
		identifyAs = IDcode

	import replyobj
	statusName = identifyAs or IDcode
	fileName = None

	import preferences
	from initprefs import PREF_PDB, PREF_PDB_FETCH
	if fileName == None and preferences.get(PREF_PDB, PREF_PDB_FETCH):
		# not found locally; try web if allowed
		fetchFile = _pdbFetch('files.rcsb.org', 'download/%s.cif'
			% IDcode.upper(), {}, statusName,
			'PDB', '%s.cif' % IDcode.upper(), ignore_cache=ignore_cache)
		fileName = fetchFile
	else:
		fetchFile = None

	if fileName == None:
		raise ValueError, (2, 'No such CIF ID: %s' % IDcode)

	from os import stat
	try:
		size = stat(fileName).st_size
	except:
		pass
	else:
		if size > 3e6:
			replyobj.status('Opening mmCIF %s, file size %d, this may take minutes.'
					% (IDcode, size))

	import mmCIF
	molList = mmCIF.open_mmcif(fileName)
	for m in molList:
		m.name = identifyAs
	global _openedInfo
	_openedInfo = "Opened %s" % statusName
	return molList

def _openCATHModel(cathID, explodeNMR=True, identifyAs=None, ignore_cache=False):
	"""Locate a CATH PDB file, read it, and add it to open models.

	_openCATHModel(cathID) => [model(s)]

	'explodeNMR' controls whether multi-MODEL files are split into
	multiple Molecules (if False, use coord sets instead)
	"""
	if not identifyAs:
		identifyAs = cathID

	import replyobj
	statusName = identifyAs or cathID

	fetchFile = _pdbFetch('data.cathdb.info', 'latest_release/pdb/' + cathID,
		{}, statusName, 'CATH', '%s.pdb' % cathID, ignore_cache=ignore_cache)

	pdbio = PDBio()
	pdbio.explodeNMR = explodeNMR
	molList = pdbio.readPDBfile(fetchFile)
	if not pdbio.ok():
		replyobj.status("")
		raise IOError(errno.EIO, pdbio.error(), identifyAs)
	for m in molList:
		m.name = identifyAs
	global _openedInfo
	_openedInfo = "Opened %s" % statusName
	return molList

def _openSCOPModel(scopID, explodeNMR=True, identifyAs=None, ignore_cache=False):
	"""Locate a SCOP PDB file, read it, and add it to open models.

	_openSCOPModel(scopID) => [model(s)]

	'explodeNMR' controls whether multi-MODEL files are split into
	multiple Molecules (if False, use coord sets instead)
	"""
	if not identifyAs:
		identifyAs = scopID

	import replyobj
	statusName = identifyAs or scopID

	fetchFile = _pdbFetch('scop.berkeley.edu', 'astral/pdbstyle',
		{'id': scopID, 'output': 'pdb'}, statusName, 'SCOP',
		'%s.pdb' % scopID, ignore_cache=ignore_cache, post=False)

	pdbio = PDBio()
	pdbio.explodeNMR = explodeNMR
	molList = pdbio.readPDBfile(fetchFile)
	if not pdbio.ok():
		replyobj.status("")
		raise IOError(errno.EIO, pdbio.error(), identifyAs)
	for m in molList:
		m.name = identifyAs
	global _openedInfo
	_openedInfo = "Opened %s" % statusName
	return molList

def _openNDBModel(ndbID, explodeNMR=True, identifyAs=None, ignore_cache=False):
	"""Translate an NDB ID to a PDB ID and open that.

	_openNDBModel(ndbID) => [model(s)]

	'explodeNMR' controls whether multi-MODEL files are split into
	multiple Molecules (if False, use coord sets instead)
	"""
	if not identifyAs:
		identifyAs = ndbID

	import replyobj
	statusName = identifyAs or ndbID

	site = "ndbserver.rutgers.edu"
	replyobj.status('Translating NDB ID %s to PDB ID using web site %s' %
					(statusName, site), blankAfter=0)
	import urllib
	params = urllib.urlencode({
		'structure_id': ndbID,
		'return_type': "PDB"
	})
	try:
		f = urllib.urlopen(
			"http://%s/tools/servlet/idswap.servlets.IdSwap"
			% site, params)
	except IOError, v:
		replyobj.error('Failed to successfully translate %s: %s\n' %
							(statusName, str(v)))
		replyobj.status("")
		return []
	for l in f:
		if "PDB ID:" not in l:
			continue
		for i, c in enumerate(l):
			if c.isdigit():
				break
		else:
			replyobj.error('Could not identify PDB ID from'
				' translation server %s\n' % site)
			replyobj.status('')
			return []
		pdbID = l[i:i + 4]
		if len(pdbID) < 4 or not pdbID[1:].isalnum():
			replyobj.error('Could not identify PDB ID code from'
				' NDB translation server %s response:\n%s'
				% (site, l))
			replyobj.status('')
			return []
		break
	else:
		replyobj.error('Unknown reply from'
					' translation server %s\n' % site)
		replyobj.status('')
		return []
	replyobj.info('NDB code %s corresponds to PDB code %s\n'
							% (ndbID, pdbID))
	return _openPDBIDModel(pdbID, explodeNMR=explodeNMR,
				identifyAs=identifyAs, ignore_cache=ignore_cache)

# despite the leading _, SimpleSession and pdb2pqr use this function
def _openPDBModel(filename, explodeNMR=True, fromSession=False,
			identifyAs=None, noprefs=False, guiErrors=True, ignore_cache=False):
	"""Read in a PDB file and add it list of open models.

	_openPDBModel(filename) => [model(s)]

	'explodeNMR' controls whether multi-MODEL files are split into
	multiple Molecules (if False, use coord sets instead)

	'guiErrors' controls whether PDB errors will be shown in a dialog
	in GUI mode.  Otherwise they will be on stderr.
	"""
	if isinstance(filename, basestring):
		if not identifyAs:
			identifyAs = os.path.split(filename)[-1]

		try:
			file = findfile(filename)
		except IOError:
			file = None

		if file == None:
			file = personalPDBFile(filename, ignore_cache=ignore_cache)

		if file == None and len(filename) == 4:
			return _openPDBIDModel(filename)

		if file == None:
			raise IOError(errno.ENOENT, os.strerror(errno.ENOENT),
								filename)
	else:
		file = filename
		filename = identifyAs
	import replyobj
	statusName = identifyAs or filename
	replyobj.status("Opening %s..." % statusName, blankAfter=0)
	if fromSession:
		pdbio = SessionPDBio()
	else:
		pdbio = PDBio()
	pdbio.explodeNMR = explodeNMR
	import cStringIO
	errLog = cStringIO.StringIO()
	from OpenSave import isUncompressedFile
	if isUncompressedFile(file):
		# Passing file name to C++ reduces reading 300,000 line PDB
		# file to 0.5 seconds versus 3.5 seconds when passing a
		# wrapped Python file object.  This is more than half
		# the total parsing and Molecule creation time.
		if fromSession:
			molList, sessionIDs = pdbio.readSessionPDBfile(file)
		else:
			molList = pdbio.readPDBfile(file, errOut=errLog)
	else:
		from OpenSave import osOpen
		f = osOpen(file)
		if fromSession:
			molList, lineNum, sessionIDs = \
			    pdbio.readSessionPDBstream(f, filename, 0)
		else:
			molList, lineNum = pdbio.readPDBstream(f, filename, 0,
							       errOut=errLog)
		f.close()
	if not pdbio.ok():
		replyobj.status("")
		raise UserError(pdbio.error())
	err = errLog.getvalue()
	if err:
		replyobj.handlePdbErrs(identifyAs, err)
	for m in molList:
		m.name = identifyAs
	if not molList and _isPdbID and not ignore_cache:
		return _openPDBModel(filename, explodeNMR, fromSession,
			identifyAs, noprefs, guiErrors, ignore_cache=True)
	if molList and fromSession:
		molList[0].sessionIDs = sessionIDs
	global _openedInfo
	_openedInfo = "Opened %s" % statusName
	return molList

def personalPDBFile(filename, ignore_cache=False):

	# try personal PDB dirs, system PDB dir and fetch pdb dir
	filenames = [filename, filename + '.pdb']
	from os.path import join
	if len(filename) == 4:
		id = filename.lower()
		filenames.append(join(id[1:3], 'pdb%s.ent' % id))
		filenames.append('pdb%s.ent' % id)
		filenames.append(id.upper() + '.pdb')

	dir = systemPDBdir()
	pdbDirs = [dir] if dir else []

	import preferences
	from initprefs import PREF_PDB, PREF_PDB_DIRS
	pdbDirs.extend(preferences.get(PREF_PDB, PREF_PDB_DIRS))
	import fetch
	if preferences.get(fetch.FETCH_PREFERENCES, fetch.FETCH_LOCAL) \
	and not ignore_cache:
		dir = preferences.get(fetch.FETCH_PREFERENCES,
				      fetch.FETCH_DIRECTORY)
		if dir:
			pdbDirs.append(join(dir, 'PDB'))

	for pdbDir in pdbDirs:
		for fname in filenames:
			pdbPath = join(pdbDir, fname)
			upath = uncompressedPath(pdbPath)
			if upath:
				global _isPdbID
				_isPdbID = True
				return upath
	return None

def uncompressedPath(path):
	from os.path import exists
	if exists(path):
		return path
	from OpenSave import compressSuffixes, osUncompressedPath
	for cs in compressSuffixes:
		if exists(path + cs):
			return osUncompressedPath(path + cs)
	return None

def _openVRMLModel(filename, identifyAs=None):
	"""Filename contains a VRML 2.0 file.

	_openVRMLModel(filename) => [model]
	"""
	if isinstance(filename, basestring) and filename[0:5] == "#VRML":
		import cStringIO
		f = cStringIO.StringIO(filename)
		filename = "<<VRML string>>"
	else:
		from OpenSave import osOpen
		f = osOpen(filename)
	import replyobj
	statusName = identifyAs or filename
	replyobj.status("Opening VRML model in %s..."
			% statusName, blankAfter=0)
	vrml = VRMLModel(f, filename)
	f.close()
	if not vrml.valid():
		replyobj.status("")
		if vrml.error():
			error = vrml.error()
		else:
			error = "unknown VRML error"
		raise IOError(errno.EIO, error, statusName)
	vrml.name = statusName
	global _openedInfo
	_openedInfo = "Opened VRML model in %s" % statusName
	return [vrml]

defaultMol2ioHelper = PyMol2ioHelper()

def _openMol2Model(filename, helper=None, identifyAs=None):
	"""Filename contains a Mol2 file.

	_openMol2Model(filename) => [model]
	"""

	if isinstance(filename, basestring):
		file = findfile(filename)
	else:
		file = filename
		filename = identifyAs
	import replyobj
	statusName = identifyAs or filename
	replyobj.status("Opening %s..." % statusName, blankAfter=0)
	if helper == None:
		helper = defaultMol2ioHelper
	mol2io = Mol2io(helper)
	from OpenSave import osOpen
	f = osOpen(file)
	molList = mol2io.readMol2stream(f, filename, 0)
	f.close()
	if not mol2io.ok():
		replyobj.status("")
		raise IOError(errno.EIO, mol2io.error(), filename)
	from initprefs import MOLECULE_DEFAULT, MOL_MOL2_NAME, Mol2NameOption
	import preferences
	nameSource = preferences.get(MOLECULE_DEFAULT, MOL_MOL2_NAME)
	for m in molList:
		if len(m.residues) == 0:
			replyobj.status("")
			raise SyntaxError("%s is missing residue section (@<TRIPOS>SUBSTRUCTURE section)"
				% (filename,))
		if nameSource == Mol2NameOption.FILE_NAME:
			name = os.path.split(filename)[-1]
		elif nameSource == Mol2NameOption.MOL_NAME:
			name = m.mol2name
		elif nameSource == Mol2NameOption.MOL_COMMENT:
			name = m.mol2comment
		from misc import isInformativeName
		if not isInformativeName(name):
			if not identifyAs:
				identifyAs = os.path.split(filename)[-1]
			name = identifyAs
		m.name = name
	from SimpleSession import registerAttribute
	registerAttribute(Molecule, "mol2name")
	registerAttribute(Molecule, "mol2type")
	registerAttribute(Molecule, "chargeModel")
	registerAttribute(Molecule, "mol2comment")
	registerAttribute(Bond, "mol2type")
	registerAttribute(Atom, "mol2type")
	global _openedInfo
	_openedInfo = "Opened %s" % statusName
	return molList

def _openPython(filename, identifyAs=None):
	"""Filename contains a Python script.

	_openPython(filename) => []
	"""
	file = findfile(filename)
	# use sandbox module's namespace to avoid contamination
	sandboxName = 'chimeraOpenSandbox'
	while sandboxName in sys.modules:
		# must be a recursive call sequence...
		sandboxName = "_" + sandboxName
	import replyobj
	statusName = identifyAs or filename
	from SimpleSession import END_RESTORE_SESSION
	def cb(a1, a2, a3, fileName=file):
		setLastSession(fileName)
	handler = triggers.addHandler(END_RESTORE_SESSION, cb, None)

	from OpenSave import osUncompressedPath
	ucPath = osUncompressedPath(file)
	import imp
	flags = 'rU'
	if ucPath.lower().endswith('.py'):
		loadFunc = imp.load_source
		if not os.path.exists(ucPath + 'c') \
		and not os.path.exists(ucPath + 'o'):
			# try to pre-compile
			replyobj.status("Compiling %s..." % statusName)
			# use repr() trick to double backslashes
			command = [ sys.executable, "-m", "py_compile", ucPath ]
			try:
				import subprocess
				if subprocess.call(command) < 0:
					raise RuntimeError
			except:
				replyobj.status("Compiling %s failed"
								% statusName)
			else:
				replyobj.status("Compiling %s succeeded"
								% statusName)
	elif ucPath.lower().endswith('.pyc') or ucPath.lower().endswith('.pyo'):
		loadFunc = imp.load_compiled
		flags = 'rb'
	else:
		loadFunc = imp.load_source
	replyobj.status("Executing %s..." % statusName)
	dirName, fileName = os.path.split(ucPath)
	cwd = os.getcwd()
	try:
		try:
			# We append '.' to the end of the path to make sure
			# that session files (also with suffix .py) will
			# always get Chimera modules before user modules.
			# It's a bad idea for users to use the same name as
			# a Chimera module anyway.
			sys.path.append('.')
			if dirName:
				os.chdir(dirName)
			f = open(fileName, flags)
			loadFunc(sandboxName, fileName, f)
			f.close()
		except ImportError, v:
			if unicode(v).startswith("Bad magic number"):
				raise UserError(".pyc files are not portable;"
					" please use .py file instead")
			raise
		except:
			raise
		finally:
			os.chdir(cwd)
			sys.path.reverse()
			sys.path.remove('.')
			sys.path.reverse()
			triggers.deleteHandler(END_RESTORE_SESSION, handler)
			if sandboxName in sys.modules:
				# Freeing module sets all globals to None.
				# Prevent that since code may have registered
				# callbacks that need those globals.
				d = sys.modules[sandboxName].__dict__
				dc = d.copy()
				del sys.modules[sandboxName]
				d.update(dc)
			if file != ucPath and ucPath.endswith(".py"):
				# remove the .pyc we compiled
				pyc = ucPath + 'c'
				if os.path.exists(pyc):
					os.unlink(pyc)

	except CancelOperation, v:
		replyobj.status("Cancelled %s" % statusName)
		return []
	except ChimeraSystemExit, v:
		triggers.activateTrigger(APPQUIT, None)
		raise ChimeraSystemExit, v
	except:
		replyobj.status("")
		raise
	replyobj.status("Executed %s" % statusName)
	return []

def _openGaussianFCF(filename, identifyAs=None):
	"""Filename contains a Gaussian formatted checkpoint file

	_openGaussianFCF(filename) => [model(s)]
	"""
	if isinstance(filename, basestring):
		if not identifyAs:
			identifyAs = os.path.split(filename)[-1]
		file = findfile(filename)
	else:
		file = filename
		filename = identifyAs
	import replyobj
	statusName = identifyAs or filename
	replyobj.status("Opening %s..." % statusName, blankAfter=0)
	from OpenSave import osOpen
	fcf = ReadGaussianFCF()
	f = osOpen(file)
	molList, lineNum = fcf.readGaussianStream(f, filename, 0)
	f.close()
	if not fcf.ok():
		replyobj.status("")
		raise IOError(errno.EIO, fcf.error(), filename)
	for m in molList:
		m.name = identifyAs
	if molList and molList[0].atoms \
	and hasattr(molList[0].atoms[0], "mullikenCharge"):
		from SimpleSession import registerAttribute
		registerAttribute(Atom, "mullikenCharge")
		registerAttribute(Molecule, "chargeModel")
	global _openedInfo
	_openedInfo = "Opened %s" % statusName
	return molList

import collections

FileTypeData = collections.namedtuple('FileTypeData', (
	'open_func',		# python function that opens files:
				#	prototype(filename, identifyAs=None)
	'extensions',		# sequence of filename extensions in lowercase
				#	starting with period (or empty)
	'prefixes',		# sequence of URL-style prefixes (or empty)
	'mime_types',		# sequence of associated MIME types (or empty)
	'canDecompress',	# True if open function handles compressed files
	'dangerous',		# True if can execute arbitrary code (scripts)
	'category',		# data category
	'batch',		# True if filename argument to open_func
				#	is a sequence of filenames
	'web_type',		# type name to display when web fetched
				# if different from type name
))

class FileInfo(object):
	"""Manage information about file types that can be opened"""
	# some known categories
	DYNAMICS = "Molecular trajectory"
	GENERIC3D = "Generic 3D objects"
	SCRIPT = "Command script"
	SEQUENCE = "Sequence alignment"
	STRUCTURE = "Molecular structure"
	SURFACE = "Molecular surface"
	VOLUME = "Volume data"

	_open = {
		"PDB": FileTypeData(
			_openPDBModel, (".pdb", ".pdb1", ".ent", ".pqr"), ("pdb",),
			("chemical/x-pdb", "chemical/x-spdbv"), True, False,
			STRUCTURE, False, None
		),
		"PDBID": FileTypeData(
			_openPDBIDModel, (), ("pdbID",), (), False, False,
			STRUCTURE, False, "PDB"
		),
		"CIFID": FileTypeData(
			_openCIFIDModel, (), ("cifID",), (), False, False,
			STRUCTURE, False, "mmCIF"
		),
		"VRML": FileTypeData(
			_openVRMLModel, (".wrl", ".vrml"), ("vrml",),
			("model/vrml",), True, False, GENERIC3D, False, None
		),
		#"X3D": FileTypeData(
		#	_openX3DModel, (".x3d",), ("x3d",), ("model/x3d+xml",),
		#	True, False,
		#	GENERIC3D, False, None
		#),
		"Mol2": FileTypeData(
			_openMol2Model, (".mol2",), ("mol2",),
			("chemical/x-mol2",), True, False,
			STRUCTURE, False, None
		),
		"Python": FileTypeData(_openPython,
			(".py", ".pyc", ".pyo", ".pyw"),
			("python", "py", "chimera"),
			("application/x-chimera",), True, True,
			SCRIPT, False, None
		),
		"Gaussian formatted checkpoint": FileTypeData(
			_openGaussianFCF, (".fchk",), ("fchk", "gaussian"),
			("chemical/x-gaussian-checkpoint",), True, False,
			STRUCTURE, False, None
		),
		# CATH updated their web site and haven't yet reimplemented
		# web fetching
		#"CATH": FileTypeData(
		#	_openCATHModel, (), ("cath",), (), False, False,
		#	STRUCTURE, False, None
		#),
		"SCOP": FileTypeData(
			_openSCOPModel, (), ("scop",), (), False, False,
			STRUCTURE, False, None
		),
		"NDB": FileTypeData(
			_openNDBModel, (), ("ndb",), (), False, False,
			STRUCTURE, False, None
		),
	}

	_alias = {}

	triggers = triggerSet.TriggerSet()
	NEWFILETYPE = "new file type"
	triggers.addTrigger(NEWFILETYPE)

	def register(self, type_, function, extensions, prefixes, mime=(),
			canDecompress=True, dangerous=None,
			category="Miscellaneous", batch=False, webType=None):
		"""Register open function for given model type

		register(type, function, extensions, prefixes) -> None

		extensions is a sequence of filename suffixes starting
		with a period.  If the type doesn't open from a filename
		(e.g. PDB ID code), then extensions should be an empty
		sequence.

		prefixes is a sequence of filename prefixes (no ':'), possibily empty.

		mime is a sequence of mime types, possibly empty.
.
		If the type doesn't want to be given compressed files of its
		type, 'canDecompress' should be False.  [The OpenSave module
		has functions to assist in the handling of compressed files.]

		dangerous should be True for scripts and other formats that
		can write/delete a users's files.

		category says what kind of data the should be classified as.

		If batch is True then the open function requires a list of
		paths.  If the user selects multiple paths they are all passed
		to the open function in one call instead of a separate call
		for each path.
		"""
		if dangerous is None:
			# scripts are inherently dangerous
			dangerous = category == self.SCRIPT
		if extensions is not None:
			exts = map(lambda s: s.lower(), extensions)
		else:
			exts = ()
		if prefixes is None:
			prefixes = ()
		if mime is None:
			mime = ()
		self._open[type_] = FileTypeData(
				function, exts, prefixes, mime,
				canDecompress, dangerous, category, batch, webType)
		self.triggers.activateTrigger(self.NEWFILETYPE, type_)

	def registerAlias(self, type_, alias):
		self._alias[alias] = type_

	def prefixes(self, type):
		"""Return filename prefixes for given model type.

		prefixes(type) -> [filename-prefix(es)]
		"""
		try:
			return self._open[type].prefixes
		except KeyError:
			return ()

	def extensions(self, type):
		"""Return filename extensions for given model type.

		extensions(type) -> [filename-extension(s)]
		"""
		try:
			exts = self._open[type].extensions
		except KeyError:
			return ()
		return exts

	def openCallback(self, type):
		"""Return open callback for given model type.

		openCallback(type) -> [callback]
		"""
		while type in self._alias:
			type = self._alias[type]
		try:
			return self._open[type].open_func
		except KeyError:
			return None

	def mimeType(self, type):
		"""Return mime type for given model type."""
		try:
			return self._open[type].mime_types
		except KeyError:
			return None

	def canDecompress(self, type):
		"""Return whether this type can open compressed files"""
		try:
			return self._open[type].canDecompress
		except KeyError:
			return False

	def dangerous(self, type):
		"""Return whether this type can write to files"""
		try:
			return self._open[type].dangerous
		except KeyError:
			return False

	def category(self, type):
		"""Return category of this type"""
		try:
			return self._open[type].category
		except KeyError:
			return "Unknown"

	def batch(self, type):
		"""Return whether open function expects list of file names"""
		try:
			return self._open[type].batch
		except KeyError:
			return False

	def types(self, sourceIsFile=False):
		"""Return known model types.

		types() -> [model-type(s)]
		"""
		if sourceIsFile:
			types = []
			for typeName, typeInfo in self._open.items():
				if typeInfo[1]:
					types.append(typeName)
			return types
		return self._open.keys()

	def webType(self, type):
		try:
			return self._open[type].web_type or type
		except KeyError:
			return type

	def categorizedTypes(self):
		"""Return know model types by category

		categorizedTypes() -> { category: model-types() }
		"""
		result = {}
		for t in self._open.keys():
			category = self.category(t)
			list = result.setdefault(category, [])
			list.append(t)
		return result

	def processName(self, filename, defaultType=None, prefixableType=True):
		type = None
		prefixed = False
		if prefixableType:
			# type may be specified as colon-separated prefix
			try:
				prefix, fname = filename.split(':', 1)
			except ValueError:
				pass
			else:
				for t in fileInfo.types():
					if prefix in fileInfo.prefixes(t):
						type = t
						filename = fname
						prefixed = True
						break
		from OpenSave import compressSuffixes
		if type == None:
			for cs in compressSuffixes:
				if filename.endswith(cs):
					stripped, ext = os.path.splitext(
								filename)
					break
			else:
				stripped = filename
			base, ext = os.path.splitext(stripped)
			ext = ext.lower()
			for t in fileInfo.types():
				if ext in fileInfo.extensions(t):
					type = t
					break
			if type == None:
				type = defaultType
		return type, prefixed, filename

fileInfo = FileInfo()

#
# export openModels -- a instance that contains all open models
#	The key is a tuple (model id #, model subid #) and the value
#	is a list of models with that key.
#

# class OpenModel: from _chimera
OpenModels.ADDMODEL = 'addModel'
OpenModels.REMOVEMODEL = 'removeModel'
OpenModels.triggers = triggerSet.TriggerSet()
OpenModels.triggers.addTrigger(OpenModels.ADDMODEL)
OpenModels.triggers.addTrigger(OpenModels.REMOVEMODEL)

def addAddHandler(self, func, data):
	"""Add trigger handler for adding models"""
	return self.triggers.addHandler(self.ADDMODEL, func, data)
OpenModels.addAddHandler = addAddHandler
del addAddHandler

def deleteAddHandler(self, handler):
	"""Delete trigger handler for adding models"""
	self.triggers.deleteHandler(self.ADDMODEL, handler)
OpenModels.deleteAddHandler = deleteAddHandler
del deleteAddHandler

def addRemoveHandler(self, func, data):
	"""Add trigger handler for removing models"""
	return self.triggers.addHandler(self.REMOVEMODEL, func, data)
OpenModels.addRemoveHandler = addRemoveHandler
del addRemoveHandler

def deleteRemoveHandler(self, handler):
	"""Delete trigger handler for removing models"""
	self.triggers.deleteHandler(self.REMOVEMODEL, handler)
OpenModels.deleteRemoveHandler = deleteRemoveHandler
del deleteRemoveHandler

def addModelClosedCallback(model, callback):
	"""Invoke a callback when a specified model is closed.
	The callback is only called when the given model is closed.
	The callback is automattically removed after it is called.
	The callback is passed one argument, the closed model.
	"""
	def cb(trigger_name, args, closed_models):
		model, callback, trigger = args
		if model in closed_models:
			callback(model)
			import chimera
			chimera.openModels.deleteRemoveHandler(trigger)
			args[2] = None    # Break circular link to trigger

	args = [model, callback, None]
	import chimera
	trigger = chimera.openModels.addRemoveHandler(cb, args)
	args[2] = trigger

def add(self, models, baseId=OpenModels.Default, subid=OpenModels.Default,
		sameAs=None, shareXform=True, hidden=False,
		checkForChanges=False, noprefs=False, fromSession=False,
		keepLongBonds=False):
	#
	# Note: this function is called from the _chimera C++ code,
	# do not change its name, or how it is accessed without also
	# changing _chimera.
	#
	"""Add models to the list of open models.

	add(models, sameAs=None, hidden=False) => None

	baseId is the base model id to start numbering models with.

	sameAs is an existing model that all of the new models should
	share the same id and subid.
	
	If shareXform is true, then initialize the model's transformation
	matrix to be the same as the lowest positively numbered model 
	(if not baseId specified) or the lowest numbered model with the
	same baseId.  (Using sameAs overrides shareXform).
	
	If hidden is true, that means that the given models do not
	normally appear when listed.
	"""
	tm0 = TimeIt('chimera.add() %d %s' %
		     (len(models), ', '.join(tuple((m.name or getattr(m, 'category', '')) for m in models))))
	if noprefs:
		for m in models:
			m.noprefs = True
	# force Python object creation before checkForChanges
	makePythonAtomsBondsResidues(models)
	molecules = [m for m in models if isinstance(m, Molecule)]
	if not fromSession:
		_postCategorizeModels.extend(molecules)
	tm1 = TimeIt('OpenModels.add()')
	self._add(models, baseId, subid, sameAs, shareXform, hidden)
	tm1.done()
	for m in models:
		viewer.addModel(m)
	# TODO: eliminate need to update cached ref counts
	for id in self.listIds(hidden=hidden):
		os = self.openState(*id)
		if hidden:
			os.hidden
		else:
			os.models
	# possibly update display name of metal complex groups
	if not fromSession:
		for m in molecules:
			m.metalComplexGroup(create=False)
	self.triggers.activateTrigger(self.ADDMODEL, models)
	if checkForChanges:
		import update
		update.checkForChanges()
	if not fromSession:
		realMolecules = [ m for m in molecules
					if getattr(m, "isRealMolecule", True) ]
		if realMolecules:
			makePseudoBondsToMetals(realMolecules)
			if not keepLongBonds:
				makeLongBondsDashed(realMolecules)
	tm0.done()

OpenModels._add = OpenModels.add
OpenModels.add = add
del add

def remove(self, models, destroying=False):
	"""Remove models from the list of open models.

	remove(models) => None
	"""
	if isModel(models):
		models = [models]
	for m in models:
		viewer.removeModel(m)
	removedModels = self._remove(models)
	# TODO: eliminate need to update cached ref counts
	for id in self.listIds(all=True):
		os = self.openState(*id)
		os.hidden
		os.models
	if removedModels:
		if not destroying:
			from selection import removeCurrent
			removeCurrent(removedModels)
		self.triggers.activateTrigger(
					self.REMOVEMODEL, removedModels)
	return removedModels
OpenModels._remove = OpenModels.remove
OpenModels.remove = remove
del remove

def list(self, id=OpenModels.Default, subid=OpenModels.Default, modelTypes=[], hidden=False, all=False):
	"""List models from the list of open models.

	list(id = None, hidden=False, all=False, modelTypes=[]) => [models]

	id is a model identifier (an integer).  If hidden is true,
	then the hidden models are returned.  If all is true, then
	both hidden and non-hidden models are returned.  modelTypes
	is a list of model types (see the global list modelTypes)
	that restricts the types of the models returned.
	"""
	models = self._list(id, subid, hidden, all)
	if modelTypes and isinstance(modelTypes, (list, tuple, set)):
		mtypes = tuple(modelTypes)
		models = [m for m in models if isinstance(m, mtypes)]
	return models
OpenModels._list = OpenModels.list
OpenModels.list = list
del list

raFetchedType = None # use by Rapid Access to give better identification
# of fetched data types
_isPdbID = False # used to communicate that PDB defaulted back to PDBID
def open(self, filename, type=None, baseId=OpenModels.Default,
		subid=OpenModels.Default, sameAs=None, shareXform=True,
		hidden=False, defaultType=None, prefixableType=False,
		checkForChanges=True, noprefs=False, temporary=False,
		ignore_cache=False, *args, **kw):
	"""Read in a file and add the models within.

	open(filename, type=None, [add arguments,] *args, **kw) -> [model(s)]

	If the type is given, then then open handler for that type is
	used.  Otherwise the filename suffix is examined to determine
	which open function to call.  See the add documentation above.

	The filename is a list of paths if the file type is specified and
	registered with a batch file reader, i.e. fileInfo.batch(type) = True.
	If the file type is not given then the filename must be a string.
	"""
	tm0 = TimeIt('chimera.open(%s)' % filename)
	if defaultType and defaultType not in fileInfo.types():
		raise ValueError, "unknown default type"
	if isinstance(filename, basestring):
		openedAs = (filename, type, defaultType, prefixableType)
	else:
		openedAs = None
	if type == None:
		type, prefixed, filename = fileInfo.processName(filename,
			defaultType=defaultType, prefixableType=prefixableType)
	else:
		prefixed = False
	if type == None and not nogui:
		from Pmw import SelectionDialog
		from tkgui import app
		def cb(but):
			val = None
			if but != 'Cancel':
				sels = sd.getcurselection()
				if sels:
					val = sels[0]
			sd.deactivate(val)
		typeList = fileInfo.types()
		typeList.sort(lambda a, b: cmp(a.lower(), b.lower()))
		sd = SelectionDialog(app, defaultbutton='OK',
			buttons=('OK', 'Cancel'), command=cb,
			title="Type Selection", scrolledlist_labelpos='n',
			label_text="Please designate file type for\n%s"
							% (filename),
			scrolledlist_items=typeList)
		type = sd.activate()
		sd.destroy()
		if type is None:
			return []

	if type and not fileInfo.canDecompress(type):
		from OpenSave import compressSuffixes
		for cs in compressSuffixes:
			if fileInfo.batch(type):
				needDecompress = [f for f in filename
						  if f.endswith(cs)]
			else:
				needDecompress = filename.endswith(cs)
			if needDecompress:
				raise UserError(
		"Compressed %s files are not handled automatically.\n"
		"You need to decompress such files manually before using them."
		% type)
	func = fileInfo.openCallback(type)
	if not func:
		raise ValueError, "Unknown model type"

	# stop any ongoing spinning if no non-pseudobond groups are open
	if not nogui:
		doStopSpinning = True
		for m in openModels.list():
			if not isinstance(m, PseudoBondGroup):
				doStopSpinning = False
				break
		if doStopSpinning and not nogui:
			import tkgui
			tkgui.stopSpinning()

	# funcs can stash status info they want shown after the redraw here
	global _openedInfo, _isPdbID
	_openedInfo = None
	_isPdbID = False

	# remove 'identifyAs' keyword if the function doesn't expect it...
	import inspect
	allArgs, v1, v2, defaults = inspect.getargspec(func)
	if defaults is None:
		defaults = ()
	kwArgNames = allArgs[len(allArgs) - len(defaults):]
	if 'identifyAs' in kw:
		import inspect
		allArgs, v1, v2, defaults = inspect.getargspec(func)
		if defaults is None:
			defaults = ()
		if 'identifyAs' not in kwArgNames:
			del kw['identifyAs']
	elif not isinstance(filename, basestring):
		# streams must supply identifyAs if possible
		if 'identifyAs' in kwArgNames:
			raise ValueError("'identifyAs' keyword must be provided"
						" when opening streams")
	if 'ignore_cache' in kwArgNames:
		kw['ignore_cache'] = ignore_cache
	tm1 = TimeIt('open func')
	models = func(filename, *args, **kw)
	tm1.done()

	tm2 = TimeIt('add model')
	if models:
		# do the self.add first so that the model number
		# is correct when we ask for it, but block the
		# ADDMODEL trigger so we can clean up the metal
		# complexes before callbacks occur
		self.triggers.blockTrigger(self.ADDMODEL)
		self.add(models, baseId=baseId, subid=subid, sameAs=sameAs,
				shareXform=shareXform, hidden=hidden,
				checkForChanges=False, noprefs=noprefs)
		if openedAs:
			for model in models:
				model.openedAs = openedAs
		_addMODRES([m for m in models if isinstance(m, Molecule)])
		tm4 = TimeIt('check for changes block')
		if checkForChanges:
			import update
			tm5 = TimeIt('update.checkForChanges()')
			update.checkForChanges()
			tm5.done()
			# since model panel only updates off
			# 'Model' trigger, only do the below
			# if changes have been checked
			#
			# avoid grouping sphgen clusters by check isRealMolecule
			if len([m for m in models if getattr(m, 'isRealMolecule', True)]) > 1:
				# possibly group in Model Panel
				grpName = None
				names = set([m.name for m in models])
				if len(names) > 1:
					if isinstance(filename, basestring):
						fname = os.path.split(filename)[-1]
						from tempfile import gettempprefix
						if not fname.startswith(gettempprefix()):
							grpName = fname
				else:
					grpName = names.pop()
				if grpName is not None:
					from ModelPanel import groupCmd
					groupCmd(models, name=grpName)
		self.triggers.releaseTrigger(self.ADDMODEL)
		tm4.done()

		numAtoms, numResidues = countAtomsAndResidues(models)
		if numAtoms > 0:
			if isinstance(filename, basestring):
				if os.path.exists(filename):
					from tempfile import gettempprefix
					fileLabel = os.path.split(filename)[-1]
					if fileLabel.startswith(gettempprefix()):
						fileLabel = "<temp file>"
				else:
					fileLabel = models[0].name
			else:
				fileLabel = "<stream>"
			_openedInfo = "Opened %s containing %d model" % (
							fileLabel, len(models))
			if len(models) > 1:
				_openedInfo += "s"
			_openedInfo += ", %d atoms, and %d residues" % (
							numAtoms, numResidues)
	tm2.done()

	# 'models' is empty for session files, so don't embed this in
	# the 'if models' test
	if ((isinstance(filename, basestring) or
             (isinstance(filename, (tuple, list)) and len(filename) == 1))
            and type and not hidden
			and not 'identifyAs' in kw) and not temporary:
		if prefixed:
			webType = type
		elif raFetchedType:
			webType = fileInfo.webType(raFetchedType)
		elif _isPdbID:
			webType = fileInfo.webType("PDBID")
			_isPdbID = False
		else:
			webType = None
                fname = filename if isinstance(filename, basestring) else filename[0]
		triggers.activateTrigger('file open', (fname, webType, type))
	if _openedInfo:
		def _postOpenedStatus(trigName, d1, d2, info=_openedInfo):
			replyobj.status(info)
			from triggerSet import ONESHOT
			return ONESHOT
		triggers.addHandler('post-frame', _postOpenedStatus, None)
	tm0.done()
	return models

OpenModels.open = open
del open

def makePseudoBondsToMetals(models):
	"""Replace normal bonds with pseudobonds for coordinated metals.

	makePseudoBondsToMetals(models) => numAtoms, deletedBonds
	"""
	tm0 = TimeIt('makePseudoBondsToMetals()')
	from elements import metals
	import preferences

	deletedBonds = []
	formedGroups = []
	for model in models:
		if not isinstance(model, Molecule):
			continue
		modelMetals = set(metalAtoms(model))
		for metal in modelMetals:
			# skip large inorganic residues (that typically
			# don't distinguish metals by name)
			if not metal.altLoc \
			and len(metal.residue.atomsMap[metal.name]) > 1:
				continue
			# bond -> pseudobond if:
			# 1) cross residue
			# 2) > 4 bonds
			# 3) neighbor is bonded to non-metal in same res
			#    unless metal has only one bond and the
			#    neighbor has no lone pairs (e.g. residue
			#    EMC in 1cjx)
			delBonds = set()
			for bonded, bond in metal.bondsMap.items():
				if bonded.residue != metal.residue:
					delBonds.add(bond)
			# eliminate cross-residue first to preserve FEO in 1av8
			if metal.numBonds - len(delBonds) > 4:
				delBonds = metal.bonds
			else:
				# metals with just one bond may be a legitimate
				# compound
				if metal.numBonds - len(delBonds) == 1:
					# avoid expensive atom-type computation
					# by skipping common elements we know
					# cannot have lone pairs...

					# find the remaining bond
					for bonded, bond in metal.bondsMap.items():
						if bond not in delBonds:
							break
					else:
						raise AssertionError("All metal bonds in delBonds")
					if bonded.element.name in ("C", "H"):
						if delBonds:
							formedGroups.append((metal, delBonds))
							deletedBonds.extend(delBonds)
						continue
					from idatm import typeInfo
					idatmType = bonded.idatmType
					if (idatmType in typeInfo and
					typeInfo[idatmType].substituents ==
					typeInfo[idatmType].geometry and
					idatmType not in  ["Npl", "N2+"]): # HEME C in 1og5
						if delBonds:
							formedGroups.append((metal, delBonds))
							deletedBonds.extend(delBonds)
						continue
				for bonded, bond in metal.bondsMap.items():
					if bonded in modelMetals:
						delBonds.add(bond)
						continue
					for bn in bonded.neighbors:
						if bn not in modelMetals and \
						bn.residue == bonded.residue:
							delBonds.add(bond)
							break
			if delBonds:
				# avoid repeated idatm computations by delaying
				# pseudobond group formation (and bond deletion)
				formedGroups.append((metal, delBonds))
				deletedBonds.extend(delBonds)

	for metal, delBonds in formedGroups:
		# atom.coordination() expects the pseudobond group
		# category to start with "coordination complex"
		mol = metal.molecule
		cmPBG = mol.metalComplexGroup(issueHint=True)
		from initprefs import MOL_COMPLEX_REPR, MOLECULE_DEFAULT
		depict = preferences.get(MOLECULE_DEFAULT, MOL_COMPLEX_REPR)
		for b in delBonds:
			if b.__destroyed__:
				continue
			a = b.otherAtom(metal)
			mol.deleteBond(b)
			pb = cmPBG.newPseudoBond(metal, a)
			if depict == "springs":
				pb.drawMode = Bond.Spring
	tm0.done()
	return deletedBonds

def _metalComplexSceneSave(trigName, myData, scene):
	mols = openModels.list(modelTypes=[Molecule])
	complexInfo = {}
	for mol in mols:
		pbg = mol.metalComplexGroup(create=False)
		if not pbg:
			continue
		from Animate.Tools import get_saveable_pb_info, sceneID
		complexInfo[sceneID(mol)] = get_saveable_pb_info(pbg)
	if not complexInfo:
		return
	scene.tool_settings["metal complexes"] = (1, complexInfo)
triggers.addHandler(SCENE_TOOL_SAVE, _metalComplexSceneSave, None)

def _metalComplexSceneRestore(trigName, myData, scene):
	restoreData = scene.tool_settings.get("metal complexes")
	if not restoreData:
		return
	version, complexInfo = restoreData
	from Animate.Tools import restore_pbs, idLookup
	for molID, info in complexInfo.items():
		mol = idLookup(molID)
		if not mol:
			continue
		pbg = mol.metalComplexGroup()
		restore_pbs(pbg, info)
triggers.addHandler(SCENE_TOOL_RESTORE, _metalComplexSceneRestore, None)

LONGBOND_PBG_NAME = "missing segments"
def makeLongBondsDashed(models):
	"""Hide long bonds and replace with dashed pseudobonds"""
	tm0 = TimeIt('makeLongBondsDashed()')
	lBonds = []
	for m in models:
		if isinstance(m, Molecule):
			lBonds.extend(longBonds(m))
	if lBonds:
		from misc import getPseudoBondGroup
		preexisting = PseudoBondMgr.mgr().findPseudoBondGroup(
							LONGBOND_PBG_NAME)
		_longBondPBG = getPseudoBondGroup(LONGBOND_PBG_NAME,
								issueHint=True)
		if not preexisting:
			_longBondPBG.lineType = Dash
			_longBondPBG.chainTraceMapping = {}
			triggers.addHandler("Atom", _longBondTraceCB,
								_longBondPBG)
			from SimpleSession import SAVE_SESSION
			triggers.addHandler(SAVE_SESSION, _chainTraceSessionCB,
								_longBondPBG)
		for lb in lBonds:
			lb.display = Bond.Never
			pb = _longBondPBG.newPseudoBond(*tuple(lb.atoms))
			pb.halfbond = True
			_longBondPBG.chainTraceMapping[pb] = None
	tm0.done()

def _longBondTraceCB(trigName, pbg, changes):
	if pbg.__destroyed__:
		from triggerSet import ONESHOT
		return ONESHOT
	ctMap = pbg.chainTraceMapping
	delPB = pbg.deletePseudoBond
	for normalPB, tracePB in pbg.chainTraceMapping.items():
		# first, fix things up
		if normalPB.__destroyed__:
			if tracePB and not tracePB.__destroyed__:
				delPB(tracePB)
			del ctMap[normalPB]
			continue
		if tracePB and tracePB.__destroyed__:
			normalPB.display = Bond.Smart
			ctMap[normalPB] = None

		# now create/remove trace pseudobonds as necessary
		a1, a2 = normalPB.atoms
		normalShowable = a1.display and a2.display
		if normalShowable:
			if tracePB:
				normalPB.display = Bond.Smart
				delPB(tracePB)
				ctMap[normalPB] = None
		else:
			if not tracePB and a1.molecule.autochain:
				shown1 = [a for a in a1.residue.atoms
								if a.display]
				shown2 = [a for a in a2.residue.atoms
								if a.display]
				if not shown1 or not shown2:
					continue
				ends1 = [(a.xformCoord().sqdistance(
					a2.xformCoord()), a) for a in shown1]
				ends2 = [(a.xformCoord().sqdistance(
					a1.xformCoord()), a) for a in shown2]
				ends1.sort()
				ends2.sort()
				tracePB = pbg.newPseudoBond(
						ends1[0][1], ends2[0][1])
				tracePB.halfbond = True
				normalPB.display = Bond.Never
				ctMap[normalPB] = tracePB

def _chainTraceSessionCB(trigName, pbg, sessionFile):
	if pbg.__destroyed__:
		from triggerSet import ONESHOT
		return ONESHOT
	from SimpleSession import sessionID
	print >> sessionFile, "ctMap = {"
	for k, v in pbg.chainTraceMapping.items():
		if v:
			value = "(%s, %s)" % tuple([repr(sessionID(a))
							for a in v.atoms])
		else:
			value = "None"
		print >> sessionFile, repr(sessionID(k)), ":", value, ","
	print >> sessionFile, "}"
	print >> sessionFile, """
try:
	newMap = {}
	from SimpleSession import idLookup
	for k, v in ctMap.items():
		if v:
			value = [idLookup(a) for a in v]
		else:
			value = v
		newMap[idLookup(k)] = value
	# avoid having the group missing its 'chainTraceMapping' attribute
	# for any period of time...
	from chimera import PseudoBondMgr
	ctGroup = PseudoBondMgr.mgr().findPseudoBondGroup(%s)
	if hasattr(ctGroup, "chainTraceMapping"):
		needHandlers = False
	else:
		needHandlers = True
		ctGroup.chainTraceMapping = {}
	ctGroup.display = %s
	# chain-trace pseudobonds only exists after a redraw...
	def restoreLBCTmap(trigName, info, trigArgs):
		ctGroup, ctMap, needHandlers = info
		try:
			from chimera import triggers, _longBondTraceCB, _chainTraceSessionCB
			from SimpleSession import SAVE_SESSION
			if needHandlers:
				ctGroup.chainTraceMapping = ctm = {}
				triggers.addHandler("Atom",
						_longBondTraceCB, ctGroup)
				triggers.addHandler(SAVE_SESSION,
						_chainTraceSessionCB, ctGroup)
			for lbpb, v in ctMap.items():
				if v:
					a1, a2 = v
					pbs1 = set(a1.pseudoBonds)
					pbs2 = set(a2.pseudoBonds)
					for pb in (pbs1 & pbs2):
						if pb.category.startswith(
						"internal-chain-"):
							value = pb
							break
					else:
						value = None
				else:
					value = v
				ctm[lbpb] = value
		finally:
			from chimera.triggerSet import ONESHOT
			return ONESHOT
	import chimera
	chimera.triggers.addHandler("post-frame", restoreLBCTmap,
						(ctGroup, newMap, needHandlers))
except:
	reportRestoreError('Error restoring chain-trace pseudobond group')
""" % (repr(pbg.category), repr(pbg.display))

def makePythonAtomsBondsResidues(models):
	"""Create Python objects for atoms, bonds, residues and coordsets.

	makePythonAtomsBondsResidues(models) => None
	"""
	tm0 = TimeIt('makePythonAtomsBondsResidues()')
	for m in models:
		try:
			m.atoms
			m.bonds
			m.residues
			m.coordSets
		except AttributeError:
			continue
	tm0.done()

def countAtomsAndResidues(models):
	"""Count the total number of atoms and residues in the given models.

	countAtomsAndResidues(models) => numAtoms, numResidues
	"""
	numAtoms = 0
	numResidues = 0
	for model in models:
		if isinstance(model, Molecule):
			numAtoms += model.numAtoms
			numResidues += model.numResidues
	return numAtoms, numResidues

_recurringClose = 0
def close(self, models):
	"""Close models and remove from list of open models.

	close(models) => None
	"""
	if isModel(models):
		models = [models]
	curModels = set(self.list(all=True))
	models = [m for m in models if m in curModels]
	if not models:
		return
	global _recurringClose, _requestCFC
	_recurringClose += 1
	for m in models:
		if not isinstance(m, ChainTrace):
			continue
		models.remove(m)
		import replyobj
		replyobj.error(
			"Cannot close autochain pseudobond group; "
			"close molecule instead\n")

	models = self.remove(models, destroying=True)
	for m in models:
		try:
			m.destroy()
		except ValueError:
			# model probably already destroyed because it was
			# associated with another model that was destroyed
			pass

	_recurringClose -= 1
	if not _recurringClose:
		import update
		if not update.inTriggerProcessing:
			update.checkForChanges()
OpenModels.close = close
del close

def closeAllModels(self, trigger=None, closure=None, triggerData=None):
	# close non-hidden models first, so that "internal chain"
	# pseudobond groups can get removed by callbacks from
	# the C++ layer.  Then close all remaining models.
	#
	# also, delay closure to the end of APPQUIT triggers, so that
	# other modules have opportunity to de-register from model-
	# closing triggers via APPQUIT
	def _closeCB(*args):
		self.close(self.list())
		self.close(self.list(all=True))
	triggers.addHandler(APPQUIT, _closeCB, None)
OpenModels.closeAllModels = closeAllModels
del closeAllModels

openModels = OpenModels.get()
openModels.viewer = viewer
triggers.addHandler(APPQUIT, openModels.closeAllModels, None)

def initializeGraphics():
	if sys.platform == "win32":
            chimera_env = os.environ['CHIMERA']
            try:
                    chimera_env.encode('ascii')
            except UnicodeError:
                    msg = ("At this time, Chimera misbehaves if the "
                            "file system path to where it is installed has "
                            "non-ASCII characters in it.  Please fix the "
                            "installation path and try again")
                    if not nogui:
                            from tkMessageBox import showerror
                            showerror(appName + ' startup error', msg)
                    else:
                            print >> sys.stderr, msg
                    raise SystemExit(1)

	# Test if OpenGL shader compilation and linking works.
	if viewer.haveShaderSupport():
		try:
			viewer.pushShader(viewer.STANDARD_SHADER)
		except:
			# Disable shader support
			import libgfxinfo as gi
			gi.disable(gi.Shading)
			replyobj.info('Disabled GPU programs because a '
				      'graphics driver bug\n  was encountered '
				      'while compiling a vertex shader.\n\n')
		
	# add a background lens to viewer
	# (must be done after openModels is created)
	initializeColors(nogui)

	# set viewer defaults
	green = Color.lookup("green")
	black = Color.lookup("black")
	try:
		try:
			viewer.highlight = LensViewer.Outline
		except ValueError, e:
			replyobj.warning("%s.\n"
				"Defaulting to Fill highlight.\n"
				"\n"
				"Possible display misconfiguration.  Please\n"
				"increase the color quality (24 bit color or\n"
				"greater), update your display (graphics)\n"
				"driver, and/or upgrade your graphics card.\n"
				"Also see chimera installation instructions."
				% e)
			viewer.highlight = LensViewer.Fill
		viewer.highlightColor = green
		#viewer.lensBorder = True
		#viewer.lensBorderColor = green
		if stereo != 'mono':
			if not viewer.camera.setMode(stereo, viewer):
				replyobj.warning('Unable to set stereo camera mode\n')
		# lighting setup moved to Lighting package
	except error:
		pass

	import bgprefs
	bgprefs.initialize()
	import palettes
	palettes.initialize()

def systemPDBdir():
	pdbDirFile = pathFinder().firstExistingFile("chimera", "pdbDir",
								False, True)
	if pdbDirFile:
		scope = {}
		try:
			execfile(pdbDirFile, scope)
		except:
			replyobj.reportException("Problem executing file"
				" containing location of system PDB directory"
				" (file: %s)" % pdbDirFile)
		if scope.has_key('pdbDir'):
			pdbDir = scope['pdbDir']
		else:
			replyobj.error("File containing location of system PDB"
				" directory (file: %s) failed to define"
				" variable 'pdbDir'.\n" % pdbDirFile)
			pdbDir = None

		if not isinstance(pdbDir, basestring) and pdbDir is not None:
			replyobj.error("File containing location of system PDB"
				" directory (file: %s) failed to define"
				" variable 'pdbDir' as a string or None.\n"
				% pdbDirFile)
		else:
			return pdbDir
	else:
		replyobj.warning("Cannot find file containing location of"
						" system PDB directory\n")
	return None

# set up handling of "new molecule" preferences
openColors = [ "tan", "sky blue", "plum", "light green", "salmon",
	"light gray", "deep pink", "gold", "dodger blue", "purple" ]
def processNewMolecules(mols):
	tm0 = TimeIt('processNewMolecules()')
	from tkoptions import MoleculeColorOption, LineWidthOption, \
		RibbonDisplayOption, RibbonXSectionOption, \
		RibbonScalingOption, AtomDrawModeOption, AtomDisplayOption, \
		BondDrawModeOption, StickScaleOption, BallScaleOption, \
		AutoChainOption, RibbonHideBackboneOption
	from initprefs import MOLECULE_DEFAULT, MOL_AUTOCOLOR, MOL_COLOR, \
		MOL_LINEWIDTH, MOL_RIBBONDISP, MOL_RIBBONMODE, \
		MOL_RIBBONSCALE, MOL_ATOMDISPLAY, MOL_ATOMDRAW, MOL_BONDDRAW, \
		MOL_IONS_REPR, MOL_STICKSCALE, MOL_BALLSCALE, MOL_PERATOM, \
		MOL_AUTOCHAIN, MOL_HIDE_BACKBONE, MOL_SMART
	import preferences
	prefget = preferences.get
	smartMols = []
	id2color = {}
	uncolored = set(mols)
	for mol in mols:
		if prefget(MOLECULE_DEFAULT, MOL_AUTOCOLOR):
			molcolor = mol.color
			mol.color = None
			if mol.color != molcolor:
				# already colored somehow
				mol.color = molcolor
			else:
				if mol.id not in id2color:
					hlColor = viewer.highlightColor
					from colorTable import getColorByName
					if viewer.background is None:
						bgColor = getColorByName("black")
					else:
						bgColor = viewer.background
					if 0 <= mol.id < len(openColors) \
					and hlColor.rgba()[:3] == (0.0, 1.0, 0.0) \
					and bgColor.rgba()[:3] in [(0.0, 0.0, 0.0), (1.0, 1.0, 1.0)]:
						id2color[mol.id] = getColorByName(openColors[mol.id])
					else:
						used = [m.color for m in openModels.list()
								if m not in uncolored]
						used.extend([bgColor, hlColor])
						rgbs = [c.rgba()[:3] for c in used if c]
						from CGLtk.color import distinguishFrom
						id2color[mol.id] = MaterialColor(*distinguishFrom(rgbs,
								seed=14, numCandidates=7))
				mol.color = id2color[mol.id]
				uncolored.remove(mol)
		else:
			defColor = prefget(MOLECULE_DEFAULT, MOL_COLOR)
			if defColor != None:
				setattr(mol, MoleculeColorOption.attribute, defColor)

		lineWidth = prefget(MOLECULE_DEFAULT, MOL_LINEWIDTH)
		if lineWidth != LineWidthOption.default:
			setattr(mol, LineWidthOption.attribute, lineWidth)

		stickScale = prefget(MOLECULE_DEFAULT, MOL_STICKSCALE)
		if stickScale != StickScaleOption.default:
			setattr(mol, StickScaleOption.attribute, stickScale)

		ballScale = prefget(MOLECULE_DEFAULT, MOL_BALLSCALE)
		if ballScale != BallScaleOption.default:
			setattr(mol, BallScaleOption.attribute, ballScale)

		if prefget(MOLECULE_DEFAULT, MOL_SMART):
			smartMols.append(mol)
			continue

		name = prefget(MOLECULE_DEFAULT, MOL_RIBBONMODE)
		if name != RibbonXSectionOption.default:
			from RibbonStyleEditor import xsection
			xs = xsection.findXSection(name)
			if xs:
				for res in mol.residues:
					xs.setResidue(res)

		name = prefget(MOLECULE_DEFAULT, MOL_RIBBONSCALE)
		if name != RibbonScalingOption.default:
			from RibbonStyleEditor import scaling
			sc = scaling.findScaling(name)
			if sc:
				for res in mol.residues:
					sc.setResidue(res)

		ribbonDisp = prefget(MOLECULE_DEFAULT, MOL_RIBBONDISP)
		if ribbonDisp != RibbonDisplayOption.default:
			for res in mol.residues:
				setattr(res, RibbonDisplayOption.attribute,
								ribbonDisp)

		hideBackbone = prefget(MOLECULE_DEFAULT, MOL_HIDE_BACKBONE)
		if hideBackbone != RibbonHideBackboneOption.default:
			mol.ribbonHidesMainchain = hideBackbone

		atomDisplay = prefget(MOLECULE_DEFAULT, MOL_ATOMDISPLAY)
		if atomDisplay != AtomDisplayOption.default:
			for a in mol.atoms:
				setattr(a, AtomDisplayOption.attribute,
							atomDisplay)

		atomDraw = prefget(MOLECULE_DEFAULT, MOL_ATOMDRAW)
		if atomDraw != AtomDrawModeOption.default:
			for a in mol.atoms:
				setattr(a, AtomDrawModeOption.attribute,
							atomDraw)

		bondDraw = prefget(MOLECULE_DEFAULT, MOL_BONDDRAW)
		if bondDraw != BondDrawModeOption.default:
			for b in mol.bonds:
				setattr(b, BondDrawModeOption.attribute,
							bondDraw)

		perAtom = prefget(MOLECULE_DEFAULT, MOL_PERATOM)
		if perAtom == "by element":
			import Midas
			Midas.color('byatom', mol.oslIdent())
		elif perAtom == "by heteroatom":
			import Midas
			Midas.color('byhet', mol.oslIdent())

		autochain = prefget(MOLECULE_DEFAULT, MOL_AUTOCHAIN)
		if autochain != AutoChainOption.default:
			setattr(mol, AutoChainOption.attribute, autochain)

	if smartMols:
		from preset import preset
		preset(openedModels=smartMols)
	tm0.done()

_postCategorizeModels = []
def categorizeSurface(*args):
	tm0 = TimeIt('categorizeSurface()')
	import Categorizer
	tm1 = TimeIt('Categorizer.categorize()')
	if not Categorizer.categorize(*args):
		# not all models yet categorized
		return
	tm1.done()
	if _postCategorizeModels:
		from initprefs import MOLECULE_DEFAULT, MOL_IONS_REPR
		import preferences
		prefget = preferences.get
		ionsDraw = prefget(MOLECULE_DEFAULT, MOL_IONS_REPR)
		# since presets ask for sequences, inject MODRES info
		# before invoking them
		prefModels = []
		for m in _postCategorizeModels:
			if isinstance(m, Molecule) and not m.__destroyed__:
				if hasattr(m, "noprefs"):
					del m.noprefs
					continue
				prefModels.append(m)
		del _postCategorizeModels[:]
		processNewMolecules(prefModels)
		for model in prefModels:
			for a in ionLikeAtoms(model):
				a.drawMode = ionsDraw
	tm0.done()

def ionLike(a):
	from elements import metals
	return a.surfaceCategory == "ions" and (a.residue.numAtoms == 1
					or a.element in metals)

def defCatAtoms(trigName, myData, atoms):
	# TODO: This is happening for new molecules before categorizing surface.
	tm0 = TimeIt('defCatAtoms()')	# TIMING
	categorizeSolventAndIons(tuple(atoms.created))
	tm0.done()

_addCatHandler = OpenModels.triggers.addHandler(
				OpenModels.ADDMODEL, categorizeSurface, 0)
_bondCatHandler = triggers.addHandler('Bond', categorizeSurface, 0)
_defCatHandler = triggers.addHandler('Atom', defCatAtoms, None)

def checkKsdssp(trigName, myData, models):
	from replyobj import info, status, warning
	from initprefs import ksdsspPrefs, KSDSSP_ENERGY, KSDSSP_HELIX_LENGTH, \
							KSDSSP_STRAND_LENGTH
	import preferences
	energy = ksdsspPrefs[KSDSSP_ENERGY]
	helixLen = ksdsspPrefs[KSDSSP_HELIX_LENGTH]
	strandLen = ksdsspPrefs[KSDSSP_STRAND_LENGTH]
	for model in models:
		if not isinstance(model, Molecule):
			continue
		if model.structureAssigned or not isProtein(model):
			continue

		if model == models[0]:
			info(
"""Model %s (%s) appears to be a protein without secondary structure assignments.
Automatically computing assignments using 'ksdssp' and parameter values:
  energy cutoff %g
  minimum helix length %d
  minimum strand length %d
Use command 'help ksdssp' for more information.
""" % (model.oslIdent()[1:], model.name, energy, helixLen, strandLen))
		else:
			info("Model %s (%s) has no secondary structure assignments. Running ksdssp.\n" % (model.oslIdent()[1:], model.name))
		status("Computing secondary structure assignments...")
		try:
			model.computeSecondaryStructure(energy, helixLen, strandLen)
		except ValueError, errVal:
			if "normalize" in unicode(errVal):
				msg = "Unable to compute secondary structure assignments" \
					" due degenerate geometry in structure"
				status(msg, color="red")
				warning(msg)
			else:
				raise
		else:
			status("Computed secondary structure assignments "
							"(see reply log)")

_ckHandler = openModels.addAddHandler(checkKsdssp, None)

def _addMODRES(pdbMolecules):
	"""Add PDB MODRES residues that modify standard residues to
	residue sequence codes"""

	import resCode
	dicts =	(resCode.regex3to1, resCode.nucleic3to1, resCode.protein3to1,
			resCode.standard3to1)
	for m in pdbMolecules:
		try:
			mrRecords = m.pdbHeaders["MODRES"]
		except (AttributeError, KeyError):
			continue
		for mr in mrRecords:
			# chimera allows for 4 character residue names
			# in PDB files
			name = mr[12:16].strip()
			stdName = mr[24:28].strip()
			for d in dicts:
				if stdName in d and name not in d:
					d[name] = d[stdName]

def suppressNewMoleculeProcessing(*args):
	global _addCatHandler, _bondCatHandler, _ckHandler, _defCatHandler, _unprocessedModels
	if args: # coming from a restore-session trigger
		setLastSessionDescriptKw({})
	# in case there was an error in an earlier session restore,
	# use an if statement...
	if _addCatHandler is not None:
		openModels.deleteAddHandler(_ckHandler)
		openModels.deleteAddHandler(_addCatHandler)
		triggers.deleteHandler('Bond', _bondCatHandler)
		triggers.deleteHandler('Atom', _defCatHandler)
		_unprocessedModels = _postCategorizeModels[:]
		_bondCatHandler = _addCatHandler = _ckHandler = _defCatHandler = None

def restoreNewMoleculeProcessing(*args):
	global _addCatHandler, _bondCatHandler, _ckHandler, _defCatHandler, _postCategorizeModels
	if args:
		trigName, myData, sesKwInfo = args
		if sesKwInfo is not None:
			version, lastSessionKw = sesKwInfo
			setLastSessionDescriptKw(lastSessionKw)
	if _addCatHandler is not None:
		# old sessions had no BEGIN trigger, compensate
		return
	# fire triggers so that the below handlers aren't called
	from update import checkForChanges
	checkForChanges()
	_bondCatHandler = triggers.addHandler('Bond', categorizeSurface, 0)
	_defCatHandler = triggers.addHandler('Atom', defCatAtoms, None)
	_ckHandler = openModels.addAddHandler(checkKsdssp, None)
	_addCatHandler = openModels.addAddHandler(categorizeSurface, 0)
	_postCategorizeModels = _unprocessedModels

from SimpleSession import BEGIN_RESTORE_SESSION, END_RESTORE_SESSION
triggers.addHandler(BEGIN_RESTORE_SESSION, suppressNewMoleculeProcessing, None)
triggers.addHandler(END_RESTORE_SESSION, restoreNewMoleculeProcessing, None)

#
# export application name
#

appName = "chimera"	# actual application name
AppName = "Chimera"	# capitalized application name (used for Tk class too)

# convenience for programming...
def runCommand(*args, **kw):
	from Midas.midas_text import makeCommand
	makeCommand(*args, **kw)
