# --- UCSF Chimera Copyright ---
# Copyright (c) 2006 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---

import chimera
#from Transition import Transition
import Transitions
from . import addChanged

DEBUG = 0
if DEBUG:
	import sys

class Keyframe(object):
	'''
	A keyframe class
	Each keyframe instance contains a reference to a scene object and
	an independent transition object.  The class provides attributes and
	methods to simplify working with a keyframe object.
	'''

	@property
	def scenes(self):
		from Scenes import scenes
		return scenes

	@property
	def keyframes(self):
		from Keyframes import keyframes
		return keyframes

	def __init__(self, scene, index, trans=None, end_frame=None):
		'''Create a new keyframe object, with reference to a scene object
		- scene: an existing scene object
		- index: where to insert it in keyframes.entries
		- trans: optional transition
		- end_frame: location on the timeline if drag 'n' dropped; if end_frame
			is set index will be overridden when inserted into keyframes.
			
		'''
		# Is this transition part of a keyframe in the timeline?
		self._inKeyFrames = False

		self.triggerInit() 	# required before assignment for scene
		self.scene = scene
		self.index = index
		self.kf_id = self.keyframes.new_id()
		if trans:
			self.trans = trans
		else:
			# frames will get overriden if end_frame is a parameter
			self.trans = self.trans_create({'frames': 20})

		if index == 0 and not end_frame:
			self.end_frame = 0
		elif not end_frame:
		# this is the only time self.end_frame might be derived from self.frames.
			self.end_frame = self.keyframes.entries[index - 1].end_frame + \
				self.frames
		else:
			self.end_frame = end_frame
			self.index = 1

		self.transHandlers('add')

	# Pickle method (session save)
	def __getstate__(self):
		pickleData = {}
		pickleData['name'] = self.name
		pickleData['trans'] = self.trans
		pickleData['index'] = self.index
		pickleData['end_frame'] = self.end_frame
		return pickleData

	# Pickle method (session restore)
	def __setstate__(self, pickleData):
		name = pickleData['name']
		scene = self.scenes.getScene_by_name(name)
		trans = pickleData['trans']
		index = pickleData.get('index', 0)
		end_frame = pickleData.get('end_frame', None)
		self.__init__(scene, index, trans, end_frame)
		# TODO: restore all the properties of the transition, esp. triggers

	def destroy(self):
		'Explicitly release references to scene and transition objects'
		if DEBUG:
			print 'Keyframe.destroy title:\t', self.keytitle
			print 'Keyframe.destroy refcount:\t', sys.getrefcount(self)
		# added when converted from property to attr
		# delete the triggers first
		self.transHandlers('delete')
		if hasattr(self, 'trans'):
			del self.trans
		if hasattr(self, 'scene'):
			del self.scene

	def addedToKeyFrames(self):
		self._inKeyFrames = True
		if self.trans:
			self.trans.addedToKeyFrames()
		addChanged("timeline")

	def removedFromKeyFrames(self):
		self._inKeyFrames = False
		if self.trans:
			self.trans.removedFromKeyFrames()
		addChanged("timeline")

	def display(self, frameCount):
		''' Show the state of a single keyframe.'''
		return self.trans.restore(frameCount, caller=self)

	@property
	def dispname(self):
		return self.scene.dispname

	@property
	def disptitle(self):
		'''formerly title attribute. This changes with the position order of the
		keyframe.'''
		return '%d: %s' % (self.index + 1, self.scene.dispname)

	@property
	def frameCount(self):
		if not hasattr(self, 'trans'):
			return None
		return self.trans.frameCount
	@frameCount.setter
	def frameCount(self, count):
		if not hasattr(self, 'trans'):
			return
		self.trans.frameCount = count

	def frameNext(self, setHandler=False):
		'''wrapper: display one frame of the current transition.'''
		if not hasattr(self, 'trans'):
			return
		self.trans.frameNext(setHandler, caller=self)

	@property
	def frames(self):
		if not hasattr(self, 'trans'):
			return 0
		return self.trans.frames
	@frames.setter
	def frames(self, newframes):
		'''frames are_extlinks_available derived from end_frame and the previous keyframe's 
		end_frame.'''
		if hasattr(self, 'trans'):
			self.trans.frames = newframes

	@property
	def frameSequence(self):
		# Get a sequence of keyframe frame numbers; this is an ordered dict
		# with keys: keyframe names, values: frame count sequence, with
		# consecutive values across the entire animation sequence.
		frameNumbers = self.keyframes.frameCounts()
		return frameNumbers[self.keytitle]

	@property
	def index(self):
		'The unique index of a keyframe in a keyframes sequence'
		return getattr(self, '_index', None)
	@index.setter
	def index(self, value):
		try:
			v = int(value)
			if v >= 0:
				self._index = v
				if self._inKeyFrames:
					addChanged("timeline")
			else:
				raise ValueError
		except:
			raise AttributeError('Keyframe.index must be an integer >= 0')

	@property
	def keytitle(self):
		'''A standardized keytitle for keyframes. this value does not vary and
		serves as the key into LightboxKeyframes.buttonDict.'''
		return '%d:%s' % (self.kf_id, self.name)

	@property
	def name(self):
		'''The name of a keyframe, refers to a single scene.name. more than one
		keyframe can have the same name; their titles are unique.'''
		if self.scene:
			return self.scene.name
		return None

	def resume(self, frameCount):
		'''continue keyframe play from Transition frame which was paused.'''
		return self.trans.restore(frameCount, caller=self)

	@property
	def scene(self):
		return getattr(self, '_scene', None)

	@scene.setter
	def scene(self, scene):
		if not scene:
			return
		if self.scene:
			del self.scene
		from Animate.Scene import Scene
		assert isinstance(scene, Scene)
		self._scene = scene
		self.sceneHandlers('add')
	@scene.deleter
	def scene(self):
		self.sceneHandlers('delete')
		if hasattr(self, '_scene'):
			del self._scene

	def sceneHandlers(self, action):
		scene = self.scene
		trigName = 'scene_invalid'
		if action == 'add':
			trigArgs = (trigName, self.triggerIn, None)
			h = scene.triggerset.addHandler(*trigArgs)
			self.triggerHandlers[trigName] = h
		elif action == 'delete' and self.triggerHandlers.has_key(trigName):
			h = self.triggerHandlers[trigName]
			scene.triggerset.deleteHandler(trigName, h)
			del self.triggerHandlers[trigName]

	def trans_create(self, valueDict=None):
		# Parse valueDict
		try:
			assert isinstance(valueDict, dict)
			if self.index == 0:
				frames = 0
			else:
				frames = valueDict.get('frames', 20)
			mode = valueDict.get('mode', 'linear')
			properties = valueDict.get('properties', ['all'])
		except:
			# If valueDict is not a dict instance, we need these defaults.
			# We can assign None to all these parameters, because
			# the Transition class has properties for argument validation.
			frames = None
			mode = None
			properties = None
		# Create or update the transition
		if hasattr(self, 'trans'):
			trans = self.trans
		else:
			# Create a unique transition instance that belongs to this keyframe.
