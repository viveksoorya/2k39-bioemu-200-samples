# --- UCSF Chimera Copyright ---
# Copyright (c) 2006 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---

from collections import OrderedDict

import chimera
import Animate
import Scenes
import Keyframes
import Cmds
import Cmd
from Keyframe import Keyframe
from Action import Action
from . import addChanged

DEBUG = 0

# play button has three possible states
MOVIE_PLAY		 = 1
MOVIE_PAUSE		 = 2
MOVIE_STOP		 = 3
MOVIE_NEXT_PREV	 = 4

# states for the 'play' button command
 # pause state not available. play will resume from selected kf

class Keyframes(object):
	'''
	A list of keyframes:
		- values are named scene frames (strings)
		- the keyframes call on functionality in scenes
	There is a 'triggerset' with several triggers to coordinate changes in
	Keyframe instances with associated GUI widgets (mainly LightboxKeyframes).
	'''

	def __init__(self):
		# The keyframe list contains named scenes.  Each item of the list
		# is a Keyframe() instance (see Keyframe.py)
		self.entries = 'property setter inits _kfList'
		# Default frames and mode for keyframe transitions
		self.FRAMES = 20
		self.MODE = 'linear'
		self._next_id = 0
		self._kfList = []
		# Define some animation commands
		self.movie_commands = [
#			'first',
#			'previous',
			'play',
#			'minusOne',
			'plusOne',
#			'next',
#			'last',
			'stop',
			'loop',
			'record',
			]
		self.movie_command_tips = {
#			'first': 'First keyframe',
#			'previous': 'Previous keyframe',
#			'minusOne': 'Backup 1 frame',
			'play': 'Play',
			'plusOne': 'Advance 1 frame',
#			'next': 'Next keyframe',
#			'last': 'Last keyframe',
			'stop': 'stop',
			'loop': 'Loop',
			'record': 'Record',
				}
		# Create boolean variables to track play-back status
		self.movie_status = {}
		self.clear()
		self.recordDialog = None
		self.triggerInit()


	def __len__(self):
		return len(self.entries)

	def __str__(self):
		return str(self.entries)

	# Pickle method (session save)
	def __getstate__(self):
		pickleData = {}
#		pickleData['names'] = self.names()
		# TODO: save all the Keyframe instances instead
		pickleData['entries'] = self.entries
		return pickleData

	# Pickle method (session restore)
	def __setstate__(self, pickleData):
		if self != Animate.Keyframes.keyframes:
			# restore in the global instance
			Animate.Keyframes.keyframes.__setstate__(pickleData)
			return
		# compatibility with older save version.
		if not pickleData.has_key('entries'):
			for name in pickleData['names']:
				self.append(name)
		#	# update additional properties or issue triggers?
		else:
			entries = pickleData['entries']
			for kf in entries:
				self.insert_keyframe(kf)

	def append(self, name='default', trans=None, end_frame=None):
		'''
		Add a named keyframe or an cmd into the end of the list:
		- inputs:
			'name' must be the name of an existing scene or cmd.
		- activates the 'keyframe_append' trigger, passing keyframe instance.
		'''
		if end_frame is not None:
			return self.insert(name, trans, end_frame)
		type = self.validate(name)
		index = len(self)
		kf = None
		if type == 'scene':
			kf = self._kfCreate(name, index, trans, end_frame)
			if kf.index == 0:
				kf.frames = 0
			#self.status()
		elif type == 'cmd':
			if index == 0:
				chimera.replyobj.warning("Animation must begin with a scene.")
				return
			kf = self._acCreate(name, index, end_frame)
			# need to change this trigger

	@property
	def cmds(self):
		'''This is a pointer to Cmds.actions which is used to access
		the cmds functionality '''
		return Cmds.cmds

	def clear(self):
		'Delete all keyframes'
		# It may seem feasible to use 'self.entries = []', but this would
		# fail to initiate associated triggers that are required to maintain
		# state for GUI elements.
		while self._kfList:
			self.remove(None, self._kfList[-1].kf_id)
		for cmd in self.movie_commands:
			self.movie_status[cmd] = False
		self.movie_status['play'] = MOVIE_STOP
		# Keep track of the keyframe display state; see show method
		self.display = None
		self.pauseSaved = False
		self.switch_keyframe = False

#	# Keep track of the keyframe display state; see show method
	@property
	def display(self):
		return self._display
	@display.setter
	def display(self, kf):
		self._display = kf
