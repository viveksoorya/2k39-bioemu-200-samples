# --- UCSF Chimera Copyright ---
# Copyright (c) 2006 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---


import chimera
import Transitions


DEBUG = 0

class Transitions(object):
	'''
	A dictionary of transitions:
		- keys are unique names for a transition (string values)
		- values are instance objects of Animate.Transition
	There is a 'triggerset' with two triggers for adding or deleting
	a transition, named 'transition_append' and 'transition_remove', respectively.
	'''

	def __init__(self):
		self.transitionDict = {}
		self.triggerInit()

	def __len__(self):
		return len(self.transitionDict)

	def __str__(self):
		return str(self.transitionDict)

	@property
	def keyframes(self):
		from Animate import keyframes
		return keyframes

	#
	# Pickle methods
	#
	def __getstate__(self):
		# Let the pickle call occur in Session.py, not here.
		# Return the transition dict; it will contain transition instances,
		# which will respond to pickle with their own __getstate__ method.
		pickleDict = self.transitionDict
		return pickleDict

	def __setstate__(self, pickleDict):
		# pickleDict is already unpickled
		self.__init__()
		for name, tr in pickleDict.items():
			self.transitionCreateTriggers(tr)
			self.transitionDict[name] = tr
			self.triggerOut('transition_append', tr.name)
			msg = 'Created transition "%s"' % tr.name
		# ensure older saved states are compatible
		from Transitions import transitions
		if 	not self.transitionDict.has_key('custom_scene'):
			self.transitionDict['custom_scene'] = transitions.transitionGet('custom_scene')

	def append(self, id=None, frames=None, mode=None, properties=None):
		'''
		Append a named transition.
		- name is an arbitrary, unique name for a transition; if the named
			transition exists, it is updated by Transitions.update()
		- frames is the number of frames in a transition
		- mode is the style of transition ('linear')
		- properties is a list of attributes to animate in a transition, the
			default is ['all']; see Animate.Transition.PropertySet.
		- activates the 'transition_append' trigger, passing 'name'.
		'''
		if id is None:
			id = self.keyframes.new_id()
		if id in self.names():
			self.update(id, frames, mode, properties)
			return self.transitionDict[id]
		self.transitionCreate(id, frames, mode, properties)
		self.triggerOut('transition_append', id)
		msg = 'Created state for transition "%s"' % id
		return self.transitionDict[id]

	def clear(self):
		'Remove all transitions'
		for name in self.names():
			self.remove(name)

	def destroy(self):
		pass

	def names(self):
		'A tuple of all transition names'
		return tuple(self.transitionDict.keys())

	@property
	def prefix(self):
		from Animate import Preferences
		pref = Preferences.get()
		return pref['transition_name']

	def remove(self, name=None):
		'''
		Remove a named transition frame from the dictionary
		- input:
			'name' is a string identifier for an existing transition
		- activates the 'transition_remove' trigger, passing 'name'
		'''
		if name is None:
			return
		tr = self.transitionGet(name)
		#tr.triggerset.deleteHandler(*self.triggerHandlers[name])
		#del self.triggerHandlers[name]
		tr.destroy()
		del self.transitionDict[name]
		self.triggerOut('transition_remove', name)
		if DEBUG:
			import sys
			REFS = sys.getrefcount(tr)
			ID = id(tr)
			print 'transitions.remove: name=%s, id=%d, refs=%d\n' % (name, ID, REFS)

	def transitionGet(self, name):
		'Return a transition instance'
		if self.validate(name):
			return self.transitionDict[name]

	def transitionCreate(self, name, frames=None, mode=None, properties=None):
		'Create a transition instance'
		from Transition import Transition
		# If arguments are None, Transition substitutes defaults.
		tr = Transition(name, frames, mode, properties)
		self.transitionDict[tr.name] = tr

	def transitionCreateName(self):
		n = len(self) + 1
		name = '%s%04d' % (self.prefix, n)
		# Ensure we get a new name
		while name in self.names():
			n += 1
			name = '%s%04d' % (self.prefix, n)
		return name

	def transitionCreateTriggers(self, transition):
		pass
		#trigName = 'transition_invalid'
		#h = transition.triggerset.addHandler(trigName, self.triggerIn, None)
		#self.triggerHandlers[transition.name] = (trigName, h)

	def title(self, name):
		tr = self.transitionGet(name)
		return tr.title

	def titles(self):
		'Get transition titles'
		return self.names()

	def triggerInit(self):
		# Track trigger handlers
		self.triggerHandlers = {}
		# These triggers are handled in GUI displays
		self.triggerset = chimera.triggerSet.TriggerSet()
		self.triggers = [ 'transition_append',
			'transition_remove', 'transition_update']
		for trigger in self.triggers:
			self.triggerset.addTrigger(trigger, self.triggerTracking)

	def triggerIn(self, trigger=None, funcData=None, trigData=None):
		'Handle triggers for transitions'
		if DEBUG:
			print 'transitions.triggerIn:', trigger, funcData, trigData

	def triggerOut(self, trigger=None, name=None):
		'''
		Activate a transition trigger, by its name
		- inputs:
			trigger=<trigger_name>: the name of a trigger to activate
			name=<transition_name>: the name of a transition
		- with no input arguments, it prints the trigger names and
			any handlers already registered for each trigger
		- with a valid trigger name, it activates that trigger
			and passes the <name> to the handler (as triggerData).
		- echoes a chimera error if the <trigger_name> is invalid
		'''
		if not trigger:
			# print the list of trigger names
			trigger_names = self.triggerset.triggerNames()
			print 'transition triggers: %s' % trigger_names
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
			print 'transitions.triggerTracking: %s = %s\n' % (trigger, repr(h))

	def update(self, name, frames=None, mode=None, properties=None):
		'''
		Update a named transition.
		- name is an arbitrary, unique name for a transition; if the named
			transition exists, it is updated.
		- frames is the number of frames in a transition
		- mode is the style of transition ('linear')
		- properties is a list of attributes to animate in a transition, the
			default is ['all']; see Animate.Transition.PropertySet for details.
		- activates a 'transition_update' trigger, passing name
		'''
		if frames is None:
			frames = 0
		if mode is None:
			mode = 'linear'
		if properties is None:
			properties = ['all']
		if self.validate(name):
			msg = 'updating state for transition "%s"' % name
			# Reassign the name, without using self.remove(name), to
			# keep it's place in transitionDict.keys() and to avoid removing
			# any keyframes that link to this transition (they should respond
			# to the transition_update trigger.
			tr = self.transitionGet(name)
			tr.frames = frames
			tr.mode = mode
			tr.properties = properties
			self.triggerOut('transition_update', name)

	def validate(self, name):
		'Verify that a named transition has been defined'
		if name in self.names():
			return True
		else:
			warn = 'No transition named "%s"' % name
			chimera.replyobj.warning(warn)
			return False

	def write(self, name='default'):
		'Write a transition to the file system'
		#
		# TODO: Look at using ZODB
		# http://www.zodb.org/documentation/tutorial.html
		#
		tr = self.transitionGet(name)
		tr.save()

# Create a set of transitions, with a couple of default styles.
transitions = Transitions()
#transitions.append(name, frames, mode, properties)
transitions.append('scene', 1, 'linear', ['all'])
transitions.append('keyframe', 20, 'linear', ['all'])
transitions.append('custom_scene', 1, 'linear', ['all'])

