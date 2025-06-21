# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---

import chimera.extension
#
# extension management object (EMO)
#
class AnimateEMO(chimera.extension.EMO):
	'Chimera extension management object for animation utilities'
	def name(self):
		return 'Animation'
	def description(self):
		return 'Animation interfaces'
	def categories(self):
		return ['Utilities']
	#def icon(self):
	#	# Comment out this function if you don't have an icon
	#	return self.path("Template.png")
	def activate(self):
		from chimera.dialogs import display
		display(self.module('GUI').GUI.name)
		return None
	def cmdLine(self, cmdName, args):
		# Comment out if no command is needed
		self.module('Commands').run(cmdName, args)
	#def modelPanelCB(self, molecules):
	#	# Comment out if no model panel button is needed
	#	self.module("modelpanel").callback(molecules)
	#	# Add any default arguments you need
	#def open(self, path):
	#	# Comment out if cannot open new file type
	#	self.module("filetype").open(path)

animEMO = AnimateEMO(__file__)
chimera.extension.manager.registerExtension(animEMO)

#===============================================================================
# Midas commands
#===============================================================================

from Midas.midas_text import addCommand
# addCommand(command, cmdFunc, revFunc=None, help=None, changesDisplay=True)

#------------------------------------------------------------------------------ 
# Add command wrappers to do imports at runtime, so extension loads faster

def doScene(cmdName, args):
	from Animate import Commands
	Commands.processScene(cmdName, args)

def doTransition(cmdName, args):
	from Animate import Commands
	Commands.processTransition(cmdName, args)

def doAnimate(cmdName, args):
	from Animate import Commands
	Commands.processAnimate(cmdName, args)

#------------------------------------------------------------------------------ 
# Add the commands

addCommand('scene',
		doScene, help=True,
		revFunc=doScene,
		changesDisplay=True)

# TODO: Enable these commands when the infrastructure is implemented

#addCommand('transition',
#		doTransition,
#		revFunc=doTransition,
#		changesDisplay=False)

#addCommand('animate',
#		doAnimate,
#		# no revFunc
#		changesDisplay=True)




#------------------------------------------------------------------------------ 
#
# TODO: Once the commands above are fully implemented, all the keyframe commands
#		might be removed.
#


# --- Commands for keyframes

def doKeyFrameAdd(cmdName, args):
	from Animate import Commands
	Commands.doKeyFrameAdd(cmdName, args)
addCommand('kfadd',
		doKeyFrameAdd,
		changesDisplay=False)

def doKeyFrameClear(cmdName, args):
	from Animate import Commands
	Commands.doKeyFrameClear(cmdName, args)
addCommand('kfclear',
		doKeyFrameClear,
		changesDisplay=False)

def doKeyFrameDel(cmdName, args):
	from Animate import Commands
	Commands.doKeyFrameDel(cmdName, args)
addCommand('kfdel',
		doKeyFrameDel,
		changesDisplay=False)

def doKeyFrameMove(cmdName, args):
	from Animate import Commands
	Commands.doKeyFrameMove(cmdName, args)
addCommand('kfmove',
		doKeyFrameMove,
		changesDisplay=False)

def doKeyFrameMovie(cmdName, args):
	from Animate import Commands
	Commands.doKeyFrameMovie(cmdName, args)
addCommand('kfmovie',
		doKeyFrameMovie,
		changesDisplay=True)

def doKeyFrameSave(cmdName, args):
	from Animate import Commands
	Commands.doKeyFrameSave(cmdName, args)
addCommand('kfsave',
		doKeyFrameSave,
		changesDisplay=False)

def doKeyFrameShow(cmdName, args):
	from Animate import Commands
	Commands.doKeyFrameShow(cmdName, args)
addCommand('kfshow',
		doKeyFrameShow,
		changesDisplay=True)

def doKeyFrameStatus(cmdName, args):
	from Animate import Commands
	Commands.doKeyFrameStatus(cmdName, args)
addCommand('kfstatus',
		doKeyFrameStatus,
		changesDisplay=False)

'''
def doKeyFrameTransition(cmdName, args):
	from Animate import Commands
	Commands.doKeyFrameTransition(cmdName, args)
addCommand('kftrans',
		doKeyFrameTransition,
		changesDisplay=False)
'''