#		self.triggerOut('set_frameline', kf)

	def disptitles(self):
		return [ kf.disptitle for kf in self.entries ]

	def drop_pauseState(self):
		'''delete paused state and reset.'''

		# delete any possible handler in an Action that was paused.
		if self.movie_status['play'] != MOVIE_STOP:
			self.endKeyframePlay(self.display)
		self.triggerOut('delete_actionHandler')
		self.pauseSaved = False
		self.pausedState = None

	@property
	def entries(self):
		return self._kfList
	@entries.setter
	def entries(self, value):
		'Set the list of keyframes'
		if not isinstance(value, list):
			return
		self._kfList = value

	def frameCounts(self):
		'''
		Returns a dict with
		- keys: keyframe keytitles
		- values: list of frame numbers
		The frame numbers begin at 1 for the first frame of the first
		keyframe.  The frame sequence increments by 1 for every frame
		of every keyframe in Keyframes.entries.
		'''
		from collections import OrderedDict
		frames = OrderedDict()
		frameCount = 1
		for kf in self.entries:
			a = frameCount
			b = frameCount + kf.frames
			frames[kf.keytitle] = range(a, b)
			frameCount = b
		return frames

	def getIndex(self, dispname):
		'''
		Get all the indices of keyframes linked to scene 'name'
		- 'name' is a scene name (keyframes link to scenes by name)
		- returns a tuple of keyframe indices that match 'name'
		'''
		indices = []
		if self.validate(dispname):
			dispnames = self.dispnames()
			while dispnames.index(dispname):
				i = dispnames.index(dispname)
				indices.append(i)
				names.pop(i)
		return tuple(indices)

	def getKeyframe_by_disptitle(self, disptitle):
		for entry in self.entries:
			if disptitle == entry.disptitle:
				return entry
		return None

	def getKeyframe_by_id(self, kf_id):
		for entry in self.entries:
			if entry.kf_id == kf_id:
				return entry
		return None

	def getKeyframe_by_keytitle(self, keytitle):
		for entry in self.entries:
			if entry.keytitle == keytitle:
				return entry
		return None

	def getKeyframe_by_index(self, index):
		return self.entries[index]

	def getName_by_keytitle(self, keytitle):
		kf = self.getKeyframe_by_keytitle(keytitle)
		if kf:
			return kf.disptitle
		return None

	def getName_by_index(self, index):
		'''
		Return a keyframe name, given an index
		- inputs:
			'index' is a keyframe index
		'''
		kf = self.getKeyframe_by_index(index)
		return kf.disptitle

	def getSceneName_by_index(self, index):
		'''movies use the scene name to restore the keyframe state.'''
		kf = self.getKeyframe_by_index(index)
		return kf.name

	def getTransition(self, index):
		'''
		Return a keyframe transition object, by index
		- inputs:
			'index=None' is a keyframe index
		'''
		kf = self.getKeyframe_by_index(index)
		return kf.trans

	def getImgSize(self):
		'''
		The size of an image thumb-nail for a keyframe.
		All keyframes have the same size for image thumb-nails.
		This is used by GUI interfaces to create button images.
		'''
		size = (0, 0)
		if len(self.names()):
			kf = self.getKeyframe_by_index(0)
			scene = kf['scene']
			size = scene.GetImgSize()
		return size

	def insert(self, name, index, end_frame=None):
		'''
		Add a named keyframe at a specific index position.
		- inputs:
			'name' must be the name of an existing scene
			'index' must be used to insert into the keyframe entries
		- activates the 'keyframe_insert' trigger, passing keyframe instance.
		- if inserting between frames have to adjust number of frames by
			splitting the existing number of frames proportionately.
		'''
		type = self.validate(name)
		if not type:
			return
		if index is None or index < 0:
			index = 0
		if index > len(self):
