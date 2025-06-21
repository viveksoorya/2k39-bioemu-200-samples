# --- UCSF Chimera Copyright ---
# Copyright (c) 2006 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---

import array
import weakref
import cPickle as pickle

import chimera
import _molecule
import Midas
import Animate
import Scenes

# models supported
from chimera import Molecule
from chimera import MSMSModel
from chimera import MaterialColor
from chimera import PseudoBondGroup

from MoleculeSurface.msurf import atom_surface_rgba

# Legacy crap to support labels in 1.6
from Ilabel import LabelsModel as getLabelsModel
from Ilabel.Arrows import ArrowsModel as getArrowsModel

# support for fading models
FADE_NONE = 0
FADE_IN = 1
FADE_OUT = 2

# TODO: integrity checking, including:
# - evaluate saved state properties with sys.getrefcount(), id(), and
# equality operators '==' vs. 'is' to determine whether saved state is
# mostly immutable or copies of mutable objects.  Must be sure that all
# saved state variables reference objects that will persist, despite any
# changes in general view or any model properties.

# TODO: Create an API for any model to register with this
# module to handle animation.  The registration may involve
# passing references to functions for getting state data,
# resetting state data, and/or an interpolation function that
# can restore state data at any point in an interpolation sequence.

DEBUG = 0

# types which can be pickled without further checking.
pickle_ok = (bool, int, float, long, str, None, type(None), unicode)


