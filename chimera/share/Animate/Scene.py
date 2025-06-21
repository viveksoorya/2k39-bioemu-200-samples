# --- UCSF Chimera Copyright ---
# Copyright (c) 2006 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---

import cPickle as pickle
import hashlib

import chimera
from SceneImage import SceneImage
import Scenes
import Transitions
from . import addChanged

DEBUG = 0

# For thumb-nail image support
def getImgSizePref():
	from Animate import Preferences
	pref = Preferences.get()
	return pref['scene_imgSize']

def setImgSizePref(size):
	from Animate import Preferences
	pref = Preferences.get()
	pref['scene_imgSize'] = size


class Scene(object):

	#
	# Track instances
	#
	instances = set()

	@classmethod
	def instancesAdd(cls, instance):
		'''Add instance to cls.instances set'''
		cls.instances.add(instance)

	@classmethod
	def instancesRemove(cls, instance):
		'''Remove instance from cls.instances set'''
		cls.instances.remove(instance)

	@classmethod
	def instancesUpdate(cls, attr):
		'''Update attr on all class instances'''
		for instance in cls.instances:
			if attr == 'imgSize':
				# The instance .img attribute is managed by a decorator, so
				# this will call SceneImage.__set__() which will resample a
				# full-size image to the required size.
				instance.img = 'thumbnail'

	#
	# All scenes have the same size for their thumb-nail image
	#
	# Initialise the image size from preferences.
	_imgSize = None # getImgSizePref()
	# This class method will encapsulate changes to the image size
	# of the class and update all the instance images.
	@classmethod
	def _imgSizeSet(cls, size):
		cls._imgSize = size
		cls.instancesUpdate('imgSize')
		addChanged("scenes")

	# Provide a convenience property for the imgSize, which is really
	# a class attribute that will change all the class instances.
	@property
	def imgSize(self):
		'''imgSize = (x,y)
		get/set the size of image thumb-nails for all scenes.
		All scenes have the same size image thumb-nail.
		'''
		return self._imgSize
	@imgSize.setter
	def imgSize(self, size):
		if len(size) == 2:
			x = int(size[0])
			y = int(size[1])
			size = (x, y)
			if self._imgSize != size:
				# Call the classmethod to ensure it sets the
				# class _imgSize attribute (not the instance).
				self._imgSizeSet(size)
		else:
			raise AttributeError('Scene.imgSize = (x,y)')

	# The SceneImage() descriptor manages scene images.
	# In SceneImage.__get__, Scene class is the owner.
	img = SceneImage()

	def __init__(self, name='default', dispname='', description='', notes=''):
		'''
		Create a named scene frame.
		- 'name' is an arbitrary string, it is used to identify or
		  reference the scene
		- 'description' is an arbitrary string (of any length)
		- 'notes' is an arbitrary string (of any length)
		'''
		# Validate name
		self._inScenes = False
		if not self._imgSize:
			self.imgSize = getImgSizePref()
		if name == '':
			error = 'Cannot create a scene with an empty name'
			chimera.replyobj.error(error)
			del self
			return None
		# Add trigger handlers
		self.triggerInit()
		# Initialize instance attributes
		self.name = name.strip()
		self.dispname = dispname.strip()
		self.description = description
		self.notes = notes
		self.ratingMax = 4
		self.rating = 1		# calls property fset
		self.tool_settings = {} # managed by tools
		# Display attributes
		#self.trans = None		# calls property fset
		self.img = 'thumbnail'	# calls SceneImage.__set__
		# Track the 'validity' of scene state data
		self.valid = True
		# Create a unique ID using md5 hash of self.state
		self.instancesAdd(self)	 # track this instance
		self.state = self._saveState()
		self.saveStateVer = 2 # helpful for tools tracking older sessions

	# Testing methods for pickle
	# http://docs.python.org/library/pickle.html
	# See 11.1.5. The pickle protocol
	# If a class defines both __getstate__() and __setstate__(), the 
	# state object need not be a dictionary and these methods can do 
	# what they want.
	#
	def __getstate__(self):
		'Pickle support: returns scene data that can be pickled'
		pickleAttr = ('name', 'description', 'dispname', 'notes',
			'rating', 'ratingMax', 'state', 'tool_settings',
			'saveStateVer', 'valid', 'viewImages')
		pickleDict = {}
		for attr in pickleAttr:
			if attr == 'viewImages':
				imgDataLst = []
				for img in self._viewImages:
					# This tuple contains arguments to Image.fromstring()
					imgData = (img.mode, img.size, img.tostring())
					imgDataLst.append(imgData)
				pickleDict[attr] = imgDataLst
				continue
			if hasattr(self, attr):
				pickleDict[attr] = getattr(self, attr)
		return pickleDict

	def __setstate__(self, pickleDict):
		'Pickle support: restores a scene instance from pickled data'
		# pickleDict is already unpickled
		# if this is the first instantiation of Scene, set _imgSize now
		self._inScenes = False
		if not self._imgSize:
			self.imgSize = getImgSizePref()
		# restore triggerset
		self.triggerInit()
		# restore simple one-to-one attributes
		exclude = ['rating', 'ratingMax', 'state',
			'viewImages']
		for k, v in pickleDict.items():
			if k in exclude:
				continue
			setattr(self, k, v)
		# setting the rating depends on first setting ratingMax
		self.ratingMax = pickleDict['ratingMax']
		self.rating = pickleDict['rating']
		if not hasattr(self, 'tool_settings'):
			self.tool_settings = {}
		if not hasattr(self, 'saveStateVer'):
			self.saveStateVer = 1
		# restore viewImages and then self.img
		from PIL import Image
		self._viewImages = []
		for imgData in pickleDict['viewImages']:
			pilImage = Image.fromstring(*imgData)
			self._viewImages.append(pilImage)
		# self.img depends on self._viewImages, trigger SceneImage.__set__:
		if self.valid:
			self.img = 'thumbnail'	# Managed by SceneImage() descriptor
		else:
			self.img = 'orphaned'	# Managed by SceneImage() descriptor
		# Restore the scene state
		self.state = pickleDict['state']
		self.instancesAdd(self)

	def destroy(self):
		'Cleanup a scene instance content'
		if DEBUG:
			import sys
			print 'Scene.destroy name:\t', self.name
			print 'Scene.destroy refcount before:\t', sys.getrefcount(self)
		self.instancesRemove(self)  # stop tracking this instance
		#del self.trans	# triggers property fdel
		del self.state	# triggers property fdel
		del self.img	# see SceneImage.__delete__()
		for trigger in self.triggers:
			self.triggerset.deleteTrigger(trigger)
		if DEBUG:
			import sys
			dir(self)
			print 'Scene.destroy refcount after:\t', sys.getrefcount(self)

	def addedToScenes(self):
		self._inScenes = True
		addChanged("scenes")

	def removedFromScenes(self):
		self._inScenes = False
		addChanged("scenes")

	def display(self, frames=1, mode='linear',
				properties=['all'], inMovie=False):
		'Display a scene (return boolean)'
		# Get the generic scene transition
		self.trans = frames  # property methods configure triggers

		caller = not inMovie and self or None
		if not self.trans.restore(caller=caller):
			# "restore" fires the SCENE_TOOL_RESTORE trigger
			return False
		return True

	def integrity(self, removedModel=None):
		'Verify models in a scene, returns set of invalid models'
		# This method is called from the Scenes class and any integrity issues
		# are handled in the Scenes class.  The scene state integrity returns
		# the intersection of removedModels with the scene state models.
		return self.state.integrity(removedModel)

	@property
	def description(self):
		'Scene description (word wrapped to 60 characters wide)'
		return self._description
	@description.setter
	def description(self, text):
		if '\n' in text:
			text = text.replace('\n', ' ')
		if isinstance(text, list):
			text = ' '.join(text)
		from textwrap import wrap
		wrapped = wrap(text, 60)
		self._description = '\n'.join(wrapped)
		if self._inScenes:
			addChanged("scenes")

	def markOrphan(self):
		'Mark the scene as invalid because it refers to missing model(s)'
		self.valid = False
		self.img = 'orphaned'	# calls SceneImage.__set__
		self.triggerOut('scene_invalid', self)