#			index = len(self)
			self.append(name)
			return
		try:
			if type == 'scene':
				kf = self._kfCreate(name, index, None, end_frame)
			if type == 'cmd':
				kf = self._acCreate(name, index, end_frame)
			self.triggerOut('keyframe_insert', kf)
		except Exception, e:
			error = 'Cannot insert keyframe to index "%d"' % index
			raise chimera.error(error)
		#self.status()

	def insert_keyframe(self, kf):
		'add to entries after creation'
		self.entries.insert(kf.index, kf)
		self.triggerOut('keyframe_append', kf)
		if not self.display:
			self.display = kf
		self.updateFrames()

	def integrity(self):
		'Remove all keyframes that are not pointers to a scene instance'
		if not self.entries:
			return
		from Scene import Scene
		liveScenes = frozenset(self.scenes.entries)
		entries = list()
		for kf in self.entries:
			if isinstance(kf, Scene) and kf not in liveScenes:
				continue
			entries.append(kf)
		self.entries = entries

	def _kfCreate(self, name, index, trans=None, end_frame=None):
		'Create a new keyframe'
		# Get a reference to the scene object for this keyframe
		scene = self.scenes.getScene_by_name(name)
		kf = Keyframe(scene, index, trans, end_frame)
		self._kfHandlers(kf, 'add')
		self.insert_keyframe(kf)
		kf.scene.state.loadTrajectories()
		return kf

	def _acCreate(self, name, index, end_frame=None):
		'Create a new action'
		# Get a reference to the action object for this action
		import copy
		cmd_class = self.cmds.cmdDict[name].__class__.__name__
		cmd = vars(Cmd)[cmd_class]()
		ac = Action(cmd, index, end_frame)
		ac.cmd.action = ac # back ref
		self.insert_keyframe(ac)
		return ac

	def _kfDelete(self, kf_id):
		'''if there is a kf to the right, give it's transition frames from
		this one.'''
		kf = self.getKeyframe_by_id(kf_id)
		index = kf.index
		if index == 0 and len(self.entries) > 1:
			# Do not let user delete zeroth keyframe if next in line
			# is an Action since Action instances cannot be at the
			# start of an animation
			if isinstance(self.entries[1], Animate.Action.Action):
				chimera.replyobj.error("Keyframe not deleted because "
							"timeline cannot start with an action")
				return
		self._kfHandlers(kf, 'delete')
		if index < len(self.entries) - 1:
			if index == 0:
				newZeroFrame = self.entries[1]
				lostframes = newZeroFrame.frames
				newZeroFrame.frames = 0
				newZeroFrame.end_frame = 0
				if len(self.entries) > 2:
					for i in range(2, len(self.entries)):
						self.entries[i].end_frame -= lostframes
						self.triggerOut('keyframe_move', self.entries[i])
				self.triggerOut('keyframe_move', newZeroFrame)
			else:
				self.entries[index + 1].frames += kf.frames
		del self.entries[index]
		self.updateFrames()
		# Allow GUI to clear keyframe widgets before kf.destroy(); the
		# GUI must remove or update all the keyframe buttons >= kf.index.
		keytitle = kf.keytitle
		self.triggerOut('keyframe_remove', keytitle)
		kf.destroy()

	def _kfHandlers(self, kf, action):
		trigName = 'keyframe_invalid'
		if action == 'add':
			trigArgs = (trigName, self.triggerIn, None)
			h = kf.triggerset.addHandler(*trigArgs)
			self.triggerHandlers[kf.kf_id] = (trigName, h)
			kf.addedToKeyFrames()
		if action == 'delete' and self.triggerHandlers.has_key(kf.kf_id):
			kf.triggerset.deleteHandler(*self.triggerHandlers[kf.kf_id])
			del self.triggerHandlers[kf.kf_id]
			kf.removedFromKeyFrames()

	def _kfRestore(self, kf):
		'''Restore this keyframe from a session.'''
		if self.validate(kf.name):
			self._kfHandlers(kf, 'add')
			self.entries.insert(len(self), kf)
#			self.updateIndexes()
			self.updateFrames()
			self.triggerOut('keyframe_append', kf)
			return kf

	def keytitles(self):
		'''
		Return a sequence of all the keyframe titles; cf. names().
		A keyframe title is a combination of the keyframe id and scene id, the
		tuple returned contains unique values (a set of keytitles).
		'''
		return tuple([kf.keytitle for kf in self.entries])

	def keytitleSplit(self, keytitle):
		kf_id, sc_name = keytitle.split(':')
		return sc_name, int(kf_id)

	def move_keyframes(self, index, newframes):
		'''Change position of the index'd kf and all to the right so the new
		frames count is Nframes for the kf at index.'''
		kf = self.entries[index]
		oldframes = kf.frames
		diff = newframes - oldframes
		for i in range(index, len(self.entries)):
			if i == index: # the only one whose frame count changes
				'''set directly; "keyframes.frames = X" calls this function.'''
				if isinstance(kf, Animate.Action.Action):
					kf.frames += diff
				if isinstance(kf, Animate.Keyframe.Keyframe):
					kf.trans.frames += diff
			kf = self.entries[i]
			kf.end_frame += diff
			self.triggerOut("keyframe_move", kf)

	def move_selections(self, selected_kfs, delta):
		'''move the keyframes to the designated frame on the timeline.
		preserve absolute position of intermediary keyframes on the timeline.
		'''
		if keyframes is None:
			return

		# need checks for bounds first
		for kf in selected_kfs:
			kf.end_frame += delta
		self.updateFrames()
		for kf in selected_kfs:
			self.triggerOut('keyframe_move', kf)

	def movie(self, command, source='MIDAS'):
		'''Implements animation commands
		- movie(< command > , < source >)
		- commands include:
			- first: display first keyframe
			- last: display last keyframe
			- next: display next keyframe
			- previous: display previous keyframe
			- play: start animation
			- stop: stop animation
			- pause: toggle pause status on / off
					pause can be enabled only during play
			- loop: toggle loop status on / off
					when looping, the 'previous', 'next' and 'play' commands will
					wrap around the beginning or end of the keyframe sequence
			- record: toggle record status on / off
					recording starts with 'play', finishes with 'stop'
		- source is where the command originates, which determines whether or
			not to activate a command trigger (to avoid recursive triggers)
			- 'MIDAS' is a Midas command source
			- 'GUI' is an animation module GUI button source
		'''
		commands = self.movie_commands + ['status']
		if command not in commands:
			msg = 'Unknown animation command'
			chimera.replyobj.warning(msg)
		if command == 'status':
			if self.movie_validate():
				self.status('display')
		if command == 'stop':
			self.movie_stop(source)
		if command == 'pause':
			self.movie_pause(source)
		if command == 'first':
			self.movie_first(source)
		if command == 'last':
			self.movie_last(source)
		if command == 'previous':
			self.movie_previous(source)
		if command == 'next':
			self.movie_next(source)
		if command == 'play':
			self.movie_play(source)
		if command == 'loop':
			self.movie_loop(source)
		if command == 'minusOne':
			self.movie_status['play'] = MOVIE_PAUSE
			self.movie_minusOne(source)
		if command == 'plusOne':
