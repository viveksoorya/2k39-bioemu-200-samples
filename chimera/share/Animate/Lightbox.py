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
import Tkdnd
from PIL.ImageTk import PhotoImage
from collections import OrderedDict

import chimera

# get access to the 'scenes' dict and 'keyframes' list
import Scenes
import Keyframes
import Transitions

DEBUG = 0


class Lightbox(object):
	'A class to manage scene and keyframe buttons'

	# Create a reference to the scenes, keyframes, and transitions
	@property
	def scenes(self):
		return Scenes.scenes
	@property
	def keyframes(self):
		return Keyframes.keyframes
	@property
	def transitions(self):
		return Transitions.transitions

	def __init__(self, parent, title,
		side=Tkinter.TOP, groupClass=Tkinter.Button):
		'''Initialize a lightbox button manager.
		'''
		# confirm access to identical object instances
		if DEBUG:
			import sys
			REFS = sys.getrefcount(Scenes.scenes)
			ID = str(id(Scenes.scenes))
			print 'Lightbox scenes:\t id = %s, refs = %s' % (ID, REFS)
			REFS = sys.getrefcount(Keyframes.keyframes)
			ID = str(id(Keyframes.keyframes))
			print 'Lightbox keyframes:\t id = %s, refs = %s\n' % (ID, REFS)
		#
		#
		self.parent = parent
		self.side = side
		# Create the parent container for all components.
		from chimera import widgets
		p = widgets.DisclosureFrame(parent, collapsed=False, text=title)
		self.group_interior = p.frame
		self.group = p
		# Configure the way the interior resizes: don't allow row 0
		# to resize (it contains utility buttons), allow row 1 to resize
		# (it contains the lightbox), and allow the only column to resize.
		self.group_interior.grid_rowconfigure(1, weight=1)
		self.group_interior.grid_columnconfigure(0, weight=1)
		# Create a balloon help manager
		self.balloonhelp = Pmw.Balloon()
		# Store GUI buttons (with component references)
		self.buttonDict = OrderedDict()
		# Create and update the button GUI
		self.lightbox_create(self.group_interior)

	#
	# --- Dialogs ---
	#

	def dialog_notebook(self, parent, title=None):
		'Add utility dialogs (activated by utility buttons)'
		# Create the main dialog
		if title is None:
			title = "Control Panels"
		self.dialog = NotebookDialog(parent, title='Control Panels')
		# Add a notebook to the dialog
		self.notebook = self.dialog.notebook
		self.notebook_populate()
		self.dialog.Close()

	def dialog_show(self, page):
		'Update and activate a page in the dialog notebook'
		self.dialog_update()
		self.notebook.selectpage(page)
		self.notebook.tab(page).focus_set()
		self.dialog.enter()

	def dialog_update(self):
		'Update utility dialogs (overload in subclasses)'
		pass

	def notebook_populate(self):
		'Add pages to the dialog notebook (overload in subclasses)'
		# Add pages to the notebook (to be populated later)
		pages = {}
		pageNames = []
		for pageName in pageNames:
			pages[pageName] = self.notebook.add(pageName)
		self.dialog._pages = pages
		# Populate each page

	def button_remove(self, name=None):
		'Remove a GUI-frame-button'
		if self.buttonDict.has_key(name):
			button = self.buttonDict[name]
			del self.buttonDict[name]
			self.balloonhelp.unbind(button)
			button.destroy()

	def button_select(self, title, selected=True, frame=None):
		'select a button'
		button = self.buttonDict[title]
		button.select(selected)

	def button_scale(self, button):
		'''Add a slider to the button frame, below the button.
		Returns Tkinter.Scale or None
		'''
		msg = 'Abstract method, implement it in subclasses'
		chimera.replyojb.warning(msg)
		return None


	def button_keytitleSplit(self, title):
		'Return name and index from button title'
		if title.count(':'):
			name, index = self.keyframes.keytitleSplit(title)
		else:
			name = title.strip()
			index = None
		return name, index

	def buttons_sorted(self):
		'Abstract function, overridden, as needed, in children.'
		return []

	def buttons_integrity(self):
		'''Query each button to verify it's references to scene or keyframe
		objects, remove any buttons with invalid references.'''
		# Get all the titles before loop, as the dict is modified in the loop
		titles = self.buttonDict.keys()
		for title in titles:
			button = self.buttonDict.get(title, None)
			if not button.verify():
				self.button_remove(title)

#	def buttons_sorted(self):
#		'Sort the titles for buttons'
#		bTitles = self.buttonDict.keys()
#		def by_idx(title):
#			return self.buttonDict[title].index
#		bTitles = sorted(bTitles, key=by_idx)
#		if DEBUG:
#			print "buttons_sorted"
#			for title in bTitles:
#				print title
#		return bTitles

	#
	# --- Lightbox (Button Grid) ---
	#

	def lightbox_callback(self, event=None):
		'A callback to rearrange the lightbox buttons'
		if event:
			self.lightbox_rearrange(event.width)

	def lightbox_clear(self):
		'Clear all the buttons'
		for bTitle in self.buttonDict.keys():
			self.button_remove(bTitle)

	def lightbox_create(self, parent):
		'Create a Pmw.ScrolledFrame for buttons'
		self.lightbox = Pmw.ScrolledFrame(parent,
			hscrollmode='none',
			vscrollmode='static')
		self.lightbox.grid(row=1, column=0,
			sticky=Tkinter.NSEW,
			padx=5, pady=5)
		# Arbitrarily set the height
		clipper = self.lightbox.component('clipper')
		clipper.configure(height=200)	# Arbitrary height!
		# Add dynamic layout for buttons when the widget is resized
		clipper.bind('<Configure>', self.lightbox_callback)

	def lightbox_rearrange(self, width=None):
		'Rearrange the button lightbox'
		from math import floor
		if width is None:
			clipper = self.lightbox.component('clipper')
			clipper.update_idletasks()
			width = clipper.winfo_width()
		width = float(width)
		for button in self.buttonDict.values():
			frame = button.frame
			frame.update_idletasks()
			frame_width = frame.winfo_width()
			framesPerRow = floor(width / frame_width)
			#print width, frame_width, framesPerRow
			break
		else:
			framesPerRow = 3
		# Assign the buttons to grid positions
		i = j = 0
		for button in self.buttons_sorted():
#			button = self.buttonDict.get(title)
			button.frame.grid(row=i, column=j)
			j += 1
			if j == framesPerRow:
				j = 0
				i += 1
		self.lightbox.reposition()

	def lightbox_update(self):
		'Recreate the button lightbox'
		msg = 'Abstract method, implement it in subclasses'
		chimera.replyojb.warning(msg)
		# See LightboxScenes and LightboxKeyframes for examples
		return None

	def selected(self):
		selected = []
		for title, button in self.buttonDict.items():
			if button.select():
				selected.append(title)
		return selected


from chimera.baseDialog import ModelessDialog
class NotebookDialog(ModelessDialog):

	buttons = ('Close',)

	def fillInUI(self, parent):
		import Pmw
		self.notebook = Pmw.NoteBook(parent, hull_height=400,
						hull_width=400)
		self.notebook.pack(fill="both", expand=1, padx=10, pady=10)