#	@property
#	def name(self):
#		'backward compatibility'
#		return self.disptitle

	@property
	def rating(self):
		'A rating property (an integer in the range [1,self.ratingMax])'
		return self._rating
	@rating.setter
	def rating(self, value):
		try:
			v = int(value)
		except:
			v = 1
		if v < 1:
			self._rating = 1
		elif v > self.ratingMax:
			self._rating = self.ratingMax
		else:
			self._rating = v
		if self._inScenes:
			addChanged("scenes")

	def _saveState(self):
		from SceneState import SceneState
		state = SceneState(self.dispname, self.name)
		if state._pickle_errs: # something failed to be saved
			from BugReport import bugNotify
			errs = state._pickle_errs
			num = len(errs)
			if num == 1:
				str = "Part of a scene could not be saved:\n" + errs[0] + ".\n"
			else:
				p_str = "Some parts of a scene could not be saved:\n"
				for e in errs:
					p_str += e + ",\n"
				str = p_str[:-2]
				str += '.\n'
			s_str = """
This indicates a problem in scene saving and we would appreciate it if you
would use the bug-report button below to send us the information that
will allow us to improve the scene saving code."""
			b_str = str + s_str
			bugNotify(b_str, str)
			state._pickle_errs = []
		return state

	@property
	def trans(self):
		'A scene transition'
		return getattr(self, '_trans', None)
	@trans.setter
	def trans(self, frames):
		# Use the frames if not 1, otherwise use a generic 'scene' transition.
		if self.trans is None:
			from Transitions import transitions
			if frames > 1:
				self._trans = transitions.transitionGet('custom_scene')
				self._trans.frames = frames
			else:
				self._trans = transitions.transitionGet('scene')
			# Register handlers for transitions (deregister them in deleter)
			self._transTriggerHandlers = {}

			# state handlers