class SceneState(object):
	"""
	A Scene object creates, updates, and retains Scene state,
	including display and model attributes
	"""
	_pickle_errs = []
	_ignore_errs = []
	_current_version = 2

	def __init__(self, disptitle, sceneName):
		"Initialise a Scene fracme state"
		self._resetRestoreVars()
		self.disptitle = disptitle
		self.name = sceneName
		self.version = 2 # track changes in how sessions are saved
		SceneState.restoreVersion = self.version # cls var needed for restores
		self._pickle_errs = [] # for reporting problems with store
		self.stateSave()

	def __getstate__(self):
		'Pickle method to save state. use "name" for compatibility'
		pickleData = {}
		pickleData['name'] = self.name
		pickleData['version'] = self.version
		#if DEBUG:
		#	self.pickleDebug(self.state)
		pickleData['state'] = self.stateDump()
		return pickleData

	def __setstate__(self, pickleData):
		'Pickle method to restore state. use"name" for compatibility'
		# recreate stateHandlers, we lose any state handlers 
		# that might have been registered with self.StateHandlerAdd()
		self._resetRestoreVars()
		self.stateHandlersSet()
		# Now restore the state (stateHandlersSet manipulates it)
		self.name = pickleData['name']
		self.version = pickleData.get('version', 1)
		SceneState.restoreVersion = self.version # cls var needed for restores
		self.state = self.stateLoad(pickleData['state'])

	def updateLabels(self, sc):
		if self.state.has_key('labels'):
			import Ilabel
			for m in chimera.openModels.list(all=True, modelTypes=[Ilabel.IlabelModel]):
				self.labelRestore(m)
			getLabelsModel()._saveScene(None, None, sc)
		if self.state.has_key('arrows'):
			self.arrowsRestore(None)
			getArrowsModel()._saveScene(None, None, sc)

	@classmethod
	def _safe_attr(cls, val, default=None, attr=None):
		"""Makes sure that val can be pickled. Returns default if it can't.
		
		Attr enables a more meaningful error message.
		Some non-pickle-able items might be members of a collection so test
		collections separately."""

		msg = "%s cannot be saved with scene (pickle)"
		err = False
		if type(val) in pickle_ok or val is None:
			return val
		elif isinstance(val, dict):
			try:
				for (vk, vv) in val.items():
					pickle.dumps(vv)
			except:
				err = True
		elif isinstance(val, list) or isinstance(val, tuple):
			try:
				for n in range(len(val)):
					pickle.dumps(val[n])
			except:
				err = True
		elif isinstance(val, set):
			try:
				for m in val:
					pickle.dumps(m)
			except:
				err = True
		else:
			try:
				pickle.loads(pickle.dumps(val))
			except:
				err = True
		if err:
			if attr:
				err = msg % (attr,)
			else:
				err = msg % (repr(val),)
			print err
			cls._pickle_errs.append(err)
			return default
		return val

	'''these next two methods were created when the module root for objects
	changed from _chimera to _molecule.'''
	@classmethod
	def c_assert_same(cls, s1, s2):
		'only call to compare object type strings. strip off the module path first.'
		assert s1[s1.rfind('.') + 1:] == s2[s2.rfind('.') + 1:]

	def assert_same(self, s1, s2):
		'only call to compare object type strings. strip off the module path first.'
		assert s1[s1.rfind('.') + 1:] == s2[s2.rfind('.') + 1:]

	@classmethod
	def AttrSave(cls, obj, exclusions=[], funcDispatch={}):
		'''
		A method to generically extract attributes from Chimera
		objects.  It uses dir(obj) and getattr() to parse or extract
		useful scene data into a new dict, with the aim that this
		dict will be compatible with pickle.  Any attributes
		that are callable or begin with '__' or '_' are automatically
		excluded.  To specify specific attributes to exclude, provide
		a list of strings in the 'exclusions', which are
		a list of attributes to be skipped for dir(obj).  To handle
		specific attributes with custom conversion functions, specify
		a funcDispatch dict with attr keys that refer to functions that
		will return state information that is compatible with pickle.
		'''
		if obj is None:
			return
		d = {}
		# Why use 'sorted' - it's a performance hit.
		#for attr in sorted(dir(obj)):
		for attr in dir(obj):
			# startswith('_') catches '__' too!
			#if  attr.startswith('__') or \
			if attr.startswith('_') or attr in exclusions:
				continue
			val = getattr(obj, attr)
			if callable(val):
				continue
			# Run a custom save method and continue.
			if attr in funcDispatch:
				fSave = funcDispatch[attr]
				d[attr] = fSave(val)
				continue
			# Known objects with save methods.
			# Did not anticipate using these conditionals with
			# derived classes of those specified.  Maybe use
			# a 'valueDispatch' dict?
			if not val: # return legitimate "none" attributes
				d[attr] = val
				continue
			if isinstance(val, chimera.Camera):
				val = cls.CameraSave(val)
			elif isinstance(val, chimera.DirectionalLight):
				val = cls.DirectionalLightSave(val)
			elif isinstance(val, chimera.MaterialColor):
				val = cls.MaterialColorSave(val)
			elif isinstance(val, chimera.Plane):
				val = cls.PlaneSave(val)
			elif isinstance(val, (chimera.Point, chimera.Vector)):
				val = cls.VectorSave(val)
			#if isinstance(val, chimera.OpenState):
			#	val = cls.OpenStateSave(val)
			#if isinstance(val, chimera.CoordSet):
			#	val = cls.CoordSetSave(val)
			else:
				# TODO: Explore using deepcopy on this val, in
				# case it is any mutable type (eg, list)
				val = cls._safe_attr(val, None, attr)

			if val: # skip attr which won't pickle
				d[attr] = val

		return d

	def attrRestore(self, obj, objDict, exclusions=[], funcDispatch={}):
		'''
		A method to generically restore attributes from Chimera
		objects.  It iterates the sorted keys (attr) of objDict and
		uses setattr(obj, attr, objDict[attr]).  The objDict should
		contain keys and values that are compatible with pickle.
		
		To specify attributes to exclude from restore processing,
		provide a list of strings in the 'exclusions', which are
		a list of attributes to be skipped.  Whenever the objDict is 
		created by AttrSave, any attributes that are callable or begin 
		with '__' or '_' are automatically excluded.
		
		To handle specific attributes with custom conversion functions,
		specify a funcDispatch dict with attr keys that refer to functions,
		which will restore obj.attr values based on values in objDict[attr].
		The function call is: func(getattr(obj, attr), objDict[attr]).
		'''
		if obj is None:
			raise chimera.error('cannot restore None')
		if objDict is None:
			raise chimera.error('nothing to restore in objDict')
		for attr in sorted(objDict.keys()):
			if attr in exclusions:
				continue
			if attr in funcDispatch:
				restoreFunc = funcDispatch[attr]
				objVal = getattr(obj, attr)
				restoreFunc(objVal, val)
				#val = restoreFunc(val)
				#setattr(obj, attr, val)
				continue
			val = objDict[attr]
			if isinstance(val, dict):
				type = val.get('type')
				#if type == repr(chimera.Camera):
				#	self.cameraRestore()
				#	continue
				if type == repr(chimera.DirectionalLight):
					attrObj = getattr(obj, attr)
					self.directionalLightRestore(attrObj, val)
					continue
				if type == repr(chimera.MaterialColor):
					val = self.MaterialColorRestore(val)
				if type == repr(chimera.Plane):
					val = self.PlaneRestore(val)
				if type == repr(chimera.Point):
					val = self.PointRestore(val)
				if type == repr(chimera.Vector):
					val = self.VectorRestore(val)
			setattr(obj, attr, val)

	@classmethod
	def CameraSave(cls, camera):
		'Save state for camera parameters (model independent)'
		exclusions = [
			'focalExtent', # not writable
			'hitherExtent', # not writable
			'projectionExtent', # not writable
		]
		camDict = cls.AttrSave(camera, exclusions)
		camDict['type'] = repr(chimera.Camera)
		return camDict

	def cameraRestore(self, camDict):
		"Restore the camera properties of the scene"
		if DEBUG:
			self.debugMessage('SceneState.cameraRestore')
		cam = chimera.viewer.camera
		if self.frameCount == self.frames:
			# make sure we finish
			# (should be the same as setting the rate to 1)
			self.attrRestore(cam, camDict)
			# Return from static scene restoration
			return
		#
		# Animation for camera parameters
		#
		# This interpolation function is used in map calls below
		interp = lambda i, j: i + (j - i) * self.rate
		# Camera properties
		# TODO: Add properties for stereo view
		# For stereo projection, eyeOffset, eyeSeparation, fieldOfView and
		# walleyeScale would have to be included.  They are all floating 
		# point numbers and therefore should be simple to animate. 
		# ortho is a flag.  I guess it's possible to animate from an
		# orthographic view to a perspective view, but I don't see 
		# much point of it.
		cam.center = tuple(map(interp, cam.center, camDict['center']))
		cam.focal += (camDict['focal'] - cam.focal) * self.rate
		cam.eyeSeparation += (camDict['eyeSeparation'] - cam.eyeSeparation) * self.rate
		cam.screenDistance += (camDict['screenDistance'] - cam.screenDistance) * self.rate
		# Camera: global clipping planes
		if chimera.viewer.clipping:
			cam.nearFar = tuple(map(interp, cam.nearFar, camDict['nearFar']))

	@classmethod
	def CenterOfRotationSave(cls, method, center):
		'''Save state for openModels center of rotation (model independent)'''
		CofR = {}
		CofR['cofr'] = cls.PointSave(center)
		CofR['cofrMethod'] = method
		return CofR

	def centerOfRotationRestore(self):
		"Restore the center of rotation properties of the scene"
		if DEBUG:
			self.debugMessage('SceneState.centerOfRotationRestore')
		# Get the current openModels and saved state parameters
		om = chimera.openModels
		CofR = self.state['view']['center']
		cofr = self.PointRestore(CofR['cofr'])
		cofrMethod = CofR['cofrMethod']
		# Center of rotation
		if cofrMethod is not None:
			om.cofrMethod = cofrMethod
		if self.frameCount == self.frames:
			# make sure we finish
			# (should be the same as setting the rate to 1)
			if om.cofrMethod != om.Independent:
				om.cofr = cofr
			# Return from static scene restoration
			return
		#
		# Animation for center of rotation
		if cofrMethod == om.cofrMethod and om.cofrMethod != om.Independent:
			om.cofr += (cofr - om.cofr) * self.rate
		return

	@classmethod
	def ClipsSave(cls, model=None):
		'''Save state for model clipping planes'''
		clips = (
			model.useClipPlane,
			cls.PlaneSave(model.clipPlane),
			model.useClipThickness,
			model.clipThickness)
		return clips

	def clipsRestore(self):
		'Restore the clipping planes of the scene'
		if DEBUG:
			self.debugMessage('SceneState.clipsRestore')
		clips = self.state['clips']
		# Note that clipping planes index by 'model'.
		# Ensure we skip models that no longer exist.
		openModels = chimera.openModels.list(all=True)
		clipModels = [m for m in clips.keys() if m in openModels]
		# Remove references to any missing models, to release them to GC.
		for m in clips.keys():
			if m not in clipModels:
				del clips[m]
		# Ensure a complete transition at the end for clipping planes
		if self.frameCount == self.frames:
			# make sure we finish
			# (should be the same as setting the rate to 1)
			for m in clipModels:
				clipInfo = clips[m]
				useClip, plane, useThickness, thickness = clipInfo
				m.clipPlane = self.PlaneRestore(plane)
				m.useClipPlane = useClip
				m.useClipThickness = useThickness
				m.clipThickness = thickness
			return
		#
		# Animation for clipping planes
		#
		for m in clipModels:
			clipInfo = clips[m]
			useClip, plane, useThickness, thickness = clipInfo
			savPlane = self.PlaneRestore(plane)
			if useClip and m.useClipPlane:
				# avoid modifying copy of clip plane...
				curPlane = m.clipPlane
				curPlane.origin += (savPlane.origin - curPlane.origin) * self.rate
				curPlane.normal += (savPlane.normal - curPlane.normal) * self.rate
				m.clipPlane = curPlane
				if m.useClipThickness == useThickness:
					m.clipThickness += (thickness - m.clipThickness) * self.rate
				else:
					m.useClipThickness = useThickness
					m.clipThickness = thickness
			else:
				m.useClipPlane = useClip
				m.clipPlane = savPlane
				m.useClipThickness = useThickness
				m.clipThickness = thickness

	@classmethod
	def CoordSetSave(cls, coordset):
		assert isinstance(coordset, chimera.CoordSet)
		d = {}
		d['type'] = repr(chimera.CoordSet)
		d['id'] = coordset.id
		return d

	def coordSetRestore(self, obj, objDict):
		assert isinstance(obj, chimera.CoordSet)
		self.assert_same(objDict['type'], repr(chimera.CoordSet))
		obj.id = objDict['id']

	#def destroy(self):
	#	pass

	def copyColor(self, color_hierarchy):
		'''Resolve the hierarchy, converting saved color if needed, and 
		return a copy of the color for use by the caller.
		
		This function can return None. It is up to the caller to send a hierarchy
		which will result in at least one list entry resolving to a color.'''
		for color in color_hierarchy:
			if isinstance(color, dict):
				color = self.MaterialColorRestore(color)
			if isinstance(color, chimera.MaterialColor):
				return chimera.MaterialColor(color, color, 1)

	def makeTransparentColor(self, color):
		if color:
			c = chimera.MaterialColor(color, color, 1)
			c.opacity = 0.0
			return c
		else:
			return color

	def debugMessage(self, methodName):
		msg = '%s:\t' % methodName
		msg += 'frameCount = %d, rate = %g' % (self.frameCount, self.rate)
		print msg

	@classmethod
	def DirectionalLightSave(cls, light):
		assert isinstance(light, chimera.DirectionalLight)
		objDict = cls.AttrSave(light)
		objDict['type'] = repr(chimera.DirectionalLight)
		return objDict

	def directionalLightRestore(self, light, lightDict):
		if light is None:
			return
		assert isinstance(light, chimera.DirectionalLight)
		self.assert_same(lightDict['type'], repr(chimera.DirectionalLight))
		#exclusions = []
		#funcDispatch = {
		#	'color': self.MaterialColorRestore,
		#	'direction': self.VectorRestore,
		#}
		self.attrRestore(light, lightDict)

	def arrowsRestore(self, ignoreModel=None):
		'Save state for an arrows model'
		# Note that the restore information is not easily or reliably
		# related to the arrowsModel.arrows list, but the code below
		# will assume the 'ident' property can be used for this purpose.
		import Ilabel
		from Ilabel import Arrows
		arrowsModel = Arrows.ArrowsModel()
		if DEBUG:
			self.debugMessage('SceneState.arrowsRestore')
		try:
			# Save the current arrows info.
			curInfo = arrowsModel.getRestoreInfo()
			curArrows = curInfo['arrows']
			# Get the saved arrows info for this scene.
			savInfo = self.state['arrows'][arrowsModel]
			savArrows = savInfo['arrows']
		except:
			if DEBUG:
				print 'Arrows model not in saved state'
			# Hide all the arrows
			arrowsModel.display = False
			return
		# It's possible to restore in one command:
		# arrowsModel.restore(savInfo)
		# However, that could destroy some arrow models that are required 
		# in other scenes or the current display state.  So, a tedious
		# process is required to restore the scene state.
		#
		# Create any arrows in the saved state that do not exist in
		# the current set of arrows.
		curArrowsLst = arrowsModel.arrows
		curArrowsID = [a.ident for a in curArrowsLst]
		savArrowsID = [arrow[1]['ident'] for arrow in savArrows]
		savArrowsMissing = [id for id in savArrowsID if id not in curArrowsID]
		for arrowID in savArrowsMissing:
			# Create a "dummy" arrow that will be refined below
			arrowsModel.addArrow(0.5, 0.5, ident=arrowID)
		# Update the current arrows:
		curArrowsLst = arrowsModel.arrows
		curArrowsID = [a.ident for a in curArrowsLst]
		# Get the current arrow objects in the saved scene state.
		savArrowsLst = [a for a in curArrowsLst if a.ident in savArrowsID]
		savArrowsID = [a.ident for a in savArrowsLst]
		# Hide all the arrows that are not in the saved state.
		ignArrowsLst = [a for a in curArrowsLst if not a in savArrowsLst]
		for arrow in ignArrowsLst:
			arrow.setShown(False)
		# Restore all the saved arrow parameters
		for arrowInfo in savArrows:
			arrowPos = arrowInfo[0]
			arrowDict = arrowInfo[1]
			arrowID = arrowDict['ident']
			arrowObj = savArrowsLst[savArrowsID.index(arrowID)]
			assert arrowID == arrowObj.ident
			arrowObj.start, arrowObj.end = arrowPos
			# Don't use self.MaterialColorRestore here!
			arrowObj.setColor(arrowDict['color'])
			arrowObj.setShown(arrowDict['shown'])
			arrowObj.setWeight(arrowDict['weight'])
			arrowObj.setHead(arrowDict['head'])

	def labelRestore(self, model=None):
		'Restore state for a 2dlabel'
		import Ilabel
		labelsModel = Ilabel.LabelsModel()
		if DEBUG:
			self.debugMessage('SceneState.labelRestore')
		try:
			# Obtain saved label parameters
			labelsDict = self.state['labels'][model]
			assert model is labelsModel
		except Exception, e:
			if DEBUG:
				print 'Labels model not in saved state'
				print type(model)
				print dir(model)
			model.display = False
			return
		labelsModel.display = labelsDict['display']
		labelsModel.color = self.MaterialColorRestore(labelsDict['color'])
		labelsModel.curLabel = None
		# loop through labels to restore display properties.
		for labelID, label in labelsModel.labelMap.items():
			try:
				labelDict = labelsDict['labels'][labelID]
			except:
				# There is no state saved for this label
				if DEBUG:
					print label.text()
				label.shown = False
				continue

			self._load_label(label, labelDict)

		# look for labels no longer in the model are part of this scene.
		for labelID, labelDict in labelsDict['labels'].items():
			if labelID in labelsModel.labelMap:
				continue
			label = labelsModel.newLabel(labelDict['position'], labelID)
			self._load_label(label, labelDict)

	def _load_label(self, label, labelDict):
		'utility function for label restoration'
		import Ilabel
		label.pos = labelDict['position']
		label.set(labelDict['text'])
		label.shown = False
		label.shown = True
		label.shown = labelDict['shown']
		for iline, line in enumerate(label.lines):
			# Each line is a list of Ilabel.Label.Character
			cDict = labelDict['lines'][iline]
			for ci, c in enumerate(line):
				c.fontName = cDict['fontName'][ci]
				c.size = cDict['size'][ci]
				c.rgba = cDict['rgba'][ci]
				c.style = cDict['style'][ci]
				c.baselineOffset = cDict['baselineOffset'][ci]

	def export(self):
		"Save a scene state to the file system"
		# TODO: pickle or shelve the scene state
		chimera.replyobj.warning('scene state export is not implemented')
		return

	def integrity(self, removedModel=None):
		'''Check if any chimera models to be removed are in the scene state.'''
		# This method is called from the Scene class and any integrity issues
		# are handled in the Scenes class.
		affected = set()
		if removedModel:
			for k, v in self.state.items():
				if (isinstance(v, weakref.WeakKeyDictionary) and removedModel in v):
					# All the keys of this WeakKeyDictionary are models
					affected.add(removedModel)
					del v[removedModel]
		return affected

	def interpolateColor(self, c1, def1, c2, def2):
		'''interpolate from one color to another. defaults are used if one
		color is None.'''
		if not c1:
			c1 = def1
		if not c2:
			c2 = def2
		if c1 == c2:
			return c2
		return MaterialColor(c1, c2, self.rate)

	def _resetRestoreVars(self):
		self.aromatics_to_interpolate = {}
		self.atomColors_to_interpolate = {}
		self.atomSurfColor_to_interpolate = {}
		self.atomLabelColor_to_interpolate = {}
		self.atomLabel_to_interpolate = {}
		self.bonds_to_interpolate = {}
		self.bondlabels_to_interpolate = {}
		self.res_fillColor_to_interpolate = {}
		self.res_labelColor_to_interpolate = {}
		self.res_ribbonColor_to_interpolate = {}
		self.molecule_color_to_interpolate = {}
		self.msms_color_to_interpolate = {}
		self.surfaceOpacity_to_interpolate = {}
		self.fadeOutModels = []
		self.fadeOutAtomSurfs = []
		self._startActiveCoordID = None

	def initStateRestore(self):
		'''determine what atoms and bonds actually need per frame property
		transtions and save them for use for all frames in this transtion.'''
		self._resetRestoreVars()
		hold_molecules = []
		fade_surfaces = {}
		for model in chimera.openModels.list(all=True):
			if isinstance(model, chimera.Molecule):
				# hold molecules until surfaces have been examined
				hold_molecules.append(model)
				continue

			"""surface fading will occur if
				the surface.display bit changes between scenes
				it is not in scene 1 but is in scene 2
				it is present in scene 1 but not in scene 2
				
				cases of partial fades are handled at the atom level."""
			if isinstance(model, chimera.MSMSModel):
				surf_fading = FADE_NONE
				self.surfaceOpacity_to_interpolate[model.molecule] = []
				if model not in self.state['surfaces'] and model.display:
					surf_fading = FADE_OUT
					self.fadeOutModels.append(model)
					surfDict = None
				elif model in self.state['surfaces']:
					surfDict = self.state['surfaces'][model]
					if model.display and not surfDict['display']:
						surf_fading = FADE_OUT
						self.fadeOutModels.append(model)
					if surfDict['display'] and not model.display:
						surf_fading = FADE_IN
				if surf_fading:
					fade_surfaces[model.molecule] = surf_fading

			if isinstance(model, chimera.PseudoBondGroup):
				pass # for now

		model_has_surface_fade = {}
		for model in hold_molecules:
			mol_fading = FADE_NONE
			if model in self.state['molecules']:
				molDict = self.state['molecules'][model]
				molecule_toColor = self.copyColor([molDict['color']])
				if model.display and not molDict['display']:
					mol_fading = FADE_OUT
					self.fadeOutModels.append(model)
					molecule_toColor = self.makeTransparentColor(molecule_toColor)
				if molDict['display'] and not model.display:
					mol_fading = FADE_IN
					model.color = self.makeTransparentColor(model.color)
					model.display = True
				if mol_fading:
					self.molecule_color_to_interpolate[model] = (model.color,
						molecule_toColor)
			else:
				if model.display:
					mol_fading = FADE_OUT
					molecule_toColor = self.makeTransparentColor(model.color)
					self.molecule_color_to_interpolate[model] = (model.color,
						molecule_toColor)
				continue
			self.atomColors_to_interpolate[model] = []
			self.atomSurfColor_to_interpolate[model] = []
			self.atomLabelColor_to_interpolate[model] = []
			self.atomLabel_to_interpolate[model] = []

			self.bonds_to_interpolate[model] = []
			self.bondlabels_to_interpolate[model] = []

			self.res_fillColor_to_interpolate[model] = []
			self.res_labelColor_to_interpolate[model] = []
			self.res_ribbonColor_to_interpolate[model] = []

			self.aromatics_to_interpolate[model] = []

			atomDict = molDict['atoms']
			defColor = self.MaterialColorRestore(molDict['color'])
			for ai, atom in enumerate(model.atoms):
				atom_fading = FADE_NONE

				# colors might be changing, molecule fading or atoms fading	
				atom_toColor = self.copyColor([atomDict['color'][ai], defColor])
				if mol_fading or atom.shownColor() != atom_toColor or \
					atom.display != atomDict['display'][ai]:
					if atom.display != atomDict['display'][ai]:
						if atom.display and not atomDict['display'][ai]:
							atom_fading = FADE_OUT
						elif not atom.display and atomDict['display'][ai]:
							atom_fading = FADE_IN

					if mol_fading == FADE_IN or atom_fading == FADE_IN:
						if not atom.color:
							atom.color = model.color
						atom.color = self.makeTransparentColor(atom.color)
						atom.display = True
					elif mol_fading == FADE_OUT or atom_fading == FADE_OUT:
						if model not in self.fadeOutModels:
							self.fadeOutModels.append(model)
						atom_toColor = self.makeTransparentColor(atom_toColor)
					self.atomColors_to_interpolate[model].append((atom, atom_toColor))

				surf_fading = atomSurf_fading = FADE_NONE
				if model in fade_surfaces:
					surf_fading = fade_surfaces[model]
				if atom.surfaceDisplay != atomDict['surfaceDisplay'][ai]:
					if atom.surfaceDisplay and not atomDict['surfaceDisplay'][ai]:
						atomSurf_fading = FADE_OUT
					elif not atom.surfaceDisplay and atomDict['surfaceDisplay'][ai]:
						atomSurf_fading = FADE_IN

				# surfaceOpacity, if used, takes precedent
				from_op = to_op = -1.0
				if atom.surfaceOpacity >= 0.0:
					from_op = atom.surfaceOpacity
				if atomDict['surfaceOpacity'][ai] >= 0.0:
					to_op = atomDict['surfaceOpacity'][ai]
				if model in self.surfaceOpacity_to_interpolate and (
					surf_fading or atomSurf_fading or
					(to_op >= 0.0 or from_op >= 0.0 and to_op != from_op)):
					# at least one set so use surfaceOpacity value during transition
					if to_op < 0.0:
						surface_toColor = self.copyColor([atomDict['surfaceColor'],
							defColor])
						to_op = surface_toColor.opacity
					if from_op < 0.0:
						from_op = atom_surface_rgba(atom)[3]
					# surface fading overrides the specifics of the surface
					if surf_fading == FADE_IN or atomSurf_fading == FADE_IN:
						from_op = 0.0
						atom.surfaceOpacity = 0.0
					if surf_fading == FADE_OUT or atomSurf_fading == FADE_OUT:
						to_op = 0.0
						if atomSurf_fading == FADE_OUT:
							self.fadeOutAtomSurfs.append(atom)
					# final bound check:
