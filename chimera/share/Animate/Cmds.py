# --- UCSF Chimera Copyright ---
# Copyright (c) 2006 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---

'''Controller/container for the Cmd instances. Linked to LightboxCmds
as a singleton.'''

import chimera
import Animate
import Cmd
from Cmd import ChoiceParam, IntParam, FloatParam, StrParam

DEBUG = 0

class Cmds(object):
	'''Contains the inventory of Cmd types available. Actions find them and
	instantiate them.'''

	def __init__(self):
		'''Create and manage the collection of cmds available on the Cmds
		palette in the Animation dialog.
		'''
		self.cmdDict = {}
		self.cmds = []
		for name in Cmd.cmds:
			self.cmdDict[name] = Cmd.cmds[name]()	# an instance that can be
			self.cmds.append(self.cmdDict[name].cmd)# copied to an Action

	def names(self):
		'A tuple of all command names'
		return tuple(self.cmdDict.keys())

	def validate(self, name):
		'Verify that a named cmd has been defined'
		if name in self.names():
			return True

	def getCmd(self, name):
		'Get an cmd, by name'
		if self.validate(name):
			return self.cmds[name]

cmds = Cmds()