#			if self.movie_status['play'] == MOVIE_STOP and self.display.frameCount == 0:
#				# stepping into the next keyframe
#				self.display = self.next_keyframe(self.display)
			self.movie_status['play'] = MOVIE_PAUSE
			self.movie_plusOne(source)
		if command == 'record':
			if self.movie_status['record']: # already running; user must have stopped it
				self.movie_pause(source)
				self.movie_stop(source)
				return
			if not self.recordDialog:
				from RecordDialog import RecordDialog
				self.recordDialog = RecordDialog(self)
			self.recordDialog.source = source
			self.recordDialog.enter()
		if source == 'GUI':
			# When the movie is called from GUI, unregister the handler
			return chimera.triggerSet.ONESHOT

	def movie_first(self, source='MIDAS'):
		'''Select the first keyframe, but don't update the display.'''
		if self.movie_validate():
			kf = self.getKeyframe_by_index(0)
			self.display = kf
#			self.movie('status')
#		if source == 'MIDAS':
#			self.triggerOut('first', None)

	def movie_last(self, source='MIDAS'):
		'''Select the last keyframe, but don't update the display.'''
		if self.movie_validate():
			# Use a non-negative index instead of python aliases (i != -1),
			# because index arithmetic in this class assumes non-negative
			# index values; errors may be raised for -ve indices.
			index = len(self) - 1
			kf = self.getKeyframe_by_index(index)
			self.display = kf
#			self.movie('status')
#		if source == 'MIDAS':
#			self.triggerOut('last', None)

	def movie_next(self, source='MIDAS'):
		if self.movie_validate():
			kf = self.display
			if kf is None:
				index = 0
			else:
				index = kf.index + 1
			if hasattr(kf, 'trans') and kf.trans.RestoringScene:
				self.movie_status['play'] = MOVIE_STOP
				# issue trigger to stop play
				self.triggerOut('transition_paused', kf)
				self.display = kf
			else:
				if index >= len(self):
					if not self.movie_status['loop']:
						self.movie_stop(source)
						return
					index = 0
				name = self.getSceneName_by_index(index)
				# switch the display setting to the next keyframe
				kf = self.getKeyframe_by_index(index)
				self.display = kf
				kf.frameCount = 0
				self.movie_status['play'] = MOVIE_PLAY
				self.show(name, index)
#		if source == 'MIDAS':
#			self.triggerOut('next', None)

	def movie_previous(self, source='MIDAS'):
		if self.movie_validate():
			kf = self.display
			if kf is None:
				index = 0
			else:
				index = kf.index
			if hasattr(kf, 'trans') and kf.trans.RestoringScene:
				self.movie_status['play'] = MOVIE_STOP
				# issue trigger to stop play
				self.triggerOut('transition_paused')
				self.display = self.getKeyframe_by_index(index - 1)
			else:
				if index <= 0:
					self.movie_stop(source)
					return
				kf = self.getKeyframe_by_index(index - 1)
				if hasattr(kf, 'scene') and kf.scene:
					kf.scene.display(inMovie=True)
				name = self.getSceneName_by_index(index)
				self.movie_status['play'] = MOVIE_PLAY
				self.show(name, index)
				self.movie('status')
#		if source == 'MIDAS':
#			self.triggerOut('previous', None)

	def movie_loop(self, source='MIDAS'):
		'toggle the loop status'
		if self.movie_status['loop']:
			self.movie_status['loop'] = False
		else:
			self.movie_status['loop'] = True
