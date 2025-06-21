# --- UCSF Chimera Copyright ---
# Copyright (c) 2006 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---

#import weakref

import chimera
import Midas
from . import addChanged

# If DEBUG is on, it slows things down
DEBUG = 0
if DEBUG:
	import sys

class Transition(object):
	'''Scene transitions
	The purpose of this class is to change the Chimera display to
	restore the view saved in a scene, using a variety of transition
	parameters, together with automatic detection of state-changes.
	Whatever the current state of the display, it should be returned to
	the saved state of a scene object.  All the scene properties are
	saved in the SceneState class, which must be passed by reference to
	this class for access to the saved state (see init method).
	This class is designed to be instantiated by scene or keyframe
	instances, to provide uniform state transition methods, with
	flexibility to have different transitions of any scene that is
	associated with one or more keyframes.
	'''

	# Try to avoid conflict in scene transitions
	# Added: manage play MaxFrameRate here
	RestoringScene = False
	from chimera import update
	previous_rate = update.MAX_FRAME_RATE
	@classmethod
	def RestoringSceneSet(cls, value):
		cls.RestoringScene = value
		if value: # starting play
			cls.previous_rate = cls.update.MAX_FRAME_RATE
			cls.update.setMaximumFrameRate(25)
		else: # ending play
			cls.update.setMaximumFrameRate(cls.previous_rate)

	# A class attribute to define the possible properties for transitions.
	PropertySet = set(['all', 'clips', 'molecules', 'surfaces',
			'view', 'volumes', 'xforms'])

	# A class attribute to define the set of interpolation modes
	#Modes = set(['geometric', 'halfstep', 'linear'])
	Modes = set(['halfstep', 'linear'])

	# Default parameters
	PROPERTIES = ['all']

	def __init__(self, name, frames=1, mode='linear', properties=['all']):
		'''Initialize scene transition; inputs:
		- name - a transition name
		- frames (int): specify how many transition steps to interpolate
			between the current display and a saved scene.
		- mode (str): interpolation method can be:
			'halfstep' | 'linear' (default)
		- properties (list) - apply transitions to specified properties,
			including: 'all' (default), 'molecules','position','surfaces', etc.;
			see Transition.PropertySet for all the options.
		'''
		# Is this transition part of a keyframe in the timeline?
		self._inKeyFrames = False
		# Init data used for tracking/firing transition triggers
		self._caller = None
		self.tool_settings = None

		self.triggerInit()
		self.name = name	# transition name (usually scene or keyframe title)
		# Assign defaults when arguments are None
		self.frames = frames	# Number of frames for transition (property)
		self.mode = mode		# transition mode
		self.properties = properties	# properties to animate
		# Additional parameters that get defaults on init.
		# TODO: Should these always get defaults?
		self.discreteFrame = 1  # Frame N of frames, for discrete transitions
		self.frameCount = 0
		self.validate()
		self._pauseOn = False
		self._switch_keyframe = False
		self._restoringFrame = False

	Session_attr = [
		'name',
		'mode',
		'frames',
		'discreteFrame',
		# Do not save frameCount since we are not restoring the playback
		# state yet. - CH
		# 'frameCount',
		'properties',
	]
	# Pickle method: called in session save
	def __getstate__(self):
		# Let the pickle call occur in Session.py, not here.
		# Return the transition state as a dict that can be pickled.
		pickleDict = {}
		for a in self.Session_attr:
			pickleDict[a] = getattr(self, a)
		return pickleDict

	# Pickle method: called in session restore
	def __setstate__(self, pickleDict):
		# pickleDict is already unpickled
		# The order of the attr restore is important, because some property
		# setters depend on other attributes to validate values.
		self.__init__(pickleDict['name'], pickleDict['frames'], pickleDict['mode'], pickleDict['properties'])
		for attr in self.Session_attr:
			try:
				value = pickleDict[attr]
			except KeyError:
				pass
			else:
				setattr(self, attr, value)
		self.validate()
		self.triggerInit()

	def destroy(self):
		# Cleanup all the trigger handlers?
		#self.triggerset.addTrigger(trigger, self.triggerTracking)
		pass

	def addedToKeyFrames(self):
		self._inKeyFrames = True

	def removedFromKeyFrames(self):
		self._inKeyFrames = False

	@property
	def discreteFrame(self):
		'The frame for discrete changes in a scene transition'
		return self._discreteFrame
	@discreteFrame.setter
	def discreteFrame(self, value):
		self._discreteFrame = self.frameCheck(value)
		self.triggerOut('transition_discreteFrame', self.name)
		if self._inKeyFrames:
			addChanged("timeline")

	@property
	def frames(self):
		'The total frames in a scene transition'
		return self._frames
	@frames.setter
	def frames(self, value):
		'changed the default to 0 because keyframe0 has 0 frames'
		try:
			v = int(value)
		except:
