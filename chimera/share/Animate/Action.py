# --- UCSF Chimera Copyright ---
# Copyright (c) 2006 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---

import chimera

import Icons
import Midas
from Cmd import ChoiceParam, IntParam, FloatParam, StrParam
from Cmds import cmds
from . import addChanged

DEBUG = 0
if DEBUG:
	import sys

class Action(object):
	'''Action instantiates an instance of command with potentially user
	modified parameters.
	'''

	# manage play MaxFrameRate here
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

	def __init__(self, cmd, index, end_frame=None):
		'''Create a new action object as an instance of a chimera command.
		- cmd: a chimera cmd on the Actions palette '''
		self.cmd = cmd
		self.name = cmd.name

		# Is this transition part of a keyframe in the timeline?
		self._inKeyFrames = False

		self.index = index
		self._frames = 20 # default for append
		self.frameCount = 0
		self.kf_id = self.keyframes.new_id()
		# this is the only time self.end_frame is derived from self.frames.
		if index == 0:
			self.end_frame = 0
		elif end_frame is None:
			self.end_frame = self.keyframes.entries[index - 1].end_frame + \
				self.frames
		else:
			self.end_frame = end_frame
		self.kf_id = self.keyframes.new_id() # 'kf_id' to ensure consistent lookups
		self.triggerInit() 	# required before assignment for scene
		self._pauseOn = False

	# Pickle method (session save)
	def __getstate__(self):
		pickleData = {}
		pickleData['name'] = self.name
		pickleData['cmd'] = self.cmd
		pickleData['index'] = self.index
		pickleData['end_frame'] = self.end_frame
		return pickleData

	# Pickle method (session restore)
	def __setstate__(self, pickleDict):
		self.__init__(pickleDict['cmd'], pickleDict['index'], pickleDict['end_frame'])
