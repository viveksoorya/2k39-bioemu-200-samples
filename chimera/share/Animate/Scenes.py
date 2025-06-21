# --- UCSF Chimera Copyright ---
# Copyright (c) 2006 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---

from collections import OrderedDict

import weakref

import chimera
import Animate
import Scenes
from Scene import Scene

DEBUG = 0

from chimera import SCENE_TOOL_SAVE, SCENE_TOOL_RESTORE

class Scenes(object):
	'''
	An ordered dictionary of scenes:
	  - keys are unique names for a scene (string values)
	  - values are instance objects of Scene
	There is a 'triggerset' with two triggers for adding or deleting
	scenes, named 'scene_append' and 'scene_remove', respectively.  These are 
	handled in the GUI.
	'''

	@property
	def imgSize(self):
		return Scene.imgSize
	@imgSize.setter
	def imgSize(self, size):
		Scene.imgSize = size
		for sc in self._scDict.keys():
			self.triggerOut('scene_update', sc)
	@imgSize.deleter
	def imgSize(self):
		raise AttributeError('cannot delete')


	def __init__(self):
		self._scDict = OrderedDict()
		# Keep track of the scene display state; see show method
		self.display = None
		# Default frames and mode for scene transitions
		self.FRAMES = 1

		# track objects with id's to support extensions managing their attributes.
		self._id_map = weakref.WeakValueDictionary()
		self._mol_map = weakref.WeakKeyDictionary()
		self._res_map = weakref.WeakKeyDictionary()
		self._atm_map = weakref.WeakKeyDictionary()
		self._bnd_map = weakref.WeakKeyDictionary()
		self._pbg_map = weakref.WeakKeyDictionary()
		self._new_obj_id = 99
		# types which are mapped to IDs for tool support
		self.map_objs = {
			chimera.Atom: 'Atom',
			chimera.Residue: 'Residue',
			chimera.Bond: 'Bond',
			chimera.Molecule: 'Molecule',
			chimera.PseudoBondGroup: 'PseudoBondGroup'
		}
		self._o_maps = {
			'Atom': self._atm_map,
			'Residue': self._res_map,
			'Bond': self._bnd_map,
			'Molecule': self._mol_map,
			'PseudoBondGroup': self._pbg_map
		}
		self.sess_ver = 1 # support for backward compatibility

		self.MODE = 'linear'
		self.triggerInit()

	def __len__(self):
		return len(self._scDict)

	def __str__(self):
		return str(self._scDict)

	#
	# Pickle methods
	#
	def __getstate__(self):
		# Let the pickle call occur in Session.py, not here.
		# Convert the OrderedDict to a regular dict; it will contain
		# scene instances, which will respond to pickle with their own
		# __getstate__ method.
		pickleDict = dict(self._scDict)
		# The 'session' scene is automatically generated at the end of any
		# session restore process (see Session.py for details).  It is not
		# to be saved in any session files.
		pickleDict.pop('session', None)
		# save the obj <=> id maps
		from SimpleSession import sessionID
		map_ids = {}
		for k, v in self._id_map.items():
			try:
				map_ids[k] = sessionID(v)
			except: # this id is no longer valid due to a closed model
				pass
		pickleDict['map_ids'] = map_ids
		return pickleDict

	def __setstate__(self, pickleDict):
		# pickleDict is already unpickled. restore id_map to scenes.
		self.__init__()
		for name, sc in pickleDict.items():
			if name == 'map_ids':
				from SimpleSession import idLookup
				for k, v in sc.items():
					obj = idLookup(v)
					(trigName, objmap) = self.obj_type(obj)
					self._id_map[k] = obj
					objmap[obj] = k
					if k > self._new_obj_id:
						self._new_obj_id = k
				continue

			self._scHandlers(sc, 'add')
			if not hasattr(sc, 'dispname'):
				# older session type
				sc.dispname = name
			self._scDict[sc.name] = sc
			self.triggerOut('scene_append', sc)
			#msg = 'Created state for scene "%s"' % sc.name
			#self.status(msg)

	def restoreMaps(self, other):
		self._id_map = other._id_map
		self._new_obj_id = other._new_obj_id
		self._mol_map = other._mol_map
		self._res_map = other._res_map
		self._atm_map = other._atm_map
		self._bnd_map = other._bnd_map
		self._pbg_map = other._pbg_map
		self._o_maps = {
			'Atom': self._atm_map,
			'Residue': self._res_map,
			'Bond': self._bnd_map,
			'Molecule': self._mol_map,
			'PseudoBondGroup': self._pbg_map
		}

	def restoreScene(self, other, name):
		sc = other.getScene_by_name(name)
		other._scHandlers(sc, 'delete')
		self._scSet(sc)
		self.triggerOut('scene_append', sc)

	def _scCreate(self, name, description=''):
		'''create a new scene'''
		sc = Scene(name, name, description)
		return self._scSet(sc)

	def _scReplace(self, old_sc, description=''):
		'''create a new scene for the current models but use the old scene's
		name and place in _scDict.'''
		sc = Scene(old_sc.name, old_sc.dispname, description)
		sc.name = old_sc.name
