# --- UCSF Chimera Copyright ---
# Copyright (c) 2006 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---

import Pmw
import Tkinter

import chimera

# get access to the 'scenes' dict and 'keyframes' list
from Lightbox import Lightbox
from LightboxButton import CmdButton
import Cmds


DEBUG = 0

class LightboxCmds(Lightbox):
	'A GUI for cmds'
	'''For now, associate specific cmds with image files to use for 
	their representation. This may change later.'''

	def __init__(self, parent):
		Lightbox.__init__(self, parent, "Actions")
		# self.dialog_create(self.group_interior)
#		self.propertiesDialog = ScenePropertiesDialog(self.group_interior, self.scenes)
#
#		self.dialog_notebook(self.group_interior, "Actions")
		# Add utility buttons.
#		self.create_utilities(self.group_interior)
		#help = 'Removing a scene removes all associated keyframes.\n'
		##help += 'scene gallery items can be dragged to animation'
		#self.balloonhelp.bind(self.lightbox, help)
#		self.triggerInit()
		self.update()

	@property
	def cmds(self):
		return Cmds.cmds

	def button_create(self, parent, cmd):
		button = CmdButton(parent, cmd)
		self.buttonDict[button.name] = button

	def button_remove(self, title=None):
		'Remove a GUI-cmd-button'
		if self.buttonDict.has_key(title):
			button = self.buttonDict[title]
			del self.buttonDict[title]
#			self.balloonhelp.unbind(button)
			button.destroy()

	def buttons_sorted(self):
		'Return all Buttonbutton titles in their current order'
		def by_name(button):
			return button.name
		return sorted(self.buttonDict.values(), key=by_name)
#		bTitles = sorted(bTitles, key=by_idx)
#		btitles = []
#		for button in self.buttonDict.values():
#			btitles.append(button.disptitle)
#		return sorted(btitles)

	def update(self):
		for name in self.cmds.cmdDict:
			if name not in self.buttonDict:
				self.button_create(self.lightbox.interior(),
					self.cmds.cmdDict[name])
		self.lightbox_rearrange()

	def unselect_all(self):
		'unselect all buttons'
		for button in self.buttonDict.values():
			button.select(False)

	def extend_select(self, cmd_title):
		'extend selection if there is a last_selected'
		last_selected = self.last_selected
		if last_selected == '':
			return
		state = "start"
		end = None
		for title, button in self.buttonDict.iteritems():
			if state == "start":
				if title == cmd_title:
					state = "during"
					end = last_selected
				if title == last_selected:
					state = "during"
					end = cmd_title
			if state == "during":
				button.select(True)
				if title == end:
					state = "after"
			else:
				button.select(False)

	def lightbox_image_update(self):
		for button in self.buttonDict.values():
			button.setImageSize()

	def toggle_select(self, cmd_title):
		button = self.buttonDict.get(cmd_title)
		if button.select():
			button.select(False)
			self.last_selected = ''
		else:
			button.select(True)
			self.last_selected = button.name

	def radio_select(self, cmd_title):
		'select/unselect this scene only'
		others_selected = False
		for title, button in self.buttonDict.iteritems():
			if title == cmd_title:
				continue
			button.select(False)
			others_selected = True
		if not others_selected:
			self.toggle_select(cmd_title)
		else:
			# If there were other buttons selected,
			# we force this button to be selected
			# even if it was already selected before
			button = self.buttonDict.get(cmd_title)
			button.select(True)
			self.last_selected = button.name