#		if source == 'MIDAS':
#			# toggle the GUI when this command comes from MIDAS
#			self.triggerOut('loop', None)

	def movie_pause(self, source='MIDAS'):
		# active play was paused. send trigger and save state
		self.movie_status['play'] = MOVIE_PAUSE
		# issue trigger to stop play
		self.triggerOut('transition_paused', self.display)
		# Save paused state
		self.save_pause()
		self.movie('status')

	def movie_play(self, source='MIDAS'):
		'Play the key-frame animation'
		if self.movie_validate():
			# Reset status
			self.movie_status['play'] = MOVIE_PLAY
			# Update GUI with a trigger (after reset status)
			if source == 'MIDAS':
				self.triggerOut('play', None)
			if self.display is None or self.display.index + 1 >= len(self):
				# If we were not displaying anything or were on the
				# last keyframe, start over
				self.movie_first(source)
			while self.movie_status['play'] == MOVIE_PLAY:
				if self.display.index == 0 and self.display.frames == 0 and \
					self.display.scene:
						# If we are at the first frame and it has no more frames
						# associated with it, then we need to make sure it is
						# shown at least once
						self.display.scene.display(inMovie=False)
				# special case if the first keyframe selected and has frames
				# to play. Just run the frames here and then continue. Playing
				# the first kf always just looks like a pause.
				if self.display.index == 0 and self.display.frames > 0 and \
					self.display.frameCount < self.display.frames:
						self.show(index=0)
						if self.movie_status['play'] == MOVIE_PAUSE:
							break
				# An interim Midas command or GUI event could
				# reset the 'stop' or 'pause' status, so they
				# are checked to exit the play process
				if self.movie_status['play'] == MOVIE_STOP:
					self.movie_stop(source)
					break
				# The pause functionality breaks the play loop to
				# get Chimera back into response mode (if a while
				# loop is used for the pause, it locks up the app).
				if self.movie_status['play'] == MOVIE_PAUSE:
					break
				self.movie_next(source)
				if self.switch_keyframe:
					self.switch_keyframe = False
					self.movie_play(source)
					break
			if self.movie_status['play'] == MOVIE_STOP:
				self.triggerOut('play_ended')

	def movie_record(self, source='MIDAS'):
		'toggle the record status and actions'
		if not len(self):
			self.movie_status['record'] = False
			chimera.replyobj.warning('No keyframes to animate.')
			return
		if self.movie_status['record']:
			# Turn off the movie recording
			self.movie_status['record'] = False
			try:
				# Complete playback before encoding
				self.movie_stop()
				cmd = 'movie encode ' + self.movie_encode_args
				chimera.runCommand(cmd)
			except Exception, e:
				pass
		else:
			# Turn on the movie recording
			self.triggerOut('record_started')
			self.movie_status['record'] = True
			try:
				self.movie_first(source)
				self.display.scene.display(inMovie=False)
				# Move to first keyframe before recording
				chimera.runCommand('movie record ' + self.movie_record_args)
				# Allow sync of playback while recording
				self.movie_play(source)
			except Exception, e:
				str(e)
				pass
#		if source == 'MIDAS':
#			# toggle the GUI when this command comes from MIDAS
#			self.triggerOut('record', None)

	def movie_resume(self, source='GUI'):
		'''restore the state and resume play of a keyframe.'''
		self.pausedState.stateRestore()
		frameCount = self.display.resume(frameCount=self.display.frameCount)
		# special case: keyframe is the last one and played completely
		if self.display.index == len(self) - 1 and frameCount == self.display.frames:
			if not self.movie_status['loop']:
				self.movie_stop()
				self.triggerOut('play_ended')

	def movie_minusOne(self, source='GUI'):
		# testing
		if self.movie_status['play'] == MOVIE_PAUSE:
			if self.display.frameCount > 0:
				self.display.trans.framePrevious(True,
							caller=self.display)
				self.save_pause()
			else:
				self.movie_status['play'] = MOVIE_STOP
				self.triggerOut('play_ended')

	def movie_plusOne(self, source='GUI'):
		'''step can begin when the movie is stopped. It can advance to the first
		frame of the next keyframe if already on the last.'''
		if self.display.frameCount == 0:
			# stepping past the current display so advance this time
			kf = self.next_keyframe(self.display)
			if kf == self.display: # already at the end
				self.movie_status['play'] = MOVIE_STOP
				self.triggerOut('play_ended')
				return
			self.display = kf

		if self.display.frameCount < self.display.frames:
			kf = self.display
			if isinstance(kf, Animate.Keyframe.Keyframe):
				kf.scene.state.initStateRestore() # needed only on the first frame but how do we know?
			kf.frameNext(True)
			self.save_pause()
		elif self.display.index == len(self.entries) - 1:
			self.movie_status['play'] = MOVIE_STOP
			self.triggerOut('play_ended')
		else: # step into next keyframe
			kf = self.getKeyframe_by_index(self.display.index + 1)
			self.display = kf
			kf.frameCount = 0
			if isinstance(kf, Animate.Keyframe.Keyframe):
				kf.scene.state.initStateRestore() # needed only on the first frame but how do we know?
			elif isinstance(kf, Animate.Action.Action):
				kf.initAction()
			kf.frameNext(True)
			self.save_pause()

	def movie_stop(self, source='MIDAS'):
		'Stop key-frame animation'
		# Reset status
		if self.movie_status['play'] != MOVIE_STOP:
			self.drop_pauseState()
			self.movie_status['play'] = MOVIE_STOP
		self.zero_frameCounts()
		#self.movie('status')
		# Sync movie recording
		if self.movie_status['record']:
			self.movie_record(source)
		# Update GUI with a trigger