#			v = 1
			v = 0
#		if v < 1:	# We need at least one frame to restore a scene
#			v = 1
		self._frames = v
		self.triggerOut('transition_frames', self.name)
		if self._inKeyFrames:
			addChanged("timeline")

	def frameCheck(self, value):
		'Validate frame parameters'
		try:
			v = int(value)
		except:
			v = 1
		if v < 1:
			v = 1
		if v > self.frames:
			v = self.frames
		return v

	@property
	def frameCount(self):
		'The frame count in a scene transition'
		return self._frameCount
	@frameCount.setter
	def frameCount(self, value):
		'Set self.frameCount to int:i, but if i < 1, i = 1'
		try:
			v = int(value)
		except:
			v = 1
		if v < 0:	# frameCount=0 in self.restore, before self.frameNext
			v = 0
		self._frameCount = v

	def frameNext(self, setHandler=False, caller=None):
		'Restore the next frame of a scene animation'
		if not hasattr(self, 'rates'):
			self.ratesInit()
		if setHandler:
			self.triggerOut('transition_started', self.name,
								caller=caller)
		self.frameCount += 1
		self.frameDisplay(direction=1, caller=caller)
		if setHandler:
			self.triggerOut('transition_complete', self.name,
								caller=caller)
		return self.frameCount

	def framePrevious(self, setHandler=False, caller=None):
		'Restore the previous frame of a scene animation'
		if setHandler:
			self.triggerOut('transition_started', self.name,
								caller=caller)
		self.frameCount -= 1
		self.frameDisplay(direction= -1, caller=caller)
		if setHandler:
			self.triggerOut('transition_complete', self.name,
								caller=caller)
		return self.frameCount

	def frameDisplay(self, direction=1, caller=None):
		'Restore a frame of a scene animation'
		if self._restoringFrame:
			#msg = 'Already restoring '
			#msg += 'scene: %s, ' % self.name
			#msg += 'frame: %d' % self.frameCount
			#chimera.replyobj.error(msg)
			Midas.wait(1)
		self._restoringFrame = True
		# Activate per-frame trigger
		trigData = {
			'properties': self.properties,
			'discreteFrame': self.discreteFrame,
			'frameCount': self.frameCount,
			'frames': self.frames,
			'rate': self.rate,
			'direction': direction,
			'caller':caller,
			}
		self.triggerOut('transition_frame', self.name, **trigData)
		self._restoringFrame = False

	@property
	def mode(self):
		'The transition mode (default is "linear")'
		return self._mode
	@mode.setter
	def mode(self, value):
		try:
			assert isinstance(value, str)
			assert value in self.Modes
			self._mode = value
		except:
			self._mode = 'linear'
		if self._inKeyFrames:
			addChanged("timeline")

	@property
	def properties(self):
		'The transition properties (default is "all")'
		return self._properties
	@properties.setter
	def properties(self, value):
		try:
			assert isinstance(value, list)
			for property in value:
				assert property in self.PropertySet
			self._properties = value
		except:
			self._properties = ['all']
		if self._inKeyFrames:
			addChanged("timeline")

	def restore(self, frameCount=0, caller=None):
		"""Restore the state of a Scene.
		While self.frameCount > self.frames, process the next frame in
		a sequence of frames in a transition from the current display state
		to restore a saved state.  After each frame is processed,
		increment self.frameCount.
		
		By passing in frameCount > 0 < self.frames the animation can be
		resumed after pause.
		frameCount is returned so that the caller knows where to resume.
		"""

		self.validate()
		if self.RestoringScene:
			msg = 'Sorry, another scene is being restored.'
			chimera.replyobj.status(msg)
			return 0
		self.RestoringSceneSet(True)
		# TODO: Do we want ratesInit() here, instead of frameDisplay?
		self.triggerOut('transition_started', self.name, caller=caller)
		self.ratesInit()
		self.frameCount = frameCount
		while self.frameCount < self.frames:
			# TODO: Do we need the wait here AND in frameDisplay?
			Midas.wait(1)
			if self._pauseOn:
				self._pauseOn = False
				self.RestoringSceneSet(False)
				self.triggerOut('transition_complete',
							self.name,
							caller=caller)
				return self.frameCount
			if self._switch_keyframe:
				self._switch_keyframe = False
				self.RestoringSceneSet(False)
				self.triggerOut('transition_complete',
							self.name,
							cmd='switch_keyframe',
							caller=caller)
				return 0
			self.frameNext(caller=caller) # increments self.frameCount
		self.RestoringSceneSet(False)
		self.triggerOut('transition_complete', self.name, caller=caller)
		self.frameCount = 0
		return self.frames

	@property
	def rate(self):
		return self.rates[self.frameCount]

	def ratesInit(self):
		'Set the interpolation rate parameter'
		# TODO: have this function return a sequence in a tuple, then
		# index the sequence for each frame.  Double check the values in
		# the sequence.  (Even if all values are the same, python should
		# be frugal with referencing the same object.
		#self.rate = [float(i) / frames for i in range(1, frames + 1)]
		#
		# Calculation examples:
		# 1 <= self.frameCount <= self.frames
		# first frame: frameCount = 1
		# last frame:  frameCount = self.frames = 20
		frames = self.frames
		# start at zero, so self.frameCount can index self.rates directly
		self.rates = [0]
		if self.mode == 'linear':
			#
			# TODO: Explore having an 'absoluteRate' that might be
			# used for manipulating the fade-in/fade-out opacity
			# in the SceneState.modelDisplayRestore etc.
			#
			self.rates += [ 1.0 / float(frames - i) for i in range(frames)]
		elif self.mode == 'halfstep':
			# provides rapid rates early, slower later (linear deceleration)
			# NOTE: halfstep is geometric with r=0.5
			self.rates += [0.5] * frames
			self.rates[-1] = 1.0
		#if self.mode == 'geometric':
		#	# The Nth term of a geometric sequence with
		#	# initial value a and common ratio r is given by:
		#	# a_n = a * r ** (n - 1).
		#	# where r != 0 is the common ratio and a is a scale factor,
		#	# equal to the sequence's start value.
		#	a = 1.0
		#	r = 0.9
		#	self.rates = [1 - a * pow(r, i) for i in range(frames)] + [1.0]
		#elif self.mode == 'geometric':
		#	# GODDARD TODO: revise so we don't over/under shoot 1
		#	self.rate = 0.5 / pow(frames, 1.0 / frames)
		self.rates = tuple(self.rates)
		return

	def triggerInit(self):
		'Initialise transition triggers'
		# These triggers are used to coordinate scene restore
		self.triggerset = chimera.triggerSet.TriggerSet()
		self.triggers = [
			'transition_discreteFrame', # issued when self.discreteFrame is assigned
			'transition_frame', # issued for every frame
			'transition_frames', # issued when self.frames is assigned
			'transition_started', # issued before first frame
			'transition_paused', # 
			'transition_complete', # issued after last frame
			'switch_keyframe', # dbl clicked during play; play switched-to after stop
			]
		for trigger in self.triggers:
			self.triggerset.addTrigger(trigger, self.triggerTracking)
		self.triggerset.addHandler('transition_paused', self.triggerIn, None)
		self.triggerset.addHandler('switch_keyframe', self.triggerIn, None)

	def triggerIn(self, trigger=None, funcData=None, trigData=None):
		if trigger == 'transition_paused':
			self._pauseOn = True
		if trigger == 'switch_keyframe':
			self._switch_keyframe = True

	def triggerOut(self, trigger=None, name=None, caller=None, **trigData):
		'''
		Activate a trigger, by its name, passing in trigData
		'''
		if not trigger:
			# print the list of trigger names
			trigger_names = self.triggerset.triggerNames()
			print 'Transition triggers: %s' % trigger_names
			for name in trigger_names:
				print 'Trigger handlers for "%s": ' % name
				print self.triggerset.triggerHandlers(name)
			return
		if trigger not in self.triggers:
			error = 'No trigger named "%s"' % trigger
			raise chimera.error(error)
		if caller:
			# If caller is set, we are playing back
			# an animation transition and we need to
			# fire transition triggers
			self._caller = caller
			from chimera import ANIMATION_TRANSITION_STEP, SCENE_TOOL_RESTORE
			from Scene import Scene
			from Keyframe import Keyframe
			if isinstance(caller, Scene):
				scene = caller
			elif isinstance(caller, Keyframe):
				scene = caller.scene
			else:
				scene = None
			from chimera import triggers
			if trigger == 'transition_frame':
				self.triggerset.activateTrigger(trigger, trigData)
				triggers.activateTrigger(
					ANIMATION_TRANSITION_STEP, self)
			elif trigger == 'transition_started':
				if self.frameCount == 0:
					self.start()
				self.triggerset.activateTrigger(trigger, name)
			elif trigger == 'transition_complete':
				self.triggerset.activateTrigger(trigger, name)
				if self.frameCount == self.frames:
					if scene:
						triggers.activateTrigger(
							SCENE_TOOL_RESTORE, scene)
					self.finish()
			else:
				self.triggerset.activateTrigger(trigger, name)
			self._caller = None
		else:
			# We are not in an animation transition so
			# we do not have to worry about firing
			# transition triggers
			import chimera
			if trigger == 'transition_frame':
				self.triggerset.activateTrigger(trigger, trigData)
			else:
				self.triggerset.activateTrigger(trigger, name)

	def triggerTracking(self, trigger, *args):
		if DEBUG:
			print trigger
			print self.triggerset.triggerHandlers(trigger)

	def validate(self):
		'validate the integrity of the scene transition parameters'
		if not self.mode in self.Modes:
			error = 'unknown transition mode: %s\n' % self.mode
			error += 'transition modes: %s' % self.Modes
			raise chimera.error(error)
		for p in self.properties:
			if p not in self.PropertySet:
				error = 'unknown transition property: %s\n' % p
				error += 'transition properties: %s' % self.PropertySet
				raise chimera.error(error)

	def target(self):
		'return keyframe/scene that owns this transition'
		return self._caller

	def scene(self):
		'return keyframe/scene that owns this transition'
		from Scene import Scene
		from Keyframe import Keyframe
		if isinstance(self._caller, Scene):
			return self._caller
		elif isinstance(self._caller, Keyframe):
			return self._caller.scene
		else:
			return None

	def start(self):
		self.tool_settings = dict()
		from chimera import triggers, ANIMATION_TRANSITION_START
		triggers.activateTrigger(ANIMATION_TRANSITION_START, self)

	def finish(self, caller=None):
		if caller:
			self._caller = caller
		if self.tool_settings is not None:
			from chimera import triggers, ANIMATION_TRANSITION_FINISH
			triggers.activateTrigger(ANIMATION_TRANSITION_FINISH, self)
			self.tool_settings = None
