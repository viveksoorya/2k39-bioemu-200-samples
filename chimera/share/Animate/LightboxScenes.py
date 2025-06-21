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
import Icons
from Lightbox import Lightbox
from LightboxButton import SceneButton

DEBUG = 0

class LightboxScenes(Lightbox):
	'A GUI for scenes'

	def __init__(self, parent):
		# Populate the parent with a group container,
		# a lightbox display, and get handles to scenes and keyframes
		Lightbox.__init__(self, parent, "Scenes")
		# Add utility dialog boxes (activated by utility buttons below).
		# self.dialog_create(self.group_interior)
		self.propertiesDialog = ScenePropertiesDialog(self.group_interior, self.scenes)
		self.last_selected = '' # name of last selected scene

		self.dialog_notebook(self.group_interior, "Scenes")
		# Add utility buttons.
		self.create_utilities(self.group_interior)
		#help = 'Removing a scene removes all associated keyframes.\n'
		##help += 'scene gallery items can be dragged to animation'
		#self.balloonhelp.bind(self.lightbox, help)
		self.triggerInit()
		self.update()

	#
	# --- Utility Buttons ---
	#

	def create_utilities(self, parent):
		self.utilities = {}
		self.utility_frame = Tkinter.Frame(parent)
		self.utility_frame.grid(row=0, column=0,
			sticky=Tkinter.NW)
		col = 0

		# self.utility_frame.bind('<Control-Button-1', notebook_append_activate)

		# Create an 'Add Scene' button
		from PIL.ImageTk import PhotoImage
		scadd_icon = Icons.LoadImage('knob-add.png')
		if scadd_icon:
			col += 1
			scadd_help = 'Add a new scene'
			scadd_icon = PhotoImage(scadd_icon)
			scadd_button = Tkinter.Button(self.utility_frame,
				image=scadd_icon,
				relief=Tkinter.FLAT,
				command=self.addScene)
			scadd_button.grid(row=0, column=col)
			scadd_button._icons = (scadd_icon,)
			self.utilities['Add Scene'] = scadd_button
			self.balloonhelp.bind(scadd_button, scadd_help)
		# Create a 'Remove Scene' button
		scdel_icon = Icons.LoadImage('knob-remove-red.png')
		if scdel_icon:
			col += 1
			scdel_help = 'Remove selected scene(s) (and timeline items)'
			scdel_icon = PhotoImage(scdel_icon)
			scdel_button = Tkinter.Button(self.utility_frame,
				image=scdel_icon,
				relief=Tkinter.FLAT,
				command=self.removeScenes)
			scdel_button.grid(row=0, column=col)
			scdel_button._icons = (scdel_icon,)
			self.utilities['Remove Scenes'] = scdel_button
			self.balloonhelp.bind(scdel_button, scdel_help)