#		if source == 'MIDAS':
#			self.triggerOut('stop', None)

	def movie_trigger(self, trigger=None, funcData=None, trigData=None):
		'Handle triggers for animation from the GUI'
		command = str(trigger)
		source = str(trigData)
		# Only handle movie triggers from the GUI
		if source == 'GUI':
			self.movie(command, source)

	def movie_validate(self):
		'Check whether there are any keyframes to animate.'
		if not len(self):
			return 0
		else:
			return len(self)

	def names(self, unique=False):
		'''Return a list of all the keyframe names's; cf. titles()
		- inputs:
			unique = True
				returns a list of unique names
			unique = False (default)
				returns a list of all names (repetition is possible)
		'''
		names = []
		if self.entries:
			for kf in self.entries:
				names.append(kf.name)
		if unique:
			return tuple(set(names))
		else:
			return tuple(names)

	def next_keyframe(self, kf):
		'return the next keyframe or kf is already on last'
		if kf.index == len(self.entries) - 1:
			return kf
		return self.getKeyframe_by_index(kf.index + 1)

	def new_id(self):
		'increment id and return to ensure uniqe keyframe ids'
		self._next_id += 1
		return self._next_id

	def remove(self, name=None, kf_id=None):
		'''
		Delete a keyframe or action
		- the keyframes list may contain multiple instances of the same name
		- an index, without a name, will remove only one instance
		- a name, without an index, will remove all instances
		- an index will take precedence over any name input
		- without any inputs, the last item is popped from the list
		return names
		- the method will not delete any scenes
		- activates the 'keyframe_remove' trigger, passing a keyframe instance
			to be removed (including associated GUI widgets)
		'''
		#
		# Parse args and delete keyframes
		if kf_id is not None:
			# Delete a single item
			self._kfDelete(kf_id)
		else:
			if name:
				# Delete any items with this name
				for keytitle in self.keytitles():
					(scene_name, kf_id) = self.keytitleSplit(keytitle)
					if scene_name == name:
						self._kfDelete(kf_id)
			else:
				# Delete the last item in the keyframe list
				if len(self):
					index = len(self) - 1
					kf = self.entries[index]
					self._kfDelete(kf.kf_id)
				#else:
				#	warning = 'No timeline frames'
				#	chimera.replyobj.warning(warning)
		#self.status()

	def replace(self, name, index):
		self.remove(name, index)
		self.insert(name, index)

	def save(self, name=None, index=None):
		'Save a keyframe to the file system (not implemented yet)'
		error = 'save method not implemented yet'
		raise chimera.error(error)
		# TODO: implement this with shelve in sceneState class
		#self.entries[name].save()

	def save_pause(self):
		'''save a scene state for the current display so it can be restored
		in case a pause is resumed.'''
		from SceneState import SceneState
		self.pausedState = SceneState('pausedScene', 'pausedScene')
		self.pausedState.properties = ['all']
		self.pausedState.frames = self.pausedState.frameCount = self.pausedState.discreteFrame = 1
		self.pauseSaved = True

	@property
	def scenes(self):
		'''This is a pointer to Scenes.scenes, which is used to access
		the scenes functionality (scene state etc.)
		'''
		return Scenes.scenes

	def show(self, name=None, index=None,
					frames=20, mode='linear', properties=['all'], force=False):
		'''
		Show the state of a single keyframe.
		- 'args': name, index, frames, mode
		- no 'args' will display the 'last' keyframe (if it exists).
		- 'name': a valid name of a keyframe state (pointer to a scene).
		- 'index': a valid positive index into the keyframes list;
					only used when name is not given;
					there may be multiple instances of a keyframe in the key
					frame list, but they all point to a single scene, so the
					specific index is not necessary.
		- 'frames': an integer to specify how many transition steps to
					interpolate between the current display state and
					the saved keyframe state.
		- 'mode': a string to specify the transition mode;
					'linear' is the only option at present;
					some transitions are discrete (regardless of this setting);
					additional options could allow subsets of transition parameters
					(such as motion, color, or model style), or variations in
					the interpolation methods available.
		- properties (list): types of properties to restore, including:
					'all', 'molecule', 'position', 'surface', 'view'.
		'''
		if DEBUG:
			print 'Keyframes.show: name = %s, index = %d\n' % (name, index)
		#
		# Although there can be multiple instances of a keyframe, each
		# instance refers to a unique scene name and the state of that
		# scene is obtained from the scenes dictionary, using the name.
		# So resolve the input parameters into a valid scene name.
		if not len(self):
			self.status()
			return False
		if index is not None:
			# Obtain the name using the index
			name = self.getSceneName_by_index(index)
		if not name:
			# Default to the last keyframe
			index = len(self) - 1
			name = self.getSceneName_by_index(index)
		if not self.validate(name):
			return False
		if index is None:
			# Assume the display at the first item with this name
			i = self.getIndex(name)
			if i:
				index = i[0]
		# Get the keyframe
		kf = self.getKeyframe_by_index(index)
		if kf is None:
			return False
		# Update the item currently in transition; the self.display values
		# are used in the movie commands for tracking display status.
		self.drop_pauseState() # playing a full keyframe; delete paused state
		self.triggerOut('keyframe_display', kf)
		if isinstance(kf, Animate.Keyframe.Keyframe) and kf.scene:
			kf.scene.state.initStateRestore()

		# the keyframe plays here
		if kf.display(kf.frameCount):
			if self.movie_status['play'] != MOVIE_STOP:
			# OK, it restored, so track it
				self.display = kf
		else:
			# It failed to display, so track the previous success
			self.triggerOut('keyframe_display', self.display)
		self.status('display')

	def status(self, type='names', **kw):
		'List the names of all keyframes on the command status bar'
		if 'log' not in kw:
			kw['log'] = True
		n = len(self)
		if n:
			if type == 'names':
				msg = 'Timeline: ' + ', '.join(self.scenes.dispnames())
			if type == 'display':
				kf = self.display
				if kf:
					msg = 'Timeline: %s (%d of %d)' % (kf.dispname, kf.index + 1, n)
				else:
					return
		else:
			msg = 'Timeline empty'
		if not msg.endswith('\n'):
			msg += '\n'
		Animate.status('%s' % msg, **kw)

	def endKeyframePlay(self, kf):
		'''user double clicked on keyframe while playing.
		Stop current play.  kf is the currently playing keyframe.'''
		try:
			trans = kf.trans
		except AttributeError:
			# Actions do not have transitions
			pass
		else:
			trans.finish(caller=kf)

	def switchKeyframePlay(self, kf):
		'''user double clicked on keyframe while playing.
		Resume on selected keyframe. kf is the currently playing keyframe.'''
		# flag to stop further of the current loop and restart on the switched kf
		self.switch_keyframe = True
		self.triggerOut('switch_keyframe', kf)

	def triggerInit(self):
		# These triggers are handled in GUI displays
		self.triggerset = chimera.triggerSet.TriggerSet()
		self.triggers = ['keyframe_append', 'keyframe_display',
			'keyframe_insert', 'keyframe_move', 'keyframe_remove',
			'keyframe_invalid', 'keyframe_update', 'change_title',
			'keyframe_properties', 'transition_paused', 'play_ended',
			'set_frameline', 'delete_actionHandler', 'switch_keyframe',
			'record_started', 'record_stopped']

		self.triggers.extend(self.movie_commands)
		for trigger in self.triggers:
			self.triggerset.addTrigger(trigger, self.triggerTracking)
		# Add scene trigger handlers.
		self.triggerHandlers = {}
		# Ensure that keyframes are properly linked to scenes, by
		# handling the trigger when a scene is removed or updated.
		for trig in ['scene_remove', 'scene_update']:
			h = self.scenes.triggerset.addHandler(trig, self.triggerIn, None)
			self.triggerHandlers[trig] = h

	def triggerIn(self, trigger=None, funcData=None, trigData=None):
		'Handle triggers for keyframes'
		if DEBUG:
			print 'Keyframes.triggerIn: ', trigger, funcData, trigData
			print
		if trigger == 'keyframe_invalid':
			# This is generated in response to a "scene_invalid" trigger.
			# After discussion, we decided to leave these objects, but
			# "mark" them as invalid (orphaned) instances.
			kf = trigData
			if kf:
				#self.remove(kf.name)
				self.triggerOut(trigger, kf)
		if trigger == 'scene_remove':
			scene = trigData
			self.remove(scene.name)
			self.integrity()
		if trigger == 'scene_update':
			sceneName = trigData.name
			self.update(sceneName)

	def triggerOut(self, trigger, *trigData):
		'''
		Activate a keyframe trigger, by its name
		- inputs:
			trigger=<trigger_name>: the name of a trigger to activate
			name=<keyframe_name>: the name of a keyframe
			index=<keyframe_index>: an index into the keyframe entries
		- with no input arguments, it prints the trigger names and
			any handlers already registered for each trigger
		- with a valid trigger name, it activates that trigger
			and passes the <keyframe_name> and <keyframe_index> to
			the handler (as triggerData).
		- raises chimera.error if the <trigger_name> is invalid
		'''
		if trigger is None:
			# print the list of trigger names
			trigger_names = self.triggerset.triggerNames()
			print 'Keyframe triggers: %s' % trigger_names
			for name in trigger_names:
				print 'Trigger handlers for "%s": ' % name
				print self.triggerset.triggerHandlers(name)
		else:
			if trigger not in self.triggers:
				error = 'No trigger named "%s"' % trigger
				raise chimera.error(error)
			if trigger in self.movie_commands:
				# 'MIDAS' means this trigger comes from the 'model',
				# the GUI handler uses this to update buttons etc.
				if DEBUG:
					print 'Keyframes.triggerOut: %s MIDAS\n' % trigger
				self.triggerset.activateTrigger(trigger, 'MIDAS')
			elif trigger == 'transition_paused':
				kf = trigData[0]
				if isinstance(kf, Animate.Keyframe.Keyframe):
					kf.trans.triggerset.activateTrigger(trigger, None)
				if isinstance(kf, Animate.Action.Action):
					kf.triggerset.activateTrigger(trigger, None)
			elif trigger == 'switch_keyframe':
				kf = trigData[0]
				if isinstance(kf, Animate.Keyframe.Keyframe):
					kf.trans.triggerset.activateTrigger(trigger, None)

			else:
				self.triggerset.activateTrigger(trigger, trigData)

	def triggerTracking(self, trigger, *args):
		if DEBUG:
			h = self.triggerset.triggerHandlers(trigger)
			print 'Keyframes.triggerTracking: %s = \t %s\n' % (trigger, repr(h))

	def update(self, name=None, index=None):
		'''
		Update keyframes
		- the keyframes list may contain multiple instances of the same name
		- an index, without a name, will replace only one keyframe
		- a name, without an index, will replace all keyframes
		- an index will take precedence over any name input
		- without any inputs, nothing is replaced
		- the method will not delete any scenes
		- activates the 'keyframe_update' trigger, passing tuple: (name, index)
		'''
		#
		# Parse args and replace keyframes
		trigName = 'keyframe_update'
		if index is not None:
			# Update an indexed item
			kf = self.getKeyframe_by_index(index)
			sc = self.scenes.getScene_by_name(kf.name)
			del kf.scene	# calls property deleter
			kf.scene = sc	# calls property setter
			self.triggerOut(trigName, kf)
		else:
			if name:
				for index, kf in enumerate(self.entries):
					if kf.name == name:
						sc = self.scenes.getScene_by_name(name)
						del kf.scene	# calls property deleter
						kf.scene = sc	# calls property setter
						self.triggerOut(trigName, kf)
		self.status()