#			trigArgs = ('transition_started', self.state.triggerIn, self.name)
#			h = self._trans.triggerset.addHandler(*trigArgs)
#			self._transTriggerHandlers[trigArgs[0]] = h
			if not self._trans.triggerset.hasHandlers('transition_frame'):
				trigArgs = ('transition_frame', self.state.triggerIn, self.name)
				h = self._trans.triggerset.addHandler(*trigArgs)
				self._transTriggerHandlers[trigArgs[0]] = h

			# scene cleanup
			trigArgs = ('transition_complete', self.triggerIn, self.name)
			h = self._trans.triggerset.addHandler(*trigArgs)
			self._transTriggerHandlers[trigArgs[0]] = h

	@trans.deleter
	def trans(self):
		# Cleanup the triggers first
		for trigName, h in self._transTriggerHandlers.items():
			self._trans.triggerset.deleteHandler(trigName, h)
		del self._trans
		# Don't remove the 'scene' transition from Transitions.transitions.

	def triggerInit(self):
		'''Create triggerset for a scene'''
		self.triggerHandlers = {}
		# Create scene triggers - handled in GUI
		self.triggerset = chimera.triggerSet.TriggerSet()
		self.triggers = ['scene_invalid']
		for trigger in self.triggers:
			self.triggerset.addTrigger(trigger, self.triggerTracking)

	def triggerIn(self, trigger=None, funcData=None, trigData=None):
		'''Generic trigger handler for scene'''
		if trigger == 'transition_complete':
			# Finished with the transition object!  The property deleter
			# will cleanup the trigger handlers.
			del self.trans

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
			handlers = self.triggerset.triggerHandlers(trigger)
			info = (self.disp.title, trigger, handlers)
			print 'Scene.triggerTracking: name=%s; trigger=%s; handlers=%s' % info

	def write(self):
		'Write a scene to the file system'
		# TODO: implement this scene save functionality instead
		#	   of this status message
		msg = 'scene.write not implemented yet'
		chimera.replyobj.warning(msg)