#		# Create a 'Clear All' button
#		scene_clear_icon = Icons.LoadImage('knob-cancel.png')
#		if scene_clear_icon:
#			col += 1
#			scene_clear_help = 'Clear all scenes (and timeline items)'
#			scene_clear_icon = PhotoImage(scene_clear_icon)
#			scene_clear_button = Tkinter.Button(self.utility_frame,
#				image=scene_clear_icon,
#				relief=Tkinter.FLAT,
#				command=self.scene_clear)
#			scene_clear_button.grid(row=0, column=col)
#			scene_clear_button._icons = (scene_clear_icon,)
#			self.utilities['Clear All'] = scene_clear_button
#			self.balloonhelp.bind(scene_clear_button, scene_clear_help)
		## Add a button for preferences
		#icon = Icons.LoadImage('settings.png')
		#if icon:
		#	col += 1
		#	help = 'Animation Preferences'
		#	icon = PhotoImage(icon)
		#	button = Tkinter.Button(self.utility_frame,
		#		image=icon,
		#		relief=Tkinter.FLAT,
		#		command=Preferences.set)
		#	button.grid(row=0, column=col)
		#	button._icons = (icon,)
		#	self.utilities['Animation Preferences'] = button
		#	self.balloonhelp.bind(button, help)

	def addScene(self):
		name = self.scenes.getNewName()
		desc = "" # set later using properties
		# Don't allow creation of a scene that already exists
		if name not in self.scenes.names():
			self.scenes.append(name, desc)
		else:
			msg = 'Scene name exists'
			chimera.replyobj.warning(msg)
	#
	# --- Buttons ---
	#

	def button_create(self, parent, scene):
		button = SceneButton(parent, scene)
		self.buttonDict[button.name] = button

	def buttons_sorted(self):
		'Sort the buttons by display name'
		import re
		regex = re.compile('(\d*)(.*)')
		def by_name(button):
			m = regex.search(button.name)
			num = m.group(1)
			if num == '':
				# force numbers to be first
				num = '100000'
			return (int(num), m.group(2))
		return sorted(self.buttonDict.values(), key=by_name)

	#
	# --- Lightbox (Button Grid) ---
	#

	def lightbox_update(self):
		'Recreate the button lightbox'
		# TODO: Instead of clearing everything and regenerating it again,
		# iterate over the buttons to validate they refer to existing
		# scenes, keep those that do and remove those that do not.  Then
		# rearrange the layout.
		self.buttons_integrity()
		for name in self.scenes.names():
			if name not in self.buttonDict:
				sc = self.scenes.getScene_by_name(name)
				self.button_create(self.lightbox.interior(), sc)
		self.lightbox_rearrange()

	def lightbox_image_update(self):
		for title, button in self.buttonDict.items():
			button.sceneImageUpdate()

	#
	# --- Dialogs ---
	#

	def dialog_create(self, frame):
		'Add menu dialogs (activated by menu buttons)'
		pass

	def dialog_update(self, sc=None):
		'Update utility dialogs'
		self.properties_dialog_update(sc)
		self.notebook_append_update()
		self.notebook_arrange_update()

	def notebook_populate(self):
		# Add pages to the notebook (to be populated later)
		pages = {}
		pageNames = ['Append', 'Arrange']
		for pageName in pageNames:
			pages[pageName] = self.notebook.add(pageName)
		self.dialog._pages = pages
		# Populate each page
		self.notebook_append_page()
		self.notebook_arrange_page()


	# --- Scene append notebook

	def notebook_append_page(self):
		'Create a notebook page for adding scenes'
		page = self.dialog._pages['Append']
		#
		# Provide an option to add a new scene here
		entry = Pmw.EntryField(page,
			labelpos='w',
			label_text='Scene Name: ',
			#command=self.scene_append, # leave this to the 'Add' button
			errorbackground='red',
			validate=self.notebook_append_validate)
		entry.pack(side=Tkinter.TOP,
			fill=Tkinter.X, expand=1,
			padx=10, pady=5)
		entry.setvalue('')
		self.notebook_append_entry = entry
		# Add balloon help
		help = 'New scene names must be unique.'
		self.balloonhelp.bind(entry, help)
		# Create a ScrolledText for scene description.
		fixedFont = Pmw.logicalfont('Fixed', size=10)
		text = Pmw.ScrolledText(page,
				# borderframe = 1,
				labelpos='nw',
				label_text='Scene Description',
				usehullsize=1,
				hull_width=400,
				hull_height=200,
				text_wrap=Tkinter.WORD,
				text_font=fixedFont,
				text_padx=4,
				text_pady=4,
		)
		text.pack(side=Tkinter.TOP,
			fill=Tkinter.BOTH, expand=1,
			padx=10, pady=5)
		self.notebook_append_text = text
		#
		# Add action buttons
		buttonbox = Pmw.ButtonBox(page,
			labelpos='nw',
			label_text='Add a new scene:',
			frame_borderwidth=2,
			frame_relief='groove')
		buttonbox.pack(side=Tkinter.BOTTOM,
			fill=Tkinter.X, expand=1,
			padx=10, pady=5)
		# Add some action buttons to the ButtonBox.
		actions = ['Add', ]
		for action in actions:
			# Use x=button to set lambda default (can't rely on runtime lookup)
			cb = lambda x = action: self.notebook_append_cb(x)
			buttonbox.add(action, command=cb)
		buttonbox.alignbuttons()	# set buttons same width
		self.append_buttonbox = buttonbox

	def notebook_append_activate(self):
		self.notebook_append_update()
		self.dialog_show('Append')

	def notebook_append_update(self):
		name = self.scenes.getNewName()
		self.notebook_append_entry.setvalue(name)
		self.notebook_append_text.clear()

	def notebook_append_cb(self, result=None):
		'Callback for the notebook page to add a new scene'
		dispname = self.notebook_append_entry.getvalue()
		desc = self.notebook_append_text.getvalue()
		# Don't allow creation of a scene that already exists
		if dispname not in self.scenes.dispnames():
			self.scenes.append(dispname, desc)
		else:
			msg = 'Scene name exists'
			chimera.replyobj.warning(msg)

	def notebook_append_validate(self, dispname=None):
		'Validate a new scene name entry'
		if dispname in self.scenes.dispnames():
			# Don't allow creation of a scene that already exists
			# Note, don't use Pmw.ERROR here because it doesn't allow
			# typing something like 'sc2' when 'sc' already exists.
			return Pmw.PARTIAL
		else:
			return Pmw.OK


	# --- Scene arrange notebook

	def notebook_arrange_page(self):
		'Create a notebook page for moving scenes'
		page = self.dialog._pages['Arrange']
		#
		# Display a list of scenes
		listbox = Pmw.ScrolledListBox(page,
			items=self.scenes.dispnames(),
			labelpos='nw',
			label_text='Scenes:',
			listbox_selectmode=Tkinter.EXTENDED,
			listbox_height=6,
			#selectioncommand=self.selectionCommand,
			#dblclickcommand=self.defCmd,
			#usehullsize=1,
			#hull_width=200,
			#hull_height=200,
			)
		listbox.pack(side=Tkinter.LEFT,
			fill=Tkinter.BOTH, expand=1,
			padx=10, pady=5)
		self.arrange_listbox = listbox
		msg = 'Arrange scenes\n'
		msg += ' - click on scene names to select\n'
		msg += ' - shift-click for range selection\n'
		msg += ' - ctrl-click for multiple, discrete selections'
		self.balloonhelp.bind(listbox, msg)
		#
		# Add action buttons
		buttonbox = Pmw.ButtonBox(page,
			labelpos='nw',
			label_text='Arrange scenes:',
			frame_borderwidth=2,
			frame_relief='groove',
			orient='vertical')
		buttonbox.pack(side=Tkinter.RIGHT,
			fill=Tkinter.X, expand=1,
			padx=10, pady=5)
		# Add some action buttons to the ButtonBox.
		#actions = ['Move Up', 'Move Down', 'Remove', 'Clear All']
		actions = ['Remove', 'Clear All']
		for action in actions:
			# Use x=button to set lambda default (can't rely on runtime lookup)
			cb = lambda x = action: self.notebook_arrange_cb(x)
			buttonbox.add(action, command=cb)
		buttonbox.alignbuttons()	# set buttons same width
		self.arrange_buttonbox = buttonbox

	def notebook_arrange_activate(self):
		'Update and activate the dialog to arrange scenes'
		self.notebook_arrange_update()
		self.dialog_show('Arrange')

	def notebook_arrange_update(self, selectedIndices=[]):
		'Update the dialog when scenes are altered'
		self.scenes.integrity()
		dispnames = self.scenes.dispnames()
		titlesSelected = [names[i] for i in selectedIndices]
		self.arrange_listbox.setlist(dispnames)
		self.arrange_listbox.setvalue(titlesSelected)

	def notebook_arrange_cb(self, action=None):
		'Callback for the dialog to arrange scenes'
		# Define lists for trackTitles and selectTitles
		trackTitles = []
		selectTitles = list(self.arrange_listbox.getvalue())
		if action == 'Move Down':
			# selectTitles is ordered from lowest to highest index, so
			# reverse it to move the highest item first.
			selectTitles.reverse()
		# Unpack name from strings in selectTitles, and
		# populate trackTitles before moving anything, in case nothing moves.
		#for i, title in enumerate(selectTitles):
		#	name, index = self.button_keytitleSplit(title)
		#	selectTitles[i] = (name, index)
		#	trackTitles.append(index)
		if action == 'Move Up':
			# TODO: until scenes.move is implemented, skip this option
			return
			# Titles is ordered from lowest to highest index
			for i, item in enumerate(selectTitles):
				name, index = item
				if index >= 1:
					# update is triggered by keyframes.move
					self.scenes.move(indexFrom=index, indexTo=index - 1)
					trackTitles[i] = index - 1
				else:
					# Stop when the lowest item in the list cannot be moved
					break
			self.notebook_arrange_update(trackTitles)
		elif action == 'Move Down':
			# TODO: until scenes.move is implemented, skip this option
			return
			# Try to move selected Titles down
			for i, item in enumerate(selectTitles):
				name, index = item
				if index < len(self.keyframes) - 1:
					# update is triggered by keyframes.move
					self.scenes.move(indexFrom=index, indexTo=index + 1)
					trackTitles[i] = index + 1
				else:
					# Stop when the highest item in the list cannot be moved
					break
			self.notebook_arrange_update(trackTitles)
		elif action == 'Clear All':
			self.scene_clear()
		elif action == 'Remove':
			names = list(self.arrange_listbox.getvalue())
			for name in names:
				self.scenes.remove(name)
		else:
			# Unknown action
			pass

	def properties_activate(self, scene):
		self.propertiesDialog.activate(scene)

	def properties_dialog_update(self, sc=None):
		self.propertiesDialog.update(sc)

	# --- Scene clear dialog

	def scene_clear(self):
		'Confirm removal of all scenes'
		from chimera.baseDialog import AskYesNoDialog
		text = ("Please confirm removal of all scenes.\n"
			"This will also clear the timeline.")
		d = AskYesNoDialog(text=text, title="Clear All Scenes")
		if d.run(self.group_interior) == "yes":
			self.scenes.clear()

	def unselect_all(self):
		'unselect all scenes.'
		for button in self.buttonDict.values():
			button.select(False) # still a property; change to function

	def extend_select(self, name):
		'extend selection if there is a last_selected'
		buttons = self.buttons_sorted()
		last_selected = self.last_selected
		if last_selected == '':
			return
		state = "start"
		end = None
		for button in buttons:
			if state == "start":
				if button.name == name:
					state = "during"
					end = last_selected
				elif button.name == last_selected:
					state = "during"
					end = name
			if state == "during":
				button.select(True)
				if button.name == end:
					state = "after"
			else:
				button.select(False)

	def toggle_select(self, name):
		button = self.buttonDict.get(name)
		if button.select():
			button.select(False)
			self.last_selected = ''
		else:
			button.select(True)
			self.last_selected = button.scene.name

	def radio_select(self, name):
		'select/unselect this scene only'
		others_selected = False
		for scene_name, button in self.buttonDict.items():
			if scene_name == name:
				continue
			# turn others off
			button.select(False)
			others_selected = True
		if not others_selected:
			self.toggle_select(name)
		else:
			# If there were other buttons selected,
			# we force this button to be selected
			# even if it was already selected before
			button = self.buttonDict.get(name)
			button.select(True)
			self.last_selected = button.scene.name

	#
	# --- Triggers ---
	#

	def removeScenes(self):
		'remove selected scenes and associated keyframes'
		for name in self.scenes.names():
			scene = self.buttonDict.get(name, None)
			if scene.select():
				self.scenes.remove(name)

	def triggerInit(self):
		'Initialise trigger handlers for scenes'
		for trig in self.scenes.triggers:
			self.scenes.triggerset.addHandler(trig, self.triggerIn, None)

	def triggerIn(self, trigger=None, funcData=None, trigData=None):
		'''
		A method to handle triggers for the scene lightbox
		- calls self.update(), which doesn't require trigger data
		- may be extended to handle more complex trigger contingencies
		'''
		if DEBUG:
			print 'LightboxScenes.triggerIn: ', trigger, funcData, trigData
		if trigger == 'scene_update':
			# Let the button object take care of updating it's display.
			pass
		if trigger in ['scene_update', 'scene_invalid']:
			# Update the scene display
			name = trigData.name
			button = self.buttonDict.get(name)
			button.sceneImageUpdate()
		if trigger == 'scene_remove':
			# Destroy the scene button
			scene = trigData
			self.button_remove(scene.name)
		self.update(trigData)

	def update(self, sc=None):
		self.lightbox_update()
		self.dialog_update(sc)