#					if to_op > 1.0:
#						to_op = 1.0
#					if from_op > 1.0:
#						from_op = 1.0
					op_range = float(to_op - from_op)
					self.surfaceOpacity_to_interpolate[model].append((atom, from_op, op_range))

				# support surfaces fading in/out
# Surface interpolation will be done using custom colors below
#				atomSurface_toColor = self.copyColor([atomDict['surfaceColor'][ai], defColor])
#				if surf_fading or atomSurf_fading or atom.surfaceColor != atomSurface_toColor:
#					if surf_fading == FADE_IN or atomSurf_fading == FADE_IN:
#						atom.surfaceDisplay = True
#						if not atom.surfaceColor:
#							atom.surfaceColor = model.color
#						atom.surfaceColor = self.makeTransparentColor(atom.surfaceColor)
#					elif surf_fading == FADE_OUT or atomSurf_fading == FADE_OUT:
#						atomSurface_toColor = self.makeTransparentColor(atomSurface_toColor)
#					self.atomSurfColor_to_interpolate[model].append((atom, atomSurface_toColor))
				if surf_fading or atomSurf_fading:
					model_has_surface_fade[model] = True

				# support labels fading in/out with molecule fade
				atomLabel_toColor = self.copyColor([atomDict['labelColor'][ai], defColor])
				if mol_fading or atom.labelColor != atomLabel_toColor:
					if mol_fading == FADE_IN:
						if atom.labelColor:
							atom.labelColor = self.makeTransparentColor(atom.labelColor)
					elif mol_fading == FADE_OUT:
						if atomLabel_toColor:
							atomLabel_toColor = self.makeTransparentColor(atomLabel_toColor)
					self.atomLabelColor_to_interpolate[model].append((atom, atomLabel_toColor))

				# support labels fading in/out when atoms remain visible
				# copy the label too in a fade in scenario
				if atom.label != atomDict['label'][ai]:
					atomLabel_fromColor = self.copyColor([atom.labelColor, atom.color, defColor])
					atomLabel_toColor = self.copyColor([atomDict['labelColor'][ai], atom.color, defColor])
					if atom.label and not atomDict['label'][ai]:
						# label fading out
						atomLabel_toColor = self.makeTransparentColor(atomLabel_toColor)
						atomLabel = atom.label
					elif not atom.label and atomDict['label'][ai]:
						# label fading in
						if atom.labelColor is None:
							atom.labelColor = atomLabel_fromColor
						atom.labelColor = self.makeTransparentColor(atom.labelColor)
						atomLabel = atomDict['label'][ai]
					else:
						atomLabel = atomDict['label'][ai]
					self.atomLabel_to_interpolate[model].append((atom, atomLabel_toColor, atomLabel))

			# bonds
			bondDict = molDict['bonds']
			for bi, bond in enumerate(model.bonds):
				bond_toColor = self.copyColor([bondDict['color'][bi], defColor])
				if mol_fading or bond.color != bond_toColor:
					if mol_fading == FADE_IN:
						if bond.color:
							bond.color = self.makeTransparentColor(bond.color)
					elif mol_fading == FADE_OUT:
						if bond_toColor:
							bond_toColor = self.makeTransparentColor(bond_toColor)
					self.bonds_to_interpolate[model].append((bond, bond_toColor))
				bondLabel_toColor = self.copyColor([bondDict['labelColor'][bi], defColor])
				if mol_fading or bond.labelColor != bondLabel_toColor:
					if mol_fading == FADE_IN:
						if bond.labelColor:
							bond.labelColor = self.makeTransparentColor(bond.labelColor)
					elif mol_fading == FADE_OUT:
						if bondLabel_toColor:
							bondLabel_toColor = self.makeTransparentColor(bondLabel_toColor)
					self.bondlabels_to_interpolate[model].append((bond, bondLabel_toColor))

			# residues
			resDict = molDict['residues']
			for ri, res in enumerate(model.residues):
				if mol_fading == FADE_OUT:
					res_fading = FADE_OUT
				elif mol_fading == FADE_IN and resDict['ribbonDisplay'][ri]:
					res_fading = FADE_IN
				elif res.ribbonDisplay != resDict['ribbonDisplay'][ri]:
					if res.ribbonDisplay:
						res_fading = FADE_OUT
					else:
						res_fading = FADE_IN
				else:
					res_fading = FADE_NONE

				resFill_toColor = self.copyColor([resDict['fillColor'][ri], defColor])
				if res_fading or res.fillColor != resFill_toColor:
					if res_fading == FADE_IN:
						if res.fillColor:
							res.fillColor = self.makeTransparentColor(res.fillColor)
					elif res_fading == FADE_OUT:
						if resFill_toColor:
							resFill_toColor = self.makeTransparentColor(resFill_toColor)
					self.res_fillColor_to_interpolate[model].append((res, resFill_toColor))
				resLabel_toColor = self.copyColor([resDict['labelColor'][ri], defColor])
				if res_fading or res.labelColor != resLabel_toColor:
					if res_fading == FADE_IN:
						if res.labelColor:
							res.labelColor = self.makeTransparentColor(res.labelColor)
					elif res_fading == FADE_OUT:
						if resLabel_toColor:
							resLabel_toColor = self.makeTransparentColor(resLabel_toColor)
					self.res_labelColor_to_interpolate[model].append((res, resLabel_toColor))
				resRibbon_toColor = self.copyColor([resDict['ribbonColor'][ri], defColor])
				if res_fading or res.ribbonColor != resRibbon_toColor:
					if res_fading == FADE_IN:
						if res.ribbonColor:
							res.ribbonColor = self.makeTransparentColor(res.ribbonColor)
						res.ribbonDisplay = True
					elif res_fading == FADE_OUT:
						if resRibbon_toColor:
							resRibbon_toColor = self.makeTransparentColor(resRibbon_toColor)
					self.res_ribbonColor_to_interpolate[model].append((res, resRibbon_toColor))

		# Initialize parameters for MSMS surfaces that are either
		# changing (custom) colors or fading in or out
		for model in chimera.openModels.list(modelTypes=[MSMSModel]):
			try:
				colorMode = self.state['surfaces'][model]['colorMode']
			except KeyError:
				colorMode = None
			if model.colorMode != colorMode:
				# Color mode is changing
				self._msmsInitInterpolation(model)
			elif model.molecule in model_has_surface_fade \
			or model.molecule in fade_surfaces:
				# Molecule or atom surface is fading
				self._msmsInitInterpolation(model)
			elif model.colorMode != model.Custom:
				# Need to convert to custom color mode for interpolation
				self._msmsInitInterpolation(model)
			else:
				# Custom colors, maybe they changed
				self._msmsCheckCustomColorChange(model)
		if model_has_surface_fade or fade_surfaces:
			chimera.viewer.singleLayerTransparency = False

		# Save initial coordinate set id
		self._startActiveCoordID = dict()
		for model in chimera.openModels.list(modelTypes=[Molecule]):
			self._startActiveCoordID[model] = model.activeCoordSet.id

	def _msmsInitInterpolation(self, model):
		if model.molecule is None:
			# Reference model is closed
			return
		try:
			molDict = self.state['molecules'][model.molecule]
		except KeyError:
			# How does this happen?
			# Reference model was not saved or got deleted?
			# In any case, the colors and display states
			# cannot change so no interpolation.
			return
		atomDict = molDict['atoms']
		atomIndexMap = dict()
		for ai, atom in enumerate(model.molecule.atoms):
			atomIndexMap[atom] = ai

		# Create source colors
		if model.colorMode == model.Custom:
			import copy
			source = copy.copy(model.customRGBA)
		elif model.colorMode == model.ByAtom and model.atomMap is not None:
			from MoleculeSurface.msurf import atom_surface_rgba
			source = [ list(atom_surface_rgba(va)) for va in model.atomMap ]
		else:
			# Assume Molecule color mode
			from MoleculeSurface.msurf import molecule_surface_rgba
			rgba = list(molecule_surface_rgba(model.molecule))
			source = model.vertexCount * [ rgba ]
		# Set undisplayed atoms to transparent in case
		# we need to fade them in
		# TODO: Handle visibilityMode other than ByAtom
		fadeInAtoms = set()
		if model.visibilityMode == model.ByAtom and model.atomMap is not None:
			for si, atom in enumerate(model.atomMap):
				if not atom.surfaceDisplay:
					source[si][3] = 0
					fadeInAtoms.add(atom)