#		old_sc.destroy()
		self._scSet(sc)
		return sc

	def _scSet(self, sc):
		if sc:
			self._scHandlers(sc, 'add')
			self._scDict[sc.name] = sc
		return sc

	def _scHandlers(self, sc, action):
		trigName = 'scene_invalid'
		if action == 'add':
			trigArgs = (trigName, self.triggerIn, None)
			h = sc.triggerset.addHandler(*trigArgs)
			self.triggerHandlers[sc] = (trigName, h)
			sc.addedToScenes()
		if action == 'delete':
			sc.triggerset.deleteHandler(*self.triggerHandlers[sc])
			del self.triggerHandlers[sc]
			sc.removedFromScenes()

	def add_obj_handler(self, obj):
		# ensure a handler for the type destructor trigger
		trigName = self.obj_type(obj)[0]
		if not trigName:
			err = "unknown object type for scenes id save: " + repr(obj)
			chimera.replyobj.error(err)
		if not chimera.triggers.hasTrigger(trigName):
			h = chimera.triggers.addHandler(trigName, self.obj_trigger, None)
			self.triggerHandlers[trigName] = h

	def append(self, name=None, description=''):
		'''
		Append a named scene.
		- name is an arbitrary, unique name for a scene; if the named 
		  scene exists, it is updated.
		- activates the 'scene_append' trigger, passing 'name'.
		'''
		sc = self.getScene_by_dispname(name)
		if sc:
			self.update(sc.name, description)
		else:
			if name is None:
				name = self.getNewName()
			sc = self._scCreate(name, description)
			self.triggerOut('scene_append', sc)
		chimera.triggers.activateTrigger(SCENE_TOOL_SAVE, sc)
		#msg = 'Created state for scene "%s"' % name
		#self.status(msg)
		return sc

	def clear(self):
		'Remove all scenes'
		for name in self.names():
			self.remove(name)

	def del_obj(self, obj):
		'Drop an object from the obj-id maps.'
		(oType, objmap) = self.obj_type(obj)
		if not oType or not objmap:
			return
		oid = objmap[obj]
		del objmap[obj]
		del self._id_map[oid]

	def del_obj_handler(self, trigName):
		chimera.triggers.deleteHandler(trigName, self.triggerHandlers[trigName])

	def destroy(self):
		self.modelHandlers('delete')

	def dispnames(self):
		'''tuple of display names for scenes.'''
		return ([sc.dispname for sc in self._scDict.values()])

	@property
	def entries(self):
		return self._scDict.values()

	def get_id_by_obj(self, obj):
		self.add_obj_handler(obj)
		(otype, objmap) = self.obj_type(obj)
		return objmap.get(obj, None)

	def get_obj_by_id(self, id):
		return self._id_map.get(id)

	def getScene_by_dispname(self, dispname):
		'''lookup scene by display name.'''
		# could use a managed lookup dict.
		for scene in self._scDict.values():
			if scene.dispname == dispname:
				return scene
		return None

	def getScene_by_name(self, name):
		return self._scDict.get(name, None)

	def getNewName(self):
		n = len(self) + 1
		name = '%s%d' % (self.prefix, n)
		while name in self.names():
			n += 1
			name = '%s%d' % (self.prefix, n)
		return name

	def integrity(self, trigger=None, closedModels=None):
		'Verify that scene data refers to open models, returns bool'
		# when this method is triggered by chimera.openModels.addRemoveHandler()
		# the trigData contains a list of 'closedModels' that are about to be
		# destroyed, which will not happen until all trigger handlers return.
		# It's not possible to undo the model changes here,
		# so this method triggers cleanup of the saved state.  The trigger
		# is handled in Scenes.py and it removes the scene, which has a 
		# cascade to remove keyframes and associated GUI elements.  If 
		# this class stored the entire state (with copy.deepcopy or pickle),
		# this integrity check and cascade may not be required.
		#
		# TODO: How many triggers are related to closing models?
		# Should we handle any additional triggers - like "delete solvent"?
		#
		valid = True
		if not self:	# We have no scenes.
			return valid
		if closedModels is None:
			return valid
		# Check all the scenes for any model data that is about to be removed,
		# which will orphan the data stored in the scenes.
		closedSceneModels = {}
		for m in closedModels:
			# check if this closed model is in any scene states
			closedSceneModels[m] = set()
			for name in self.names():
				sc = self._scDict[name]
				# Check for scene integrity, which will
				# add a watermark to an invalid scene.
				if sc.integrity(m):
					closedSceneModels[m].add(name)
					valid = False
		if valid:
			return valid
		# Create information about removed models in scenes
		warnings = ''
		for m in closedModels:
			names = closedSceneModels[m]
			sceneNames = self.dispnames_by_id(names)
			warnings += "Model %s, #%d, " % (m.name, m.id)
			warnings += "is in scenes: "
			warnings += ', '.join(sorted(sceneNames))
			warnings += '.\n\n'
		#
		if DEBUG:
			print 'Scenes.integrity: \n'
			print warnings
		if trigger == 'removeModel' and not valid:
			## Remove all the invalid scenes
			#for sceneName in closedSceneModels:
			#	self.remove(sceneName)
			# Add a watermark to all the invalid scenes
			sceneNames = set()
			for m in closedModels:
				sceneNames.update(closedSceneModels[m])
				self.del_obj(m)
			for sceneName in sceneNames:
				sc = self.getScene_by_name(sceneName)
				sc.markOrphan()