#		name = pickleData['name']
#		cmd = pickleData['cmd']
#		index = pickleData.get('index', 1) # must be non-zero
#		end_frame = pickleData('end_frame')
#		self.__init__(cmd, index, end_frame)
		# TODO: restore all the properties of the command

	def actionFrameHandler(self, do, param=None):
		'''triggers to be fired between the start and end of an action command.
		Midas command unregister their own handlers when done.'''
		trigNames = ['transition_frame'] #, 'keyframe_display']
		for trigName in trigNames:
			if do == 'add':
				if not param:
					chimera.replyobj.error("missing parameter for actionFrameHandler")
					return
				trigArgs = (trigName, self.cmd.callback(), param)
				h = self.triggerset.addHandler(*trigArgs)
				self.triggerHandlers[trigName] = h

			# Midas command de-register themselves using param as arg 'do'
			if do == 'delete' or isinstance(do, dict):
				if do == 'delete' or do['command'] in cmds.cmds:
					# De-register the handler in the Action
					h = self.triggerHandlers.get(trigName, None)
					if h:
						self.triggerset.deleteHandler(trigName, h)
						del self.triggerHandlers[trigName]

	def destroy(self):
		'Explicitly release references to scene and transition objects'
		if DEBUG:
			print 'Action.destroy title:\t', self.disptitle
			print 'Action.destroy refcount:\t', sys.getrefcount(self)

	def addedToKeyFrames(self):
		self._inKeyFrames = True
		self.cmd.addToKeyFrames()
		addChanged("timeline")

	def removedFromKeyFrames(self):
		self._inKeyFrames = False
		self.cmd.removeFromKeyFrames()
		addChanged("timeline")

	def display(self, frameCount=0, direction=1):
		''' Run the command. Similar to Transition.restore() '''
		self.RestoringSceneSet(True)

		if frameCount == 0: # fresh start
			self.initAction()
		param = self.pauseParam
		self.actionFrameHandler('add', param)
		self.frameCount = frameCount
		while self.frameCount < self.frames:
			Midas.wait(1)
			if self._pauseOn:
				self._pauseOn = False
				self.RestoringSceneSet(False)
				self.actionFrameHandler('delete')
				return self.frameCount
			trigData = {
				'direction': direction,
				'caller': self,
				}
			self.triggerOut('transition_frame', self.name, **trigData)
			self.frameCount += 1

		self.RestoringSceneSet(False)
		return True

	@property
	def frames(self):
		return self._frames
	@frames.setter
	def frames(self, value):
		self._frames = value
		self.triggerOut('action_frames', self)
		if self._inKeyFrames:
			addChanged("timeline")

	def frameNext(self, setHandler=False):
		'''display one frame of the current action.'''
		self.RestoringSceneSet(True)
		param = self.pauseParam
		if not param:
			return

		self.actionFrameHandler('add', param)
		trigData = {
			'direction': 1,
			'caller': self,
		}
		self.triggerOut('transition_frame', self.name, **trigData)
		Midas.wait(1)
		self.frameCount += 1
		self.RestoringSceneSet(False)
		self.actionFrameHandler('delete')

	@property
	def keyframes(self):
		from Keyframes import keyframes
		return keyframes

	@property
	def index(self):
		'The unique index of an action in a keyframes sequence'
		return getattr(self, '_index', None)
	@index.setter
	def index(self, value):
		try:
			v = int(value)
			if v >= 0:
				self._index = v
			else:
				raise ValueError
			if self._inKeyFrames:
				addChanged("timeline")
		except:
			raise AttributeError('Action.index must be an integer >= 0')

	def initAction(self):
		param = self.cmd.cb_param()
		self.pauseParam = param
		param['removalHandler'] = self.actionFrameHandler

	@property
	def keytitle(self):
		'A standardized title for keyframes'
		return '%d:%s' % (self.kf_id, self.name)

	@property
	def dispname(self):
		return self.name

	@property
	def disptitle(self):
		return '%d: %s' % (self.index + 1, self.name)

	def resume(self, frameCount):
		'''continue keyframe play from Transition frame which was paused.'''
		return self.display(frameCount)

	def triggerInit(self):
		'Initialize triggers and trigger handlers'
		self.triggerset = chimera.triggerSet.TriggerSet()
		self.triggers = [
			'transition_frame', # issued for every frame
			'action_frames', 	# issued when frame count changes
			'transition_paused', # user paused play
			'delete_actionHandler', # drop pause state if handler still exists
			]
		for trigger in self.triggers:
			self.triggerset.addTrigger(trigger, self.triggerTracking)
		self.triggerHandlers = {}
		for trig in ['action_frames', 'transition_paused']: 	#self.triggers:
			h = self.triggerset.addHandler(trig, self.triggerIn, None)
			self.triggerHandlers[trig] = h
		h = self.keyframes.triggerset.addHandler('delete_actionHandler', self.triggerIn, None)
		self.keyframes.triggerHandlers[trig] = h

	def triggerIn(self, trigger=None, funcData=None, trigData=None):
		'Handle triggers for an action'
		if trigger == 'action_frames':
			self.cmd.update()
		if trigger == 'transition_paused':
			self._pauseOn = True
		if trigger == 'delete_actionHandler':
			self.actionFrameHandler('delete')

	def triggerOut(self, trigger=None, name=None, **trigData):
		''' Activate a trigger, by its name, passing in trigData '''
		if not trigger:
			# print the list of trigger names
			trigger_names = self.triggerset.triggerNames()
			print 'Action triggers: %s' % trigger_names
			for name in trigger_names:
				print 'Trigger handlers for "%s": ' % name
				print self.triggerset.triggerHandlers(name)
		else:
			if trigger not in self.triggers:
				error = 'No trigger named "%s"' % trigger
				raise chimera.error(error)
			self.triggerset.activateTrigger(trigger, trigData)

	def triggerTracking(self, trigger, *args):
		if DEBUG:
			print 'Action.triggerTracking: ', self.disptitle
			print 'Action.triggerTracking: ', trigger
			print 'Action.triggerTracking: ', self.triggerset.triggerHandlers(trigger)

	@property
	def valid(self):
		return True