#		else:
#			print "unsupported surface visibility mode", model.visibilityMode
		import numpy
		if not isinstance(source, numpy.ndarray):
			source = numpy.array(source, dtype=float)

		# Create target colors
		def makeRGBA(c, o):
			rgba = list(c.rgba())
			if o >= 0:
				rgba[3] = o
			return rgba
		try:
			surfDict = self.state['surfaces'][model]
		except KeyError:
			surfDict = None
		if surfDict is None:
			import copy
			target = copy.copy(source)
			target[:,3] = 0
		elif surfDict['colorMode'] == model.Custom:
			import copy
			target = copy.copy(surfDict['vertexColors'])
		elif surfDict['colorMode'] == model.ByAtom and model.atomMap is not None:
			c = self.copyColor([ molDict['surfaceColor'], molDict['color'] ])
			o = molDict['surfaceOpacity']
			molRGBA = makeRGBA(c, o)
			target = list()
			for atom in model.atomMap:
				ai = atomIndexMap[atom]
				c = self.copyColor([ atomDict['surfaceColor'][ai] ])
				if c is None:
					rgba = molRGBA
				else:
					rgba = makeRGBA(c, atomDict['surfaceOpacity'][ai])
				target.append(rgba)
		else:
			# Assume Molecule color mode
			molDict = self.state['molecules'][model.molecule]
			c = self.copyColor([ molDict['surfaceColor'], molDict['color'] ])
			o = molDict['surfaceOpacity']
			rbba = makeRGBA(c, o)
			target = model.vertexCount * [ rgba ]
		# Set undisplayed atoms to transparent in case
		# we need to fade them out
		# TODO: Handle visibilityMode other than ByAtom
		if surfDict is None:
			pass
		elif surfDict['visibilityMode'] == model.ByAtom and model.atomMap is not None:
			for si, atom in enumerate(model.atomMap):
				ai = atomIndexMap[atom]
				if not atomDict['surfaceDisplay'][ai]:
					target[si][3] = 0
#		else:
#			print "unsupported surface visibility mode", surfDict['visibilityMode']

		# If source does not match target, set up interpolation
		if not self._msmsSameColors(source, target):
			# Convert to numpy array for interpolation
			if not isinstance(target, numpy.ndarray):
				target = numpy.array(target, dtype=float)
			self.msms_color_to_interpolate[model] = target
			model.display = True
			model.set_custom_rgba(source)
			if fadeInAtoms:
				for atom in fadeInAtoms:
					atom.surfaceDisplay = True
				model.update_visibility()

	def _msmsCheckCustomColorChange(self, model):
		surfDict = self.state['surfaces'][model]
		if not self._msmsSameColors(surfDict['vertexColors'], model.customRGBA):
			self.msms_color_to_interpolate[model] = surfDict['vertexColors']

	def _msmsSameColors(self, cv1, cv2):
		import numpy
		if isinstance(cv1, numpy.ndarray) and isinstance(cv2, numpy.ndarray):
			if cv1.shape != cv2.shape:
				return False
			return (cv1 == cv2).all()
		if len(cv1) != len(cv2):
			return False
		for rgba1, rgba2 in zip(cv1, cv2):
			for i in range(4):
				if rgba1[i] != rgba2[i]:
					return False
		return True


	def stateRestoreComplete(self):
		self._startActiveCoordID = None

	# Keep a set of rgba objects.  This might optimize memory, but only so far
	# as the objects it contains are referenced in scene data, otherwise it 
	# might prevent garbage collection by keeping 1 reference to them.
	materialColors = {}
	@classmethod
	def MaterialColorSave(cls, mc):
		'Return an RGBA tuple from a MaterialColor object'
		if mc is None:
			return
		assert isinstance(mc, chimera.MaterialColor)
		colorDict = {}
		colorDict['type'] = repr(chimera.MaterialColor)
		rgba = mc.rgba()
		# Try to optimize the number of rgba objects in the state
		try:
			rgba = cls.materialColors[rgba]
		except KeyError:
			cls.materialColors[rgba] = rgba
		#if rgba in cls.materialColors:
		#	rgba = cls.materialColors.get(rgba)
		#else:
		#	cls.materialColors[rgba] = rgba
		colorDict['rgba'] = rgba
		return colorDict

	@classmethod
	def MaterialColorRestore(cls, colorDict):
		'Return a MaterialColor object from another or an RGBA tuple'
		if colorDict is None:
			return
		cls.c_assert_same(colorDict['type'], repr(chimera.MaterialColor))
		rgba = colorDict['rgba']
		if isinstance(rgba, (tuple, list)):
			return chimera.MaterialColor(*rgba)
		return None

	def moleculeCompress(self, molDict):
		'''use functions derived from SimpleSession to compress selected 
		attributes which are arrays. A copy has to be returned to avoid
		overwritting state dictionaries.'''
		from sessionVersions.v2 import atomsCompress, bondsCompress, residuesCompress
		newMolDict = {}
		newMolDict['atoms'] = atomsCompress(molDict['atoms'])
		newMolDict['bonds'] = bondsCompress(molDict['bonds'])
		newMolDict['residues'] = residuesCompress(molDict['residues'])
		for k in molDict.keys():
			if not newMolDict.has_key(k):
				newMolDict[k] = molDict[k]
		return newMolDict

	def moleculeConvert(self, molDict, oldver):
		'''Convert a molecule saved with an older session version to use the
		current session version. This will be applied if the session is saved.'''
		from sessionVersions.v2 import atomsConvert, bondsConvert, residuesConvert
		molDict['atoms'] = atomsConvert(molDict['atoms'], oldver)
		molDict['bonds'] = bondsConvert(molDict['bonds'], oldver)
		molDict['residues'] = residuesConvert(molDict['residues'], oldver)
		return molDict

	def moleculeExpand(self, molDict):
		'''Expand the compressed attributes of the molecule.'''
		from sessionVersions.v2 import atomsExpand, bondsExpand, residuesExpand
		molDict['atoms'] = atomsExpand(molDict['atoms'])
		molDict['bonds'] = bondsExpand(molDict['bonds'])
		molDict['residues'] = residuesExpand(molDict['residues'])
		return molDict

	def modelDisplayRestore(self, model=None, targetDisplay=None):
		'Animate the display of an entire model'
		#print 'modelDisplayRestore: type(model):', type(model)
		if not hasattr(model, 'display'):
			return
		if DEBUG:
			print 'model.display:', model.display
			print 'targetDisplay:', targetDisplay
			#print id(model.display), id(targetDisplay)
		if self.frameCount == 1:
			self.modelTransitions[model] = {}
			if model.display and not targetDisplay:
				# model is displayed, but it was not when saved
				self.modelTransitions[model]['display'] = 'fade-out'
				if DEBUG:
					self.debugMessage("set model fade-out")
			elif targetDisplay and not model.display:
				# model is not displayed, but it was when saved
				self.modelTransitions[model]['display'] = 'fade-in'
				if DEBUG:
					self.debugMessage("set model fade-in")
			else:
				self.modelTransitions[model]['display'] = None
				if DEBUG:
					self.debugMessage("set model No-fade")
		if model in self.modelTransitions:
			if self.modelTransitions[model]['display'] == 'fade-out':
				if DEBUG:
					self.debugMessage("model fade-out")
				if self.frameCount == self.frames:
					# reset the display at the end of the animation, not before
					# TODO: restore opacity to saved state!
					self.ModelOpacityRestore(model, 0.0)
					model.display = False
				else:
					# decrease opacity (inverse of rate)
					self.ModelOpacityRestore(model, self.rate)
			if self.modelTransitions[model]['display'] == 'fade-in':
				if DEBUG:
					self.debugMessage("model fade-in")
				if self.frameCount == 1:
					# Display a transparent model on the first frame
					self.ModelOpacityRestore(model, 0.0)
					model.display = True
				else:
					# increase opacity
					#
					# TODO: calculate difference in opacity and multiply by rate!
					#
					#
					self.ModelOpacityRestore(model, self.rate)
			if self.frameCount == self.frames:
				self.modelTransitions[model]['display'] = None

	@classmethod
	def ModelOpacityRestore(cls, model=None, opacity=1.0):
		'Set the opacity for an entire model'
		#print 'ModelOpacityRestore:', type(model), opacity
		if not hasattr(model, 'color') or not model.color:
			# There's nothing we can modify
			return
		if isinstance(model.color, chimera.MaterialColor):
			model.color.opacity = opacity
		else:
			# Unknown color attribute
			return
		if isinstance(model, chimera.Molecule):
			# also set opacity of components (residues, atoms, bonds)
			#
			# TODO: Explore whether it's better to do all this in
			# Molecule*Restore() methods.
			#
			for atom in model.atoms:
				if atom.color:
					atom.color.opacity = model.color.opacity
			for bond in model.bonds:
				if bond.color:
					bond.color.opacity = model.color.opacity
			for r in model.residues:
				if r.fillColor:
					r.fillColor.opacity = model.color.opacity
				if r.ribbonColor:
					r.ribbonColor.opacity = model.color.opacity
		# TODO: add opacity details for volumes, etc.


	def models(self):
		'Returns a set of the model objects in the scene state'
		models = []
		for k, v in self.state.items():
			if isinstance(v, weakref.WeakKeyDictionary):
				# All the keys of this WeakKeyDictionary are models
				models.extend(v.keys())
		return set(models)

	def modelsLookup(self, models, sessionState):
		'''
		For sessionState = 'sessionSave':
			Return {model: modelID} for all Chimera models in scene state.
			Uses SimpleSession.sessionID.
		For sessionState = 'sessionRestore':
			models is a list of modelID values from SimpleSession.sessionID.
			Return {modelID: model} for all Chimera models in scene state.
			Uses SimpleSession.idLookup.
		'''