#			from Animate.Transition import Transition
#			trans = Transition(self.title, frames, mode, properties)
			import Animate
			trans = Transitions.transitions.append(self.kf_id,
				frames, mode, properties)
			# Hook into the transition triggers
#		else:
#			# The Transition class has properties for argument validation.
#			tr.frames = frames
#			tr.mode = mode
#			tr.properties = properties

			# Might want to validate args before returning

			#
			# TODO: Issue a trigger that the transition has been updated?
			# Decide whether to do that here or in Transition.
			#
		if self._inKeyFrames:
			trans.addedToKeyFrames()
		return trans

	def transHandlers(self, action):
		'''enable triggers between start and end of a transition.'''
		trigNames = ['transition_started', 'transition_complete']
		if hasattr(self, 'trans'):
			tr = self.trans
			if action == 'add':
				self._transTriggerHandlers = {}
			for trigName in trigNames:
				if action == 'add':
					trigArgs = (trigName, self.triggerIn, self.name)
					h = tr.triggerset.addHandler(*trigArgs)
					self._transTriggerHandlers[trigName] = h
				elif action == 'delete':
					h = self._transTriggerHandlers[trigName]
					tr.triggerset.deleteHandler(trigName, h)
					del self._transTriggerHandlers[trigName]
			if action == 'delete':
				del self._transTriggerHandlers

	def transFrameHandler(self, action, opDict=None):
		'''triggers to be received between the start and end of a transition.'''
		trigNames = ['transition_frame']
		for trigName in trigNames:
			if action == 'add':
				# Register the scene.state with the transition
				trigArgs = (trigName, self.scene.state.triggerIn, self.name)
				h = self.trans.triggerset.addHandler(*trigArgs)
				self._transTriggerHandlers[trigName] = h
			if action == 'delete':
				# De-register the scene.state with the transition
				try:
					h = self._transTriggerHandlers[trigName]
				except KeyError:
					# Someone else deleted it already?
					pass
				else:
					self.trans.triggerset.deleteHandler(trigName, h)
					del self._transTriggerHandlers[trigName]

	def triggerInit(self):
		'Initialize triggers and trigger handlers'
		self.triggerHandlers = {}
		# Create keyframe triggers - handled in GUI
		self.triggerset = chimera.triggerSet.TriggerSet()
		self.triggers = ['keyframe_invalid']
		for trigger in self.triggers:
			self.triggerset.addTrigger(trigger, self.triggerTracking)

	def triggerIn(self, trigger=None, funcData=None, trigData=None):
		'Handle triggers for a keyframe'
		if trigger == 'scene_invalid':
			self.triggerset.activateTrigger('keyframe_invalid', self)
			# Don't call self.destroy() here, leave that to the
			# keyframes controller, so there is time for associated GUI
			# elements to clean up.
		if trigger == 'transition_started':
			self.transFrameHandler('add')
		if trigger == 'transition_complete':
			self.transFrameHandler('delete', trigData)

	def triggerTracking(self, trigger, *args):
		if DEBUG:
			print 'Keyframe.triggerTracking: ', self.disptitle
			print 'Keyframe.triggerTracking: ', trigger
			print 'Keyframe.triggerTracking: ', self.triggerset.triggerHandlers(trigger)

	@property
	def valid(self):
		if self.scene:
			return self.scene.valid
		else:
			return False