from chimera.baseDialog import ModelessDialog

class ScenePropertiesDialog(ModelessDialog):
	'manage properties for scenes'
	buttons = ("Okay", "Apply", "Cancel")
	title = "Scene Properties"
	help = 'ContributedSoftware/animation/animation.html#scene-context'

	def __init__(self, parent, scenes, *args, **kw):
		self.scenes = scenes
		self.balloonhelp = Pmw.Balloon()
		ModelessDialog.__init__(self, *args, **kw)
		self.Close()

	def fillInUI(self, parent):
		'Create a dialog to manage properties of scenes'
		# scene selector
		combobox = Pmw.ComboBox(parent,
			label_text='Scenes:',
			labelpos='nw',
			selectioncommand=self.update, # value is a scene name
			history=False,
			)
		combobox.pack(side=Tkinter.TOP, anchor=Tkinter.N,
			fill=Tkinter.X, expand=0,
			padx=5, pady=5)
		combobox.listbox = combobox.component('scrolledlist')
		combobox.entry = combobox.component('entryfield')
#		combobox.component('entryfield_entry').configure(state=Tkinter.DISABLED)
		dispnames = self.scenes.dispnames()
		if dispnames:
			combobox.listbox.setlist(dispnames)
			combobox.entry.setvalue(dispnames[0])
		self.scSelector = combobox


		# Create a ScrolledText for scene description.
		fixedFont = Pmw.logicalfont('Fixed', size=10)
		text = Pmw.ScrolledText(parent,
				# borderframe = 1,
				labelpos='nw',
				label_text='Scene Description',
				usehullsize=1,
				hull_width=400,
				hull_height=200,
				text_wrap=Tkinter.WORD,
				text_font=fixedFont,
				text_padx=4,
				text_pady=4,
		)
		text.pack(side=Tkinter.TOP,
			fill=Tkinter.BOTH, expand=1,
			padx=10, pady=5)
		self.desc = text

	def activate(self, scene):
		self.update(scene)
		self.enter()

	def validate_name(self, dispname):
		'Validate a new scene name entry'
		if dispname in self.scenes.dispnames():
			# Don't allow creation of a scene that already exists
			# Note, don't use Pmw.ERROR here because it doesn't allow
			# typing something like 'sc2' when 'sc' already exists.
			return Pmw.PARTIAL
		else:
			return Pmw.OK

	def update(self, scene=None):
		'''scene may be an instance or a scene.name.'''
		if isinstance(scene, str):
			scene = self.scenes.getScene_by_dispname(scene)
		if scene:
			self.name = scene.name
		else:
			self.name = None
		scSel = self.scSelector
		dispnames = self.scenes.dispnames()
		if not dispnames:
			scSel.listbox.setlist([])
			# self.entry.clear()
			self.desc.clear()
			return
		scSel.listbox.setlist(dispnames)
		if scene:
			scSel.entry.setvalue(scene.dispname)
			self.desc.setvalue(scene.description)

	def Apply(self):
		# save the current scene's setting
		scSel = self.scSelector
		cur_name = scSel.entry.get()
		# new_name = self.entry.getvalue()
#		scene = self.scenes.getScene(cur_name)
#		scene.name = new_name
		new_desc = self.desc.getvalue()
		sc = self.scenes.getScene_by_name(self.name)
		self.scenes.update_properties(sc.name, {'description': new_desc,
			'dispname': cur_name})
		self.update(sc)

	def Okay(self):
		# Apply and close
		self.Apply()
		self.Close()