#		if DEBUG:
#			print 'SceneState.modelsLookup: ', self.name
		modelsID = {}
		if sessionState == 'sessionSave':
			from SimpleSession import sessionID
			for model in models:
				try:
					modelsID[model] = sessionID(model)
				except:
					if DEBUG:
						print 'SceneState.modelsLookup::model = ', model
					# We want this to work outside session saving
					try:
						modelsID[model] = (model.id, model.subid,
									model.__class__.__name__)
					except ValueError:
						# model is gone, just ignore
						pass
		elif sessionState == 'sessionRestore':
			# Ensure that this code is called when a session is restored.
			assert Animate.sessionRestoring
			from SimpleSession import idLookup
			for modelID in models:
				try:
					# Use SimpleSession to map modelID to a model object
					modelsID[modelID] = idLookup(modelID)
				except:
					if modelID == 'LabelsClass' or 'IlabelModel' in modelID:
						modelsID['LabelsClass'] = getLabelsModel()
					elif modelID == 'ArrowsClass' or '_ArrowsModel' in modelID:
						modelsID['ArrowsClass'] = getArrowsModel()
					elif isinstance(modelID, tuple):
						import SimpleSession
						mid, subid, className = modelID
						ref = (mid, subid)
						refModels = SimpleSession.modelMap.get(ref, [])
						mList = [ m for m in refModels
							if m.__class__.__name__ == className ]
						if len(mList) == 1:
							modelsID[modelID] = mList[0]
						elif DEBUG:
							print models
							msg = 'Cannot get model for: ', modelID
							raise chimera.error(msg)
					elif DEBUG:
						print models
						msg = 'Cannot get model for: ', modelID
						raise chimera.error(msg)
		else:
			msg = 'Unknown sessionState argument'
			chimera.replyobj.error(msg)
		return modelsID

	@classmethod
	def MoleculeSave(cls, mol=None):
		'Save state for a molecule model'
		# save all the molecule properties to be animated
		assert isinstance(mol, chimera.Molecule)
		exclusions = [
			'activeCoordSet',
			'atomsMoved', 	# read-only attribute
			'clipPlane', 	# handled by ClipsSave & clipsRestore
			'coordSets',
			'crystal_contact_models',
			'id', 			# read-only attribute
			'mol2comments',
			'mol2data',
			'multiscale_chain_data',
			'openState',
			'openedAs',
			'pdbHeaders',
			'subid', 		# read-only attribute
			'atom1',	# read-only attributes in scale bar
			'atom2',
			'label_atom',
		]
		funcDispatch = {
			#'openState': cls.OpenStateSave,
			'atoms': cls.MoleculeAtomsSave,
			'bonds': cls.MoleculeBondsSave,
			'residues': cls.MoleculeResiduesSave,
		}
		Scenes.scenes.save_obj(mol)
		molDict = cls.AttrSave(mol, exclusions, funcDispatch)
		molDict['type'] = repr(chimera.Molecule)
		#openState = chimera.openModels.openState(mol.id, mol.subid)
		molDict['active'] = mol.openState.active
		molDict['activeCoordSet.id'] = mol.activeCoordSet.id

		return molDict

	def moleculeRestore(self, model=None):
		"Restore the state of a molecule."
		if DEBUG:
			self.debugMessage('SceneState.moleculeRestore')
		# Fade out any unsaved molecules
		if model not in self.state['molecules']:
			# This could be a new molecule, not in the saved state.

			# it should be faded in here


			if DEBUG:
				print 'This molecule not in saved state'
			if self.frameCount == self.discreteFrame:
				#self.modelDisplayRestore(model, False)
				model.display = False
			return
		# Retrieve saved molecule parameters
		molDict = self.state['molecules'][model]
		self.assert_same(molDict['type'], repr(chimera.Molecule))
		# Animate the global model display (uses self.model_opacity)
		#self.modelDisplayRestore(model, molDict['display'])
		#
		if self.frameCount == self.discreteFrame:
			exclusions = [
				# If self.modelDisplayRestore is used, add:
				'display',
				'atoms', 	#: self.moleculeAtomsRestore,
				'bonds', 	#: self.moleculeBondsRestore,
				'residues', #: self.moleculeResiduesRestore,
				'color',
				'numAtoms',
				'numBonds',
				'numResidues',
			]
			self.attrRestore(model, molDict, exclusions)
			model.openState.active = molDict['active']

		# call for all frames and test frameCount in each function
		saved_mol_color = self.MaterialColorRestore(molDict['color'])
		if self.frames == 1:
			model.color = saved_mol_color
		else:
			try:
				(molecule_color, to_molecule_color) = self.molecule_color_to_interpolate[model]
				model.color = self.interpolateColor(molecule_color, None, to_molecule_color, None)
			except (KeyError, AttributeError):
				# Do nothing if not interpolating
				pass
		self.moleculeAtomsRestore(model, molDict['atoms'], saved_mol_color)
		self.moleculeBondsRestore(model, molDict['bonds'], saved_mol_color)
		self.moleculeResiduesRestore(model, molDict['residues'], saved_mol_color)
		#
		# might interpolate from endcap > sphere by
		# setting sphere radius to the starting radius
		# of the endcap and growing it to the final
		# sphere radius over N frames
		#
		# similarly for wire > stick and
		# maybe for wire | stick > ball&stick
		#
		# Animation for molecule coordinate sets.
		# Interpolations for coordinate sets will implement
		# morphing and trajectory animations (molecular dynamics)
		savCoordID = molDict['activeCoordSet.id']
		if len(model.coordSets) > 1 and self._startActiveCoordID is not None:
			initCoordID = self._startActiveCoordID[model]
			f = self.frameCount / float(self.frames)
			curCoordID = (initCoordID + int((savCoordID - initCoordID) * f))
		else:
			curCoordID = savCoordID
		if curCoordID != model.activeCoordSet.id:
			model.activeCoordSet = model.findCoordSet(curCoordID)

		# and finally
		if self.frameCount == self.frames:
			model.display = molDict['display']



	#===========================================================================
	#
	# TOO SLOW
	#
	# @classmethod
	# def MoleculeAtomsSave(cls, atoms):
	#	atomList = []
	#	for atom in atoms:
	#		atomDict = cls.AtomSave(atom)
	#		atomList.append(atomDict)
	#	return atomList
	#
	# def moleculeAtomsRestore(self, atoms, atomList):
	#	'restore display properties for atoms'
	#	for ai, atom in enumerate(atoms):
	#		atomDict = atomList[ai]
	#		self.AtomRestore(atom, atomDict)
	#===========================================================================

	@classmethod
	def MoleculeAtomsSave(cls, atoms):
		'Store atom properties for animation'
		nAtoms = len(atoms)
		# initialize atom properties
		atomDict = {}
		atomDict['color'] = [None] * nAtoms
		atomDict['display'] = [False] * nAtoms
		atomDict['drawMode'] = [0] * nAtoms
		atomDict['label'] = [None] * nAtoms
		atomDict['labelColor'] = [None] * nAtoms
		atomDict['radius'] = [0.0] * nAtoms
		atomDict['surfaceColor'] = [None] * nAtoms
		atomDict['surfaceDisplay'] = [False] * nAtoms
		atomDict['surfaceOpacity'] = [1.0] * nAtoms
		# loop through atoms to store display properties.
		for ai, atom in enumerate(atoms):
			Scenes.scenes.save_obj(atom)
			if cls.restoreVersion > 1:
				atomDict['color'][ai] = atom.color
				atomDict['labelColor'][ai] = atom.labelColor
				atomDict['surfaceColor'][ai] = atom.surfaceColor
			else:
				atomDict['color'][ai] = cls.MaterialColorSave(atom.color)
				atomDict['labelColor'][ai] = cls.MaterialColorSave(atom.labelColor)
				atomDict['surfaceColor'][ai] = cls.MaterialColorSave(atom.surfaceColor)
			atomDict['display'][ai] = cls._safe_attr(atom.display, False)
			atomDict['drawMode'][ai] = cls._safe_attr(atom.drawMode, 0)
			atomDict['label'][ai] = cls._safe_attr(atom.label, None)

			atomDict['radius'][ai] = cls._safe_attr(atom.radius, 0.0)
			atomDict['surfaceDisplay'][ai] = cls._safe_attr(atom.surfaceDisplay, False)
			atomDict['surfaceOpacity'][ai] = cls._safe_attr(atom.surfaceOpacity, -1.0)
		return atomDict

	def moleculeAtomsRestore(self, model, atomDict, defColor):
		'restore display properties for atoms'

		atoms = model.atoms
		if self.frames == 1:
			for ai, atom in enumerate(atoms):
				atom.drawMode = atomDict['drawMode'][ai]
				atom.radius = atomDict['radius'][ai]
				if self.version > 1:
					atom.color = atomDict['color'][ai]
					atom.surfaceColor = atomDict['surfaceColor'][ai]
					atom.labelColor = atomDict['labelColor'][ai]
				else:
					atom.color = self.MaterialColorRestore(atomDict['color'][ai])
					atom.surfaceColor = self.MaterialColorRestore(atomDict['surfaceColor'][ai])
					atom.labelColor = self.MaterialColorRestore(atomDict['labelColor'][ai])
				atom.surfaceOpacity = atomDict['surfaceOpacity'][ai]
				atom.display = atomDict['display'][ai]
				atom.label = atomDict['label'][ai]
				atom.surfaceDisplay = atomDict['surfaceDisplay'][ai]
			return

		# multi-frame transition; do these once
		if self.frameCount == self.discreteFrame:
			surfFade = False
			for fo_model in self.fadeOutModels:
				if isinstance(fo_model, chimera.MSMSModel) and \
					fo_model.molecule == model:
					surfFade = True
					break
			for ai, atom in enumerate(atoms):
				atom.drawMode = atomDict['drawMode'][ai]
				atom.radius = atomDict['radius'][ai]
				if model not in self.fadeOutModels and \
					atom not in self.fadeOutModels:
					atom.display = atomDict['display'][ai]
					atom.label = atomDict['label'][ai]

				# might be a surface for this molecule
				if not surfFade and atom not in self.fadeOutAtomSurfs:
					atom.surfaceDisplay = atomDict['surfaceDisplay'][ai]

		# do for each transition frame
		to_atom_color = None
		if model in self.atomColors_to_interpolate:
			for (atom, to_atom_color) in self.atomColors_to_interpolate[model]:
				atom.color = self.interpolateColor(atom.color, model.color,
					to_atom_color, defColor)
		if model in self.atomSurfColor_to_interpolate:
			for (atom, atomSurface_toColor) in self.atomSurfColor_to_interpolate[model]:
				atom.surfaceColor = self.interpolateColor(atom.surfaceColor,
					defColor, atomSurface_toColor, to_atom_color)
		if model in self.atomLabelColor_to_interpolate:
			for (atom, atomLabel_toColor) in self.atomLabelColor_to_interpolate[model]:
				atom.labelColor = self.interpolateColor(atom.labelColor,
					(atom.color or defColor), atomLabel_toColor, to_atom_color)
		if model in self.atomLabel_to_interpolate:
			for (atom, atomLabel_toColor, atomLabel) in self.atomLabel_to_interpolate[model]:
				atom.labelColor = self.interpolateColor(atom.labelColor,
					(atom.color or defColor), atomLabel_toColor, to_atom_color)
				if atomLabel:
					atom.label = atomLabel
		if model in self.surfaceOpacity_to_interpolate:
			for (atom, from_op, op_range) in self.surfaceOpacity_to_interpolate[model]:
				if atom.surfaceOpacity < 0.0:
					atom.surfaceOpacity = atom.molecule.color.opacity
				atom.surfaceOpacity = from_op + (op_range * self.frameCount / self.frames)

		if self.frameCount == self.frames:
			for ai, atom in enumerate(atoms):
				atom.display = atomDict['display'][ai]
				atom.label = atomDict['label'][ai]
				atom.surfaceOpacity = atomDict['surfaceOpacity'][ai]
				atom.surfaceDisplay = atomDict['surfaceDisplay'][ai]

	@classmethod
	def MoleculeBondsSave(cls, bonds):
		'Store bond properties for animation'
		nBonds = len(bonds)
		# initialize bond properties
		bondDict = {}
		bondDict['color'] = [None] * nBonds
		bondDict['display'] = [False] * nBonds
		bondDict['drawMode'] = [0] * nBonds
		bondDict['label'] = [None] * nBonds
		bondDict['labelColor'] = [None] * nBonds
		bondDict['radius'] = [0.0] * nBonds
		# loop through bonds to store display properties.
		for bi, bond in enumerate(bonds):
			Scenes.scenes.save_obj(bond)
			if cls.restoreVersion > 1:
				bondDict['color'][bi] = bond.color
				bondDict['labelColor'][bi] = bond.labelColor
			else:
				bondDict['color'][bi] = cls.MaterialColorSave(bond.color)
				bondDict['labelColor'][bi] = cls.MaterialColorSave(bond.labelColor)
			bondDict['display'][bi] = cls._safe_attr(bond.display, False)
			bondDict['drawMode'][bi] = cls._safe_attr(bond.drawMode, 0);
			bondDict['label'][bi] = cls._safe_attr(bond.label, u'');
			bondDict['radius'][bi] = cls._safe_attr(bond.radius, 0.0);
		return bondDict

	def moleculeBondsRestore(self, model, bondDict, defColor):
		'restore display properties for bonds'
		bonds = model.bonds
		if self.frames == 1 or self.frameCount == self.discreteFrame:
			for bi, bond in enumerate(bonds):
				bond.display = bondDict['display'][bi]
				bond.drawMode = bondDict['drawMode'][bi]
				bond.label = bondDict['label'][bi]
				bond.radius = bondDict['radius'][bi]
				if self.frames == 1:
					bond.color = bondDict['color'][bi]
					bond.labelColor = bondDict['labelColor'][bi]

		if self.frames > 1:
			if model in self.bonds_to_interpolate:
				for (bond, bond_toColor) in self.bonds_to_interpolate[model]:
					bond.color = self.interpolateColor(bond.color, model.color,
						bond_toColor, defColor)
			if model in self.bondlabels_to_interpolate:
				for (bond, bondLabel_toColor) in self.bondlabels_to_interpolate[model]:
					bond.labelColor = self.interpolateColor(bond.labelColor, model.color,
						bondLabel_toColor, defColor)

	@classmethod
	def MoleculeResiduesSave(cls, residues):
		'Store residue properties for animation'
		nRes = len(residues)
		# initialize residue properties
		resDict = {}
		resDict['fillColor'] = [None] * nRes
		resDict['fillDisplay'] = [False] * nRes
		resDict['fillMode'] = [0] * nRes
		resDict['label'] = [u''] * nRes
		resDict['labelColor'] = [None] * nRes
		#resDict['labelCoord'] = [chimera.Point()] * nRes
		resDict['labelOffset'] = [None] * nRes
		resDict['ribbonColor'] = [None] * nRes
		resDict['ribbonDisplay'] = [False] * nRes
		resDict['ribbonDrawMode'] = [0] * nRes
		resDict['ribbonStyle'] = [None] * nRes
		# loop through residues to store display properties.
		for ri, res in enumerate(residues):
			Scenes.scenes.save_obj(res)
			if cls.restoreVersion > 1:
				resDict['fillColor'][ri] = res.fillColor
				resDict['labelColor'][ri] = res.labelColor
				resDict['ribbonColor'][ri] = res.ribbonColor
			else:
				resDict['fillColor'][ri] = cls.MaterialColorSave(res.fillColor)
				resDict['labelColor'][ri] = cls.MaterialColorSave(res.labelColor)
				resDict['ribbonColor'][ri] = cls.MaterialColorSave(res.ribbonColor)
			resDict['fillDisplay'][ri] = cls._safe_attr(res.fillDisplay, False);
			resDict['fillMode'][ri] = cls._safe_attr(res.fillMode, 0)
			resDict['label'][ri] = cls._safe_attr(res.label, u'')
				# res.labelCoord is calculated from labelOffset
				#resDict['labelCoord'][ri] = res.labelCoord()
			resDict['labelOffset'][ri] = cls._safe_attr(res.labelOffset, None)
			resDict['ribbonDisplay'][ri] = cls._safe_attr(res.ribbonDisplay, False)
			resDict['ribbonDrawMode'][ri] = cls._safe_attr(res.ribbonDrawMode, 0)
			resDict['ribbonStyle'][ri] = cls.RibbonStyleSave(res.ribbonStyle)
		return resDict

	def moleculeResiduesRestore(self, model, resDict, defColor):
		'restore display properties for residues'
		residues = model.residues
		if self.frames == 1 or self.frameCount == self.discreteFrame:
			for ri, res in enumerate(residues):
				res.fillDisplay = resDict['fillDisplay'][ri]
				res.fillMode = resDict['fillMode'][ri]
				res.label = resDict['label'][ri]
				res.labelOffset = resDict['labelOffset'][ri]
				#res.ribbonDisplay = resDict['ribbonDisplay'][ri]
				res.ribbonDrawMode = resDict['ribbonDrawMode'][ri]
				res.ribbonStyle = self.ribbonStyleRestore(resDict['ribbonStyle'][ri])

				if self.frames == 1:
					res.fillColor = resDict['fillColor'][ri]
					res.labelColor = resDict['labelColor'][ri]
					res.ribbonColor = resDict['ribbonColor'][ri]

		if self.frames > 1:
			try:
				res_colors = self.res_fillColor_to_interpolate[model]
			except (AttributeError, KeyError):
				pass
			else:
				for (res, resFill_toColor) in res_colors:
					res.fillColor = self.interpolateColor(res.fillColor, model.color,
						resFill_toColor, defColor)
			try:
				res_colors = self.res_labelColor_to_interpolate[model]
			except (AttributeError, KeyError):
				pass
			else:
				for (res, resLabel_toColor) in res_colors:
					res.labelColor = self.interpolateColor(res.labelColor, model.color,
						resLabel_toColor, defColor)
			try:
				res_colors = self.res_ribbonColor_to_interpolate[model]
			except (AttributeError, KeyError):
				pass
			else:
				for (res, resRibbon_toColor) in res_colors:
					res.ribbonColor = self.interpolateColor(res.ribbonColor, model.color,
						resRibbon_toColor, defColor)

		if self.frameCount == self.frames:
			for ri, res in enumerate(residues):
				res.ribbonDisplay = resDict['ribbonDisplay'][ri]
				res.label = resDict['label'][ri]

	@classmethod
	def MSMSModelSave(cls, model=None):
		'Save state for a surface model'
		# Save surface parameters
		import copy
		surfDict = {
			'name': model.name,
			'display': model.display,
			'colorMode': model.colorMode,
			'visibilityMode': model.visibilityMode,
			'density': model.density,
			'probeRadius': model.probeRadius,
			'category': model.category,
			'allComponents': model.allComponents,
			'surface_piece_defaults':
				copy.copy(model.surface_piece_defaults),
			}
		colors = model.customRGBA
		if colors is not None:
			surfDict['vertexColors'] = colors
		return surfDict

	def MSMSModelRestore(self, model=None):
		"Restore the surface properties of the scene"
		if DEBUG:
			self.debugMessage('SceneState.MSMSModelRestore')