#
#	def updateIndexes(self):
#		for i, kf in enumerate(self.entries):
#			kf.index = i

	def updateFrames(self):
		'''create a new list of entries in order of their end_frames on 
		the timeline, recalculating their frame counts. End_frame(s) 
		have already been updated as the result of a move.'''
		kf_list = []
		def by_endframe(kf):
			return kf.end_frame
		self.entries = sorted(self.entries, key=by_endframe)
#		current_endframe = 0
		for i, entry in enumerate(self.entries):
			if entry.index != i:
				info = "will move %s to position %d" % (entry.keytitle, i)
				oldtitle = str(entry.keytitle)
				entry.index = i
				self.triggerOut('change_title', oldtitle)
			old = entry.frames
			if i == 0: # first kf is special
				last_entry = entry
				entry.frames = entry.end_frame
			else:
				if entry.end_frame == last_entry.end_frame:
					entry.end_frame += 1
				entry.frames = entry.end_frame - last_entry.end_frame
			if entry.frames != old:
				self.triggerOut("keyframe_properties", entry)
			last_entry = entry

	def validate(self, name):
		'''
		Validate that a keyframe is a scene or a command.
		- returns 'scene' when keyframe 'name' is a reference to a scene
		- returns 'cmd' when keyframe 'name' is a reference to a cmd
		- returns False otherwise
		
		Restoring sessions saved before id's were used means keying on name.
		'''
		sc = self.scenes.getScene_by_name(name)
		if sc:
			return 'scene'
		elif name in self.cmds.names():
			return 'cmd'
		else:
			msg = 'Keyframes link to scenes - '
			msg += 'no scene named "%s"' % name
			chimera.replyobj.warning(msg)
			return False

	def zero_frameCounts(self):
		'when play is stopped, reset all frameCounts.'
		for kf in self.entries:
			kf.frameCount = 0

	def okay_to_delete_scene(self, name):
		if len(self.entries) == 0:
			return ""
		kf = self.getKeyframe_by_index(0)
		if kf.scene.name != name:
			return ""
		if len(self.entries) > 1:
			# Do not let user delete zeroth keyframe if next in line
			# is an Action since Action instances cannot be at the
			# start of an animation
			if isinstance(self.entries[1], Animate.Action.Action):
				return ("Scene cannot be deleted because "
					"timeline cannot start with an action")
		return ""

keyframes = Keyframes()
