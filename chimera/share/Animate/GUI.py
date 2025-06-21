# --- UCSF Chimera Copyright ---
# Copyright (c) 2006 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---


# Note: To access the Animation GUI instance while running chimera, use:
#aniGUI = chimera.dialogs.find('Animation')
#aniGUI.keyframesGUI
#aniGUI.scenesGUI

import Tkinter as Tk
import chimera
from chimera.baseDialog import ModelessDialog, NotifyDialog

import Animate
import Preferences
import LightboxScenes
import LightboxCmds
import LightboxKeyframes

class GUI(ModelessDialog):
	name = 'Animation'
	help = 'ContributedSoftware/animation/animation.html'
	buttons = ('Preferences', 'Close',)
	#default = 'Close'
	provideStatus = True
	statusPosition = 'above'

	def __init__(self, *args, **kw):
		ModelessDialog.__init__(self, *args, **kw)

	def fillInUI(self, parent):
		'Fill in Tkinter user interface in parent frame'
		self.parent = parent
		pref = Preferences.get()
		# Add a 'lightbox' for scenes and actions
		parent.columnconfigure(0, weight=1)
		parent.columnconfigure(1, weight=1)
		parent.rowconfigure(0, weight=1)
		parent.rowconfigure(1, weight=1)
		self.scGUI = LightboxScenes.LightboxScenes(parent)
		self.scGUI.group.grid(row=0, column=0, sticky="nsew")
		self.scGUI.group.collapseCmd = self._collapseCB
		self.cmdGUI = LightboxCmds.LightboxCmds(parent)
		self.cmdGUI.group.grid(row=0, column=1, sticky="nsew")
		self.cmdGUI.group.collapseCmd = self._collapseCB

		# add a lightbox for keyframes/animation
		self.kfGUI = LightboxKeyframes.LightboxKeyframes(parent)
		self.kfGUI.group.grid(row=1, column=0, columnspan=2, sticky="nsew")
		self.kfGUI.group.collapseCmd = self._collapseCB
		self.kfGUI.update()
		# Add Tkdnd functions to the parent
		self.dnd_widget = self.parent
		self.dnd_widget.dnd_accept = self.dnd_accept
		self.dnd_widget.dnd_commit = self.dnd_commit
		self.dnd_widget.dnd_enter = self.dnd_enter
		self.dnd_widget.dnd_leave = self.dnd_leave
		self.dnd_widget.dnd_motion = self.dnd_motion

		self.scGUI.lightbox_update()

	def _collapseCB(self, df, collapsed):
		f = self.uiMaster()
		if (self.scGUI.group.isCollapsed()
		and self.cmdGUI.group.isCollapsed()):
			f.rowconfigure(0, weight=0)
		else:
			f.rowconfigure(0, weight=1)
		if self.kfGUI.group.isCollapsed():
			f.rowconfigure(1, weight=0)
		else:
			f.rowconfigure(1, weight=1)

	def map(self):
		Animate.statusFunc = self.status
	def unmap(self):
		Animate.statusFunc = chimera.replyobj.status
	def Hide(self):
		self.Close()
	def Preferences(self):
		Preferences.set()
	#
	# --- Tkdnd methods ---
	#
	def dnd_accept(self, Source, event):
		#Tkdnd is asking us if we want to tell it about a TargetObject.
		#print "aniGUI::dnd_accept"
		return self.dnd_widget
	def dnd_enter(self, Source, event):
		#This is called when the mouse pointer goes from outside the
		#Target Widget to inside the Target Widget.
		#print "aniGUI::dnd_enter"
		#Source.show()
		# protect against a color-well color being dragged across the timeline
		if hasattr(Source, 'updateXY'):
			Source.updateXY(event.x_root, event.y_root)
	def dnd_leave(self, Source, event):
		#This is called when the mouse pointer goes from inside
		#to outside the Target Widget.
		#print "aniGUI::dnd_leave"
		#Source.hide()
		return
	def dnd_motion(self, Source, event):
		#This is called when the mouse pointer moves within the TargetWidget.
		#print "aniGUI::dnd_motion"
		# protect against a color-well color being dragged across the timeline
		if hasattr(Source, 'updateXY'):
			Source.updateXY(event.x_root, event.y_root)
	def dnd_commit(self, Source, event):
		#This is called if the DraggedObject is being dropped on us
		#print "aniGUI::dnd_commit; Object received= %s" % repr(Source)
		return


chimera.dialogs.register(GUI.name, GUI)