#		# Fade out any unsaved surfaces
#		if model not in self.state['surfaces']:
#			# This could be a new surface, not in the saved state.
#			if self.frameCount == self.discreteFrame and model not in self.fadeOutModels:
#				#self.modelDisplayRestore(model, False)
#				model.display = False
#			return

		if self.frameCount == self.frames:
			# If at last step of interpolation, copy all data from state
			colorMode = model.colorMode
			try:
				surfDict = self.state['surfaces'][model]
			except KeyError:
				model.display = False
			else:
				exclusions = [
					'vertexColors',
				]
				self.attrRestore(model, surfDict, exclusions)
				try:
					model.customRGBA = surfDict['vertexColors']
				except KeyError:
					# Must not be custom color mode
					pass
				except:
					chimera.replyobj.warning("Ignoring error restoring custom surface vertex colors")
					chimera.replyobj.reportException()
			if colorMode != model.colorMode:
				model.update_coloring()
		else:
			try:
				target = self.msms_color_to_interpolate[model]
			except KeyError:
				# Not interpolating, nothing to do
				pass
			else:
				# Go for simple RGBA interpolation for now
				source = model.customRGBA
				rgba = (1 - self.rate) * source + self.rate * target
				model.set_custom_rgba(rgba)

	@classmethod
	def OpenStateSave(cls, openState):
		d = {}
		d['active'] = openState.active
		d['type'] = 'openState'
		return d

	@classmethod
	def OpenStateRestore(cls, model, openStateDict):
		model.openState.active = openStateDict['active']

	def pickleDumpItem(self, k, v):
		try:
			s = pickle.dumps(v)
		except:
			s = ''
		return s

	def pickleLoadItem(self, k, v, tabs=''):
		try:
			data = pickle.loads(v)
			#print tabs, 'unpickled', k, v
		except:
			data = None
			#print tabs, 'cannot unpickle', k, v
		return data

	def pickleDebug(self, d, tabs=''):
		print '\n', self.name
		models = self.models()
		modelsID = self.modelsLookup(models, 'sessionSave')
		for k, v in d.items():
			if isinstance(v, weakref.WeakKeyDictionary):
				# Cannot pickle these, convert to pickle-friendly data
				v = dict(v)
				vKeys = list(v.keys())	# v.keys will change in the loop
				for model in vKeys:
					if model in models:
						modelID = modelsID[model]
						#print self.name, repr(model), ' modelID: ', modelID
						v[modelID] = v[model]
						del v[model]
			if self.pickleDumpItem(k, v):
				pass
				#print tabs, 'pickled', k
			else:
				print tabs, 'pickle failed:', k, v
				if isinstance(v, dict):
					tabs += '\t'
					self.pickleDebug(v, tabs)	# recursive
					tabs = tabs[:-1]	# remove an indent level
				break

	@classmethod
	def PlaneSave(cls, obj):
		'''Save state for chimera.Plane'''
		assert isinstance(obj, chimera.Plane)
		d = {}
		d['type'] = repr(chimera.Plane)
		d['origin'] = cls.PointSave(obj.origin)
		d['normal'] = cls.VectorSave(obj.normal)
		return d

	@classmethod
	def PlaneRestore(cls, objDict):
		'''Restore state for chimera.Plane'''
		cls.c_assert_same(objDict['type'], repr(chimera.Plane))
		plane = chimera.Plane()
		plane.origin = cls.PointRestore(objDict['origin'])
		normal = cls.VectorRestore(objDict['normal'])
		if normal.length:
			plane.normal = normal
		return plane

	@classmethod
	def PointSave(cls, point):
		'''Save a chimera.Point as an xyz tuple'''
		assert isinstance(point, chimera.Point)
		objDict = {}
		objDict['type'] = repr(chimera.Point)
		objDict['xyz'] = cls.xyzSave(point)
		return objDict

	@classmethod
	def PointRestore(cls, objDict):
		'''Create a new chimera.Point from an xyz tuple'''
		cls.c_assert_same(objDict['type'], repr(chimera.Point))
		return cls.xyzRestore(objDict['xyz'], 'point')

	@classmethod
	def PseudoBondGroupSave(cls, pbg):
		pbgDict = {}
		Scenes.scenes.save_obj(pbg)
		pbgDict['type'] = repr(chimera.PseudoBondGroup)
		pbgDict['color'] = cls.MaterialColorSave(pbg.color)
		pbgDict['display'] = cls._safe_attr(pbg.display, False)
		pbgDict['showStubBonds'] = cls._safe_attr(pbg.showStubBonds, False)
		pbgDict['lineWidth'] = cls._safe_attr(pbg.lineWidth, 0.0)
		pbgDict['stickScale'] = cls._safe_attr(pbg.stickScale, 0.0)
		pbgDict['lineType'] = cls._safe_attr(pbg.lineType, 0)
		return pbgDict

	def pseudoBondGroupRestore(self, pbg):
		if not self.state.has_key('pseudobondgroup'):