#			msg = 'Orphaned state for scenes:'
#			msg += '\n' * 2
#			msg += warnings
#			#msg += 'All orphaned scenes were removed.\n'
#			msg += 'All orphaned scenes are marked.\n'
#			msg += 'Those scenes may not work as expected.\n'
#			msg += 'They might be partially recovered by first\n'
#			msg += 'restoring them and then updating the scene.'
#			msg += '\n' * 2
#			chimera.replyobj.warning(msg)
		return valid

	def modelHandlers(self, action):
		'model trigger handlers'
		if action == 'add':
			# Catch program closing a model
			h = chimera.openModels.addRemoveHandler(self.triggerIn, None)
			self.triggerHandlers['openModelsRemove'] = h
		if action == 'delete':
			h = self.triggerHandlers['openModelsRemove']
			chimera.openModels.deleteRemoveHandler(h)
			for trigName in self.map_objs.values():
				if chimera.triggers.hasTrigger(trigName):
					if self.triggerHandlers.has_key(trigName):
						h = self.triggerHandlers[trigName]
						chimera.triggers.deleteHandler(trigName, h)
			self.triggerHandlers = None

	def dispnames_by_id(self, nameList):
		return [self._scDict[name].dispname for name in nameList]

	def new_id(self):
		self._new_obj_id += 1
		return self._new_obj_id

	def obj_trigger(self, trigger=None, funcData=None, trigData=None):
		'Check whether an object(s) has been deleted. If so, del from obj maps.'
		if trigData.deleted:
			for obj in trigData.deleted:
				try:
					self.del_obj(obj)
				except:
					chimera.replyobj.warning("object not mapped in scenes: " + repr(obj))
		# check if map is empty now
		try:
			objmap = self._o_maps[trigger]
		except TypeError:
			chimera.replyobj.error('invalid scene object trigger: ' + trigger)
		if len(objmap) == 0:
			self.del_obj_handler(trigger)

	def obj_type(self, obj):
		'Return the name for triggers and map used for this type.'
		for objtype in self.map_objs.keys():
			if isinstance(obj, objtype):
				name = self.map_objs[objtype]
				objmap = self._o_maps[name]
				return (name, objmap)
		if DEBUG:
			print "Unknown type being mapped in scenes: " + repr(obj)
		return (None, None)

	@property
	def prefix(self):
		import Preferences
		pref = Preferences.get()
		return pref['scene_name']

	def remove(self, name='default'):
		'''
		Remove a named scene frame from the dictionary
		- input:
			'name' is a string identifier for an existing scene
		- activates the 'scene_remove' trigger, passing 'name'
		'''
		import Keyframes
		msg = Keyframes.keyframes.okay_to_delete_scene(name)
		if msg:
			chimera.replyobj.error(msg)
			return
		sc = self._scDict[name]
		self._scHandlers(sc, 'delete')
		del self._scDict[name]
		# Allow the system to respond before the scene is destroyed.  This
		# call must occur after removing the scene from _scDict.
		self.triggerOut('scene_remove', sc)
		sc.destroy()
		#self.status()
		if DEBUG:
			import sys
			REFS = sys.getrefcount(sc)
			ID = id(sc)
			print 'Scenes.remove: name=%s, id=%d, refs=%d\n' % (name, ID, REFS)

	def show(self, name='default', frames=1, mode='linear', properties=['all']):
		'''
		Restore the state of a scene.
		- frames (int): specify how many transition steps to interpolate
				  between the current display and the saved scene state.
		- mode (str): interpolation method can be:
				  'geometric' | 'halfstep' | 'linear' (default)
		- properties (list): types of properties to restore, including:
				  'all', 'molecule', 'position', 'surface', 'view'.
		'''
		sc = self._scDict[name]
		if sc.display(frames, mode, properties):
			msg = 'Viewing scene "%s".' % sc.name
			self.status(msg)
			self.display = name
			self.triggerOut('scene_display', sc)
		else:
			msg = 'Failed to display "%s" scene.' % name
			self.status(msg)

	def save_obj(self, obj):
		'''put this object in the map if not already there. 
		add a destructor handler if needed.'''
		oid = self.get_id_by_obj(obj)
		if not oid:
			oid = self.new_id()
			(otype, objmap) = self.obj_type(obj)
			self._id_map[oid] = obj
			objmap[obj] = oid
			obj._oid = oid

	def status(self, msg=None, **kw):
		'List the names of all scene frames on the status bar'
		if 'log' not in kw:
			kw['log'] = True
		if msg is None:
			if len(self):
				msg = 'Scenes: ' + ', '.join(self.dispnames())
			else:
				msg = 'No scenes'
		if not msg.endswith('\n'):
			msg += '\n'
		Animate.status('%s' % msg, **kw)

	def names(self):
		'''invariant key to _scDict. dispnames can be modified but are not keys.'''
		return (self._scDict.keys())

	def exists(self, name):
		return name in self._scDict

	def update(self, name, description=''):
		'''
		Update a named scene
		name: a string identifier for an existing scene
		- activates the 'scene_update' trigger, passing tuple(name)
		'''
		if self.validate(name):
			msg = 'updating state for scene "%s"' % name
			self.status(msg)
			# Reassign the name, without using self.remove(name), to 
			# keep it's place in _scDict.keys() and to avoid removing
			# any keyframes that link to this scene (they should respond
			# to the scene_update trigger.
			old_sc = self._scDict[name]
			sc = self._scReplace(old_sc, description)
			self.triggerOut('scene_update', sc)
			self.status()
			# remove triggers from the old scene after reassigning the name
			# and updating keyframes.
			for trigger in old_sc.triggers:
				old_sc.triggerset.deleteTrigger(trigger)
			chimera.triggers.activateTrigger(SCENE_TOOL_SAVE, sc)
			return True
		return False

	def update_properties(self, name, propDict):
		scene = self._scDict[name]
		for prop in propDict:
			if hasattr(scene, prop):
				setattr(scene, prop, propDict[prop])
		self.triggerOut('scene_display', scene)
		self.triggerOut('scene_update', scene)

	def triggerInit(self):
		# Track trigger handlers
		self.triggerHandlers = {}
		self.modelHandlers('add')
		# These triggers are handled in GUI displays
		self.triggerset = chimera.triggerSet.TriggerSet()
		self.triggers = [
			'scene_append', 'scene_display',
			'scene_remove', 'scene_update', 'scene_invalid']
		for trigger in self.triggers:
			self.triggerset.addTrigger(trigger, self.triggerTracking)


	def triggerIn(self, trigger=None, funcData=None, trigData=None):
		'Handle triggers for scenes'
		if DEBUG:
			print 'Scenes.triggerIn: ', trigger, funcData, trigData
		if trigger == 'removeModel':
			self.integrity(trigger, trigData)
		elif trigger == 'scene_invalid':
			# After discussion, we decided to leave these objects, but
			# "mark" them as invalid (orphaned) instances.
			#self.remove(name)
			self.triggerOut('scene_invalid', trigData)
		elif trigger == Animate.SCENE_TOOL_SAVE:
			print "debug: scene tool save", repr(trigData)
		elif trigger == Animate.SCENE_TOOL_RESTORE:
			print "debug: scene tool restore", repr(trigData)
		if DEBUG:
			print 'Scenes.triggerIn:', trigger, funcData, trigData

	def triggerOut(self, trigger=None, name=None):
		'''
		Activate a scene trigger, by its name
		- inputs:
		  trigger=<trigger_name>: the name of a trigger to activate
		  name=<scene_name>: the name of a scene
		- with no input arguments, it prints the trigger names and
		  any handlers already registered for each trigger
		- with a valid trigger name, it activates that trigger
		  and passes the <name> to the handler (as triggerData).
		- echoes a chimera error if the <trigger_name> is invalid
		'''
		if not trigger:
			# print the list of trigger names
			trigger_names = self.triggerset.triggerNames()
			print 'Scene triggers: %s' % trigger_names
			for n in trigger_names:
				print 'Trigger handlers for "%s": ' % n
				print self.triggerset.triggerHandlers(n)
		else:
			if trigger not in self.triggers:
				error = 'No trigger named "%s"' % trigger
				chimera.replyobj.error(error)
			self.triggerset.activateTrigger(trigger, name)

	def triggerTracking(self, trigger, *args):
		if DEBUG:
			h = self.triggerset.triggerHandlers(trigger)
			print 'Scenes.triggerTracking: %s = %s\n' % (trigger, repr(h))

	def validate(self, name):
		'Verify that a named scene has been defined'
		if name in self.names():
			return True
		#elif name == 'default':
		#	chimera.viewer.resetView()
		#	Midas.window('#')
		#	Midas.uncofr()
		#	self.append(name)
		#	msg = 'Viewing "default" scene (added to scenes).'
		#	self.status(msg)
		#	return True
		else:
			self.status()
			warn = 'No scene id "%s"' % name
			chimera.replyobj.warning(warn)
			return False

	def write(self, name='default'):
		'Write a scene to the file system'
		#
		# TODO: Look at using ZODB
		# http://www.zodb.org/documentation/tutorial.html
		#
		sc = self.getScene_by_dispname(name)
		sc.save()

scenes = Scenes()

import Tkinter as Tk
class OrphanDialog(chimera.baseDialog.AskYesNoDialog):
	"""Class for asking a yes/no question (modally), with a pref option"""

	def __init__(self, text, justify='left', icon=None, **kw):
		"""'text' should be the question being asked"""
		self.show_dialog = Tk.IntVar()
		chimera.baseDialog.AskYesNoDialog.__init__(self, text, justify, icon, **kw)

	def fillInUI(self, parent):
		chimera.baseDialog.AskYesNoDialog.fillInUI(self, parent)
		self.dialog_pref = Tk.Checkbutton(parent,
			text="Don't show this dialog again (can be re-enabled in Preferences)",
			onvalue=True, offvalue=False, variable=self.show_dialog)
		self.dialog_pref.pack(fill=Tk.BOTH, expand=Tk.TRUE, padx=4, pady=4)
		self.reconfig = True

	def showDialogOption(self):
		'''f the user checked the "don't show" box it means they want the 
		show dialog flag set to false.'''
		return not self.show_dialog.get()