#			chimera.replyobj.warning("pseudobondgroups not saved in this scene.")
			return
		if not self.state['pseudobondgroup'].has_key(pbg):
			return
		pbgDict = self.state['pseudobondgroup'][pbg]
		s = repr(PseudoBondGroup)
		self.assert_same(pbgDict['type'], repr(PseudoBondGroup))
		pbg.color = self.MaterialColorRestore(pbgDict['color'])
		pbg.display = pbgDict['display']
		pbg.showStubBonds = pbgDict['showStubBonds']
		pbg.lineWidth = pbgDict['lineWidth']
		pbg.stickScale = pbgDict['stickScale']
		pbg.lineType = pbgDict['lineType']

	def ribbonStyleRestore(self, styleEntry):
		if styleEntry == None:
			return None
		if not isinstance(styleEntry, dict):
			chimera.replyobj.error("wrong type saved in ribbonStyleRestore")
		ribbonStyle = getattr(chimera, styleEntry['name'])(styleEntry['size'])
		return ribbonStyle

	@classmethod
	def RibbonStyleSave(cls, ribbonStyleObj):
		"If ribbon style is set, it's an object; handle it here."
		if ribbonStyleObj == None:
			return None
		rsDict = {}
		rsDict['name'] = ribbonStyleObj.__class__.__name__
		rsDict['size'] = ribbonStyleObj.size
		return rsDict

	@classmethod
	def SelectionSetSave(cls, selDict):
		'''Save a selectionSet'''
		# TODO: save a weakValueDict that refers to atom, bond, residue models
		#print selDict
		#print type(selDict)
		return {}

	@classmethod
	def SelectionSetRestore(cls, selDict):
		'''Restore a selectionSet'''
		# TODO: restore a weakValueDict
		return {}

	def stateDump(self):
		'Called by session save processing (and Scene.uniqueID)'
		models = self.models()
		modelsID = self.modelsLookup(models, 'sessionSave')
		stateDict = {}
		modelsDict = {}
		stateDict['models'] = modelsDict
		for k, v in self.state.items():
			if isinstance(v, weakref.WeakKeyDictionary):
				# Cannot pickle these, convert to pickle-friendly data
				if k in models:
					raise chimera.error('weakref key should not be a model')
				# The keys of modelsDict can be used to track items that will
				# be converted between weakKeyDictionary and dict.
				modelsDict[k] = []
				v = dict(v) # convert weakKeyDictionary to dict.
				# This loop will substitute each model object for a modelID,
				# and the modelID is generated by SimpleSession (they are
				# only available during session saving).
				vKeys = list(v.keys())	# v.keys will change in the loop
				for model in vKeys:
					if model in models:
						try:
							modelID = modelsID[model]
						except KeyError:
							# Model must have been
							# closed.  Ignore.
							continue
						modelsDict[k].append(modelID)
						# use SimpleSession here to compress v[model]
						if k == 'molecules' and self.version > 1:
							vv = self.moleculeCompress(v[model])
						else:
							vv = v[model]
						v[modelID] = vv
						del v[model]
			if self.pickleDumpItem(k, v):
				# OK, it's compatible with pickle!
				stateDict[k] = v
			else:
				print 'key:', k
				print 'value:', v
				self.pickleDebug(v)
				msg = 'Error in scene state pickle\n'
				msg += 'key: %s' % repr(k)
				#msg += 'value: %s' % repr(v)
				raise chimera.error(msg)
		return stateDict

	def stateLoad(self, stateDict):
		'Called by session restore processing'
 		# Extract pickle-tracking data and discard it from stateDict,
		# they don't form a part of the scene state proper.
		modelsDict = stateDict['models']
		del stateDict['models']
		# Resolve SimpleSession.sessionID values into restored models
		#print 'SceneState.stateLoad, before: ', modelsDict
		for k in modelsDict.keys():
			modelsID = modelsDict[k]
			#modelsDict[k] = self.modelsLookup(modelsID, 'sessionRestore')
			d = self.modelsLookup(modelsID, 'sessionRestore')
			if d:
				modelsDict[k] = d
			else:
				del modelsDict[k]
		#print 'SceneState.stateLoad, after: ', modelsDict
		state = {}
		doUpdate = False
		for k, v in stateDict.items():
			if k in modelsDict:
				modelsID = modelsDict[k]
				vKeys = list(v.keys())	# v.keys will change in the loop
				for modelID in vKeys:
					if modelID in modelsID:
						model = modelsID[modelID]
						value = v[modelID]
						if k == 'molecules':
							# molecules are compressed using SimpleSession tools
							if self.version > 1:
								value = self.moleculeExpand(value)
							else: # convert older version to this version
								value = self.moleculeConvert(value, self.version)
								doUpdate = True
						del v[modelID]
						v[model] = value
					else:
						del v[modelID]
				# Convert from dict back to weakKeyDict, so that model keys
				# and values will be released whenever a model is closed.
				try:
					v = weakref.WeakKeyDictionary(v)
				except:
					print 'SceneState.stateLoad::k = ', k
					print 'SceneState.stateLoad::v.keys() = ', v.keys()
					print 'SceneState.stateLoad::modelsDict = ', modelsDict
					raise
			state[k] = v
		# update version after old version scenes have been converted
		if doUpdate:
			self.updateSaveVersion()
		return state

	# A dictionary of the type of scene states that can be saved
	StateHandlers = {}

	@classmethod
	def StateHandlerAdd(cls, stateName, modelClass, stateSaveFunc):
		'''
		An API to add a function for saving state.
		- stateName: a string to identify the type of state saved
		- modelClass: a class object for a model class that can be saved;
		  can also be a keyword string:
		  'All' if all chimera models support the properties saved
		  by the stateSaveFunc (e.g., xforms),
		  'Independent' if the stateSaveFunc does not depend on
		  any models (e.g., lighting and camera properties)
		- stateSaveFunc: any function that can save the model state
		  and return it in a data structure that can be input to another
		  function for restoring the model to this saved state
		'''
		stateType = (stateName, modelClass)
		if stateType not in cls.StateHandlers:
			# Initialize a list of handlers for this state type;
			# only one function can register to save state
			cls.StateHandlers[stateType] = stateSaveFunc
		# TODO: define similar API to restore state?
		# TODO: Should it trigger an update to the saved state?

	@classmethod
	def StateHandlersRegister(cls):
		# Register methods for saving state that are model independent
		cls.StateHandlerAdd('view', 'Independent', cls.ViewSave)
		# Register methods for saving state that are supported by all models
		cls.StateHandlerAdd('clips', 'All', cls.ClipsSave)
		cls.StateHandlerAdd('xforms', 'All', cls.XformsSave)
		# Register methods for saving state for specific models
		cls.StateHandlerAdd('molecules', Molecule, cls.MoleculeSave)
		cls.StateHandlerAdd('surfaces', MSMSModel, cls.MSMSModelSave)
		cls.StateHandlerAdd('pseudobondgroup', PseudoBondGroup, cls.PseudoBondGroupSave)
		# TODO: Handle other models, including:
		# - surfaces (not MSMSModel surfaces)
		return cls.StateHandlers

	def stateHandlersSet(self):
		self.stateHandlers = self.StateHandlersRegister()
		if not getattr(self, 'state', None):
			self.state = {}
		# Initialize data structures to save model state properties
		for stateName, modelClass in self.stateHandlers.keys():
			if modelClass == 'Independent':
				self.state[stateName] = None
			else:
				# The keys of this dict are model instances
				# The values will be returned by a stateSaveFunc
				self.state[stateName] = weakref.WeakKeyDictionary()

	# TODO: convert self.state into a read-only property, after it is set?
	#self.state = property(getState)
	def stateSave(self):
		"Record the state of a scene"
		#
		# loop through all modelTypes
		# - model types can be extended, so we don't know in advance all the
		#   possible types to be handled.
		#modelTypes = [x.__class__ for x in chimera.openModels.list(all=True)]
		#modelTypes = list(set(modelTypes))
		#for i, t in enumerate(modelTypes):
		#	modelTypes[i] = re.findall("_chimera[.](.*)[']", str(t))[0]
		#
		self.stateHandlersSet()
		#
		# Save anything that is model independent
		for stateType, stateSaveFunc in self.stateHandlers.items():
			stateName, modelClass = stateType
			if modelClass == 'Independent':
				self.state[stateName] = stateSaveFunc()
		# get a list of all the current open models
		# include hidden models
		models = chimera.openModels.list(all=True)
		hidden = chimera.openModels.list(hidden=True)

		# skip models whose tools manage state via SCENE_TOOL_SAVE trigger.
		for model in models:
			if model in hidden and model.id >= 0 and \
				not isinstance(model, PseudoBondGroup):
				# Skip all hidden models that share a model.id with
				# a non-hidden model (these are automatically managed);
				# other hidden models have model.id < 0 and they include
				# PseudoBondGroup, etc.
				continue
			# Find all registered functions that can save state for model.
			for stateType, stateSaveFunc in self.stateHandlers.items():
				stateName, modelClass = stateType
				if modelClass == 'Independent':
					continue
				elif modelClass == 'All':
					# e.g.: ClipsSave, XformsSave
					self.state[stateName][model] = stateSaveFunc(model)
				elif isinstance(model, modelClass):
					self.state[stateName][model] = stateSaveFunc(model)

		# handle cases where only partial save occurred. save fail types
		# so they are not reported more than once per chimera session.
		errs = self.__class__._pickle_errs
		if errs:
			for e in errs:
				if e not in self.__class__._ignore_errs:
					self._pickle_errs.append(e)
					self.__class__._ignore_errs.append(e)
			self.__class__._pickle_errs = []

	def stateRestore(self):
		'Restore a single frame in a transition to restore a scene'
		# TODO: Generate a set of models that are not in the saved state
		#	   and handle them first?
		if DEBUG:
			msg = 'SceneState.stateRestore (%s)' % self.name
			self.debugMessage(msg)
		import Ilabel
		from Ilabel import Arrows
		for model in chimera.openModels.list(all=True):
			#
			# TODO: include options to transform only spatial, color, etc.
			#
			if isinstance(model, chimera.Molecule) and \
			('molecules' in self.properties or 'all' in self.properties):
				self.moleculeRestore(model)
			elif isinstance(model, chimera.MSMSModel) and \
			('surfaces' in self.properties or 'all' in self.properties):
				self.MSMSModelRestore(model)
			elif isinstance(model, PseudoBondGroup) and \
				('pseudobondgroups' in self.properties or 'all' in self.properties):
				self.pseudoBondGroupRestore(model)
		# TODO: other model state, etc.
		if 'view' in self.properties or 'all' in self.properties:
			self.viewRestore()
		if 'clips' in self.properties or 'all' in self.properties:
			self.clipsRestore()
		if 'xforms' in self.properties or 'all' in self.properties:
			self.xformsRestore()

		if self.frameCount == self.frames:
			self.stateRestoreComplete()



	def updateSaveVersion(self):
		self.version = SceneState._current_version
		SceneState.restoreVersion = self.version

	@classmethod
	def VectorSave(cls, vector):
		'''Save a chimera.Vector as an xyz tuple'''
		assert isinstance(vector, chimera.Vector)
		objDict = {}
		objDict['type'] = repr(chimera.Vector)
		objDict['xyz'] = cls.xyzSave(vector)
		return objDict

	@classmethod
	def VectorRestore(cls, objDict):
		'''Create a new chimera.Vector from an xyz tuple'''
		cls.c_assert_same(objDict['type'], repr(chimera.Vector))
		return cls.xyzRestore(objDict['xyz'], 'vector')

	@classmethod
	def ViewSave(cls):
		'Save state for view parameters (model independent)'
		view = {}
		method = chimera.openModels.cofrMethod
		try:
			center = chimera.openModels.cofr
			if center is None:
				center = chimera.Point(0, 0, 0)
		except ValueError:
			center = chimera.Point(0, 0, 0)
		view['center'] = cls.CenterOfRotationSave(method, center)
		view['camera'] = cls.CameraSave(chimera.viewer.camera)
		view['viewer'] = cls.ViewerSave(chimera.viewer)
		return view

	def viewRestore(self):
		"Restore the view properties of the scene"
		# It's important to restore in this order:
		self.centerOfRotationRestore()
		self.viewerRestore()
		camDict = self.state['view']['camera']
		self.cameraRestore(camDict)

	@classmethod
	def ViewerSave(cls, viewer):
		'Save state for viewer parameters (model independent)'
		exclusions = [
			'backgroundImage', # PIL object
			'backgroundGradient', # (< _chimera.Texture object at 0x2a015f8 > , 128, 0.0, 0.0)
			'backgroundLens', # < _chimera.Lens object at 0x2214148 >
			'pixelScale',
			'camera',
			#'selectionSet',
		]
		funcDispatch = {
			'selectionSet': cls.SelectionSetSave,
		}
		viewerDict = cls.AttrSave(viewer, exclusions, funcDispatch)
		return viewerDict

	def viewerRestore(self):
		"Restore the viewer properties of the scene"
		if DEBUG:
			self.debugMessage('SceneState.viewerRestore')
		# Get the current viewer
		viewer = chimera.viewer
		# saved viewer properties
		sc_view = self.state['view']
		sc_viewer = sc_view['viewer']
		sc_viewSize = sc_viewer['viewSize']
		sc_scaleFactor = sc_viewer['scaleFactor']
		if self.frameCount == self.frames:
			exclusions = [
				'camera', # should be excluded in ViewerSave
				'backgroundLens', # not writable
				'showPlaneModel', # Only required for GUI mouse mode
				'selectionSet', # not writable
				'windowOrigin', # not writable
			]
			funcDispatch = {
				'selectionSet': self.SelectionSetRestore,
			}
			#self.attrRestore(viewer, sc_viewer, exclusions)
			self.attrRestore(viewer, sc_viewer, exclusions, funcDispatch)
			viewer.setViewSizeAndScaleFactor(sc_viewSize, sc_scaleFactor)
			return
		#
		# Animation for view parameters
		#
		# Greg Couch: None of the lighting values seem particularly important
		# to animate initially, but could be useful for the advanced animator.
		# For the Effects tool, the depth cueing, silhouettes, and show shadows
		# settings would be useful; for the Lighting tool, the lighting mode, 
		# the brightness and contrast, and the light directions, and the 
		# material shininess (sharpness and reflectivity) settings would be
		# useful. For the Background preferences, the method, color, gradient,
		# and image settings would be useful, especially the opacity of the
		# gradient and image, but images don't pickle, so I'd skip images
		# until round 2 if you add it at all.
		#
		#
		# This interpolation function is used in map calls below
		interp = lambda i, j: i + (j - i) * self.rate
		# Viewer properties
		scaleFactor = viewer.scaleFactor
		scaleFactor += (sc_scaleFactor - scaleFactor) * self.rate
		viewSize = viewer.viewSize
		viewSize += (sc_viewSize - viewSize) * self.rate
		viewer.setViewSizeAndScaleFactor(viewSize, scaleFactor)
		# Camera: global clipping planes
		if viewer.clipping or sc_viewer.has_key('clipping'):
			viewer.clipping = True
		# Don't do: viewer.clipping = sc_viewer['clipping']
		# wait until self.frameCount == self.frames (see above)

	@classmethod
	def XformsSave(cls, model=None):
		'Save state for model spatial transforms'
		xform = chimera.openModels.openState(model.id, model.subid).xform
		return repr(xform)

	def xformsRestore(self):
		'Restore the spatial transform of a model'
		if DEBUG:
			self.debugMessage('SceneState.xformsRestore')
		# Note that xforms index by 'model'.
		# Ensure we skip models that no longer exist.
		xforms = self.state['xforms']
		openModels = chimera.openModels.list(all=True)
		xformModels = [m for m in xforms.keys() if m in openModels]
		# Remove references to any missing models, to release them to GC.
		for m in xforms.keys():
			if m not in xformModels:
				del xforms[m]
		# Transform the xforms into a format that is compatible with
		# chimera.openModels.openState.  The rationale for this is that
		# model instances are unique for every model, whereas model.id and
		# model.subid are changed as models are opened or closed.  If we only
		# rely on model.id/model.subid, we cannot be confident that saved scene
		# data actually belongs to a specific, unique model.
		tmp = {}
		for model, xform in xforms.items():
			tmp[(model.id, model.subid)] = eval(xform)
		xforms = tmp
		# Getting a handle on the open models
		om = chimera.openModels
		#
		# DLW: Don't believe we need this section on aligning 'new' models 
		# to the lowest model ID.  Any models that are not in the saved state
		# can disappear or fade out.
		#
		# have currently open models not in the position keep their
		# orientation relative to the lowest open model...
		#missing = []
		#fromXF = toXF = lowID = None
		#for molID in om.listIds():
		#	if molID in xforms:
		#		if lowID == None or molID < lowID:
		#		   lowID = molID
		#			fromXF = om.openState(*molID).xform
		#			toXF = xforms[molID]
		#	else:
		#		missing.append(molID)
		#if missing and fromXF:
		#	for molID in missing:
		#		xf = om.openState(*molID).xform
		#		xf.multiply(fromXF.inverse())
		#		xf.multiply(toXF)
		#		xforms[molID] = xf
		#
		if self.frameCount == self.frames:
			# make sure we finish
			# (should be the same as setting the rate to 1)
			for molId, xf in xforms.items():
				om.openState(*molId).xform = xf
			return
		# Animation for spatial transforms
		from chimera import openModels
		osxf = dict()
		for molId, xf in xforms.items():
			try:
				osxf[openModels.openState(*molId)] = xf
			except ValueError:
				# model is gone, just ignore
				pass
		Midas.interpolateOpenStates(osxf, self.rate)

	# Keep a set of vector.data() objects; this might optimize memory, but only
	# so far as the objects it contains are referenced in scene data, otherwise
	# it might prevent garbage collection by keeping 1 reference to them.
	vectors = {}
	@classmethod
	def xyzSave(cls, vector):
		'Return an XYZ tuple from chimera.Vector.data() or chimera.Point.data()'
		if isinstance(vector, (chimera.Vector, chimera.Point)):
			# chimera.Vector.data() returns an xyz tuple
			# chimera.Point.data() returns an xyz tuple
			xyz = vector.data()
		else:
			xyz = None
		# Try to optimize the number of vector objects in the state
		if xyz in cls.vectors:
			xyz = cls.vectors.get(xyz)
		else:
			cls.vectors[xyz] = xyz
		return xyz

	@classmethod
	def xyzRestore(cls, xyz, type):
		'''Create a new chimera.Vector or chimera.Point
		from an xyz tuple or list of length 3, the type
		is either 'point' or 'vector'.'''
		if isinstance(xyz, (tuple, list)) and len(xyz) == 3:
			xyz = tuple(xyz)
		else:
			return
		if type == 'point':
			return chimera.Point(*xyz)
		if type == 'vector':
			return chimera.Vector(*xyz)

	def triggerIn(self, trigger=None, funcData=None, trigData=None):
		'Generic trigger handler for scene state'
		if DEBUG:
			print
			print 'SceneState.triggerIn:', trigger, funcData, trigData
		if trigger == 'transition_frame':
			self.frames = trigData['frames']
			self.frameCount = trigData['frameCount']
			self.discreteFrame = trigData['discreteFrame']
			self.rate = trigData['rate']
			self.properties = trigData['properties']
#			if self.frameCount == 1:
#				self._startActiveCoordID = dict()
#				for model in chimera.openModels.list(modelTypes=[Molecule]):
#					self._startActiveCoordID[model] = model.activeCoordSet.id
			self.stateRestore()
#			if self.frameCount == self.frames:
#				del self._startActiveCoordID

		'''determine what atoms and bonds actually need per frame property
		transtions and save them for use for all frames in this transtion.'''

	def loadTrajectories(self):
		for model in self.state['molecules']:
			model.loadAllFrames()

# Call some class methods to initialize class attributes
SceneState.StateHandlersRegister()
